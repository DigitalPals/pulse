"""
Web server module for Cybex Pulse.
"""
import hashlib
import json
import logging
import os
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from cybex_pulse import __version__
from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config
from cybex_pulse.utils.system_check import check_required_tools, get_installation_instructions
from cybex_pulse.utils.version_manager import version_manager
from cybex_pulse.utils.async_logging import async_log_manager
from cybex_pulse.web.utils.network import get_local_ip
from cybex_pulse.web.filters import register_filters
from cybex_pulse.web.routes import register_routes
from cybex_pulse.web.api import register_api_routes


class WebServer:
    """Web server for Cybex Pulse application."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager, logger: logging.Logger, main_app=None):
        """Initialize the web server.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
            main_app: The main CybexPulseApp instance for callbacks
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logger
        self.main_app = main_app  # Reference to main application for callbacks
        self.server = None  # Will hold the Flask server instance
        self.version = version_manager.get_version()  # Get version from version manager
        self.is_dev_version = version_manager.is_development_version()
        self.version_last_modified = version_manager.get_last_modified()
        
        # Check required tools
        self.tool_status = check_required_tools()
        self.logger.info(f"Required tools status: {self.tool_status}")
        self.get_installation_instructions = get_installation_instructions
        
        # Import Flask here to avoid dependency if web interface is disabled
        try:
            from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash, Response, stream_with_context
            import werkzeug.serving
            self.flask = Flask
            self.jsonify = jsonify
            self.render_template = render_template
            self.request = request
            self.redirect = redirect
            self.url_for = url_for
            self.session = session
            self.flash = flash
            self.Response = Response
            self.stream_with_context = stream_with_context
            self.werkzeug = werkzeug
            self.json = json  # Use the imported json module
        except ImportError:
            self.logger.error("Flask not installed. Web interface disabled.")
            return
        
        # Initialize Flask app
        self.app = self.flask(__name__)
        self.app.secret_key = os.urandom(24)
        
        # Register custom filters
        register_filters(self.app)
        
        # Setup authentication and configuration decorators
        self.login_required = self._create_login_required_decorator()
        self.configuration_required = self._create_configuration_required_decorator()
        
        # Register all routes
        self._register_routes()
        
        # Register teardown function to close database connections after each request
        @self.app.teardown_request
        def close_db_connection(exception=None):
            """Close database connection after each request."""
            if hasattr(self, 'db_manager'):
                self.db_manager.close()
    def start(self) -> None:
        """Start the web server."""
        if not hasattr(self, 'app'):
            self.logger.error("Flask not installed. Web interface not started.")
            return
        
        # Set up asynchronous logging for Werkzeug to prevent lock contention
        async_log_manager.patch_werkzeug_logger()
        self.logger.debug("Werkzeug logger patched with asynchronous logging")
        
        host = self.config.get("web_interface", "host")
        port = self.config.get("web_interface", "port")
        
        # Display appropriate message based on host binding
        if host == "0.0.0.0":
            actual_ip = get_local_ip()
            if actual_ip:
                self.logger.info(f"Starting web server on all interfaces - access at http://{actual_ip}:{port}")
            else:
                self.logger.info(f"Starting web server on all interfaces - access at http://YOUR_IP_ADDRESS:{port}")
        else:
            self.logger.info(f"Starting web server on {host}:{port}")
        
        # Use Werkzeug's make_server instead of app.run() for better shutdown control
        self.server = self.werkzeug.serving.make_server(
            host, port, self.app, threaded=True
        )
        self.server.serve_forever()
    
    def shutdown(self) -> None:
        """Shutdown the web server gracefully."""
        if not self.server:
            self.logger.debug("No web server instance to shut down")
            return
            
        self.logger.info("Shutting down web server gracefully")
        try:
            # Directly shut down the server in the current thread
            # This is safer than using a separate thread which might cause the NoneType error
            self._shutdown_server()
            
            # Clean up async logging resources for Werkzeug
            from cybex_pulse.utils.async_logging import async_log_manager
            if hasattr(async_log_manager, 'werkzeug_listener') and async_log_manager.werkzeug_listener:
                self.logger.debug("Cleaning up Werkzeug async logging resources")
                async_log_manager.werkzeug_listener.stop()
                async_log_manager.werkzeug_logger_patched = False
        except Exception as e:
            self.logger.error(f"Error during web server shutdown: {e}")
    
    def _shutdown_server(self) -> None:
        """Internal method to shutdown the server."""
        try:
            if self.server:
                self.server.shutdown()
                self.server = None
                self.logger.info("Web server shutdown completed")
        except Exception as e:
            self.logger.error(f"Error in web server shutdown: {e}")
    
    def _register_routes(self) -> None:
        """Register all Flask routes."""
        # Register website routes
        register_routes(self.app, self)
        
        # Register API routes
        register_api_routes(self.app, self)
    
    def _create_login_required_decorator(self):
        """Create a login_required decorator bound to this instance.
        
        Returns:
            function: Decorator function
        """
        def login_required(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._is_authenticated():
                    return self.redirect(self.url_for('login'))
                return f(*args, **kwargs)
            return decorated_function
        return login_required
    
    def _create_configuration_required_decorator(self):
        """Create a configuration_required decorator bound to this instance.
        
        Returns:
            function: Decorator function
        """
        def configuration_required(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.config.is_configured():
                    return self.redirect(self.url_for('setup_wizard'))
                return f(*args, **kwargs)
            return decorated_function
        return configuration_required
    
    def _is_authenticated(self) -> bool:
        """Check if user is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        # If no authentication is configured, allow access
        username = self.config.get("web_interface", "username")
        password_hash = self.config.get("web_interface", "password_hash")
        
        if not username or not password_hash:
            return True
        
        return self.session.get('logged_in', False)
    
    def _check_credentials(self, username: str, password: str) -> bool:
        """Check if credentials are valid.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        config_username = self.config.get("web_interface", "username")
        config_password_hash = self.config.get("web_interface", "password_hash")
        
        if not config_username or not config_password_hash:
            return True
        
        # Hash the provided password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        return username == config_username and password_hash == config_password_hash