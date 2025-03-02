"""
Utility functions for the web interface.
"""

from cybex_pulse.web.utils.auth import login_required, configuration_required
from cybex_pulse.web.utils.network import get_local_ip

__all__ = [
    "login_required",
    "configuration_required",
    "get_local_ip"
]