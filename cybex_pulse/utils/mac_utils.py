"""
Utility functions for MAC address handling.
"""

def normalize_mac(mac_address: str) -> str:
    """Normalize MAC address to a consistent format.
    
    Converts MAC address to lowercase for consistent comparison and storage.
    
    Args:
        mac_address: MAC address string
        
    Returns:
        Normalized MAC address string (lowercase)
    """
    if not mac_address:
        return ""
    
    # Convert to lowercase for consistent comparison
    return mac_address.lower()

def normalize_vendor(vendor: str) -> str:
    """Normalize vendor name to a consistent format.
    
    Removes parentheses and "locally administered" text from vendor names.
    
    Args:
        vendor: Vendor name string
        
    Returns:
        Normalized vendor name string
    """
    if not vendor:
        return ""
    
    # Remove "locally administered" text
    vendor = vendor.replace("(locally administered)", "").replace("locally administered", "")
    
    # Remove any parentheses and their contents
    import re
    vendor = re.sub(r'\([^)]*\)', '', vendor)
    
    # Remove extra whitespace
    vendor = ' '.join(vendor.split())
    
    return vendor.strip()