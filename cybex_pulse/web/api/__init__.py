"""
API routes for the web interface.
"""

from cybex_pulse.web.api.devices import register_device_routes
from cybex_pulse.web.api.events import register_event_routes
from cybex_pulse.web.api.speed import register_speed_routes
from cybex_pulse.web.api.fingerprinting import register_fingerprinting_routes
from cybex_pulse.web.api.system import register_system_api

__all__ = [
    "register_api_routes"
]

def register_api_routes(app, server):
    """Register all API routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    register_device_routes(app, server)
    register_event_routes(app, server)
    register_speed_routes(app, server)
    register_fingerprinting_routes(app, server)
    register_system_api(app, server)