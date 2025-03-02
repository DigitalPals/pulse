"""
Template filters for the Cybex Pulse web interface.
"""

from cybex_pulse.web.filters.datetime import timestamp_to_time, timestamp_to_relative_time
from cybex_pulse.web.filters.json import from_json
from cybex_pulse.web.filters.icon import device_icon

__all__ = [
    "timestamp_to_time",
    "timestamp_to_relative_time",
    "from_json",
    "device_icon",
    "register_filters"
]

def register_filters(app):
    """Register all template filters with the Flask application.
    
    Args:
        app: Flask application instance
    """
    app.jinja_env.filters['timestamp_to_time'] = timestamp_to_time
    app.jinja_env.filters['timestamp_to_relative_time'] = timestamp_to_relative_time
    app.jinja_env.filters['from_json'] = from_json
    app.jinja_env.filters['device_icon'] = device_icon