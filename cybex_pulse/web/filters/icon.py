"""
Icon related filters for templates.
"""
from cybex_pulse.utils.icon_mapper import IconMapper


def device_icon(vendor, device_name=None):
    """Get the appropriate Font Awesome icon HTML for a device based on vendor and device name.
    
    Args:
        vendor: Device vendor name
        device_name: Device model name
        
    Returns:
        str: HTML for the appropriate icon
    """
    icon_mapper = IconMapper()
    return icon_mapper.get_icon_html(vendor, device_name)