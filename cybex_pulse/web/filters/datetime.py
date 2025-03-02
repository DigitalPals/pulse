"""
Date and time filters for templates.
"""
import time
from datetime import datetime


def timestamp_to_time(timestamp):
    """Convert Unix timestamp to human-readable time.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        str: Formatted datetime string
    """
    if not timestamp:
        return "N/A"
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))


def timestamp_to_relative_time(timestamp):
    """Convert Unix timestamp to relative time (e.g., '5m ago').
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        str: Relative time string
    """
    if not timestamp:
        return "N/A"
    
    now = time.time()
    diff = now - timestamp
    
    if diff < 60:
        return "Just now"
    elif diff < 3600:
        minutes = int(diff / 60)
        return f"{minutes}m ago"
    elif diff < 86400:
        hours = int(diff / 3600)
        return f"{hours}h ago" 
    else:
        days = int(diff / 86400)
        return f"{days}d ago"