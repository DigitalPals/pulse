"""
Network utilities for the web interface.
"""
import socket


def get_local_ip():
    """Get the local IP address of the machine.
    
    Returns:
        str: The local IP address, or None if it cannot be determined
    """
    try:
        # Create a socket that connects to an external address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
        s.close()
        return ip_address
    except:
        return None