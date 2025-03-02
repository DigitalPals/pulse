"""
JSON filters for templates.
"""
import json


def from_json(json_string):
    """Convert JSON string to Python object.
    
    Args:
        json_string: JSON string to parse
        
    Returns:
        dict/list: Parsed JSON data or empty list on error
    """
    if not json_string:
        return []
    try:
        return json.loads(json_string)
    except (json.JSONDecodeError, TypeError):
        return []