"""
Dashboard routes for the web interface.
"""
import json
import time
from cybex_pulse.utils.system_check import get_installation_instructions


def register_dashboard_routes(app, server):
    """Register dashboard routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Make config, version, and update status available to all templates
    @app.context_processor
    def inject_config():
        # Get update status if available
        update_available = False
        update_disabled = False
        update_checker = server.main_app.update_checker if server.main_app else None
        
        if update_checker:
            update_available = update_checker.update_available
            
            # Check if update should be disabled based on commit hash
            if hasattr(update_checker, 'current_commit_hash') and update_checker.current_commit_hash:
                if update_checker.current_commit_hash.startswith("install-") or update_checker.current_commit_hash == "unknown":
                    update_disabled = True
            
        return {
            'config_obj': server.config,
            'version': server.version,
            'update_available': update_available,
            'update_disabled': update_disabled
        }

    # Dashboard route
    @app.route('/')
    @server.login_required
    @server.configuration_required
    def dashboard():
        devices = server.db_manager.get_all_devices()
        # Add current timestamp for template
        now = int(time.time())
        
        # Get missing tools and their installation instructions
        missing_tools = {}
        for tool, installed in server.tool_status.items():
            if not installed:
                missing_tools[tool] = get_installation_instructions(tool)
        
        # Get recent speed tests for Internet Health status
        speed_tests = server.db_manager.get_recent_speed_tests(limit=10)
        
        # Get recent events for dashboard display
        events = server.db_manager.get_recent_events(limit=5)
        
        # Get website monitoring data
        website_checks = []
        if server.config.config.get("monitoring", {}).get("websites", {}).get("enabled", False):
            # Get the most recent check for each website
            all_checks = server.db_manager.get_website_checks()
            url_to_latest_check = {}
            
            for check in all_checks:
                url = check.get('url')
                if url not in url_to_latest_check or check.get('timestamp', 0) > url_to_latest_check[url].get('timestamp', 0):
                    url_to_latest_check[url] = check
            
            website_checks = list(url_to_latest_check.values())
        
        # Count security vulnerabilities for Network Security status
        security_vulnerabilities = 0
        for device in devices:
            device_id = device.get('id')
            if device_id:
                security_scans = server.db_manager.get_security_scans(device_id, limit=1)
                if security_scans and security_scans[0].get('vulnerabilities'):
                    try:
                        vulnerabilities = json.loads(security_scans[0]['vulnerabilities'])
                        if vulnerabilities:
                            security_vulnerabilities += len(vulnerabilities)
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        return server.render_template('dashboard.html',
                                   devices=devices,
                                   now=now,
                                   missing_tools=missing_tools,
                                   speed_tests=speed_tests,
                                   events=events,
                                   website_checks=website_checks,
                                   security_vulnerabilities=security_vulnerabilities,
                                   config=server.config)
                               
    # About route                           
    @app.route('/about')
    @server.login_required
    def about():
        return server.render_template('about.html')