"""
Web routes for the Cybex Pulse application.
"""

from cybex_pulse.web.routes.dashboard import register_dashboard_routes
from cybex_pulse.web.routes.devices import register_device_routes
from cybex_pulse.web.routes.events import register_events_routes
from cybex_pulse.web.routes.security import register_security_routes
from cybex_pulse.web.routes.setup import register_setup_routes
from cybex_pulse.web.routes.auth import register_auth_routes
from cybex_pulse.web.routes.internet import register_internet_routes
from cybex_pulse.web.routes.updates import register_update_routes
from cybex_pulse.web.routes.console import register_console_routes

__all__ = [
    "register_routes"
]

def register_routes(app, server):
    """Register all web routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Register all route modules
    register_dashboard_routes(app, server)
    register_device_routes(app, server)
    register_events_routes(app, server)
    register_security_routes(app, server)
    register_setup_routes(app, server)
    register_auth_routes(app, server)
    register_internet_routes(app, server)
    register_update_routes(app, server)
    register_console_routes(app, server)
    
    # Register error handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return server.render_template('404.html'), 404
    
    @app.errorhandler(500)
    def server_error(e):
        return server.render_template('500.html'), 500