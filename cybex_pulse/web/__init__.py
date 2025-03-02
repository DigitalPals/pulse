"""
Web interface module for Cybex Pulse.
"""
import os
from pathlib import Path

# Create a Jinja2 filter to convert timestamps to human-readable time
def timestamp_to_time_filter(timestamp):
    """Convert a Unix timestamp to a human-readable time string."""
    from datetime import datetime
    if not timestamp:
        return "Never"
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")

# Create a Jinja2 filter to parse JSON strings
def from_json_filter(json_string):
    """Parse a JSON string into a Python object."""
    import json
    if not json_string:
        return []
    try:
        return json.loads(json_string)
    except:
        return []

def init_app(app):
    """Initialize the Flask application with template filters and static files."""
    # Register template filters
    app.jinja_env.filters['timestamp_to_time'] = timestamp_to_time_filter
    app.jinja_env.filters['from_json'] = from_json_filter
    
    # Ensure static directory exists
    static_dir = Path(__file__).parent / "static"
    if not static_dir.exists():
        static_dir.mkdir(parents=True)
        
    css_dir = static_dir / "css"
    if not css_dir.exists():
        css_dir.mkdir(parents=True)
    
    # Ensure templates directory exists
    templates_dir = Path(__file__).parent / "templates"
    if not templates_dir.exists():
        templates_dir.mkdir(parents=True)