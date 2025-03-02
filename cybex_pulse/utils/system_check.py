"""
System check utilities for Cybex Pulse.
"""
import logging
import shutil
import subprocess
from typing import Dict, List, Tuple

logger = logging.getLogger("cybex_pulse.system_check")

def check_required_tools() -> Dict[str, bool]:
    """
    Check if required tools are installed on the system.
    
    Returns:
        Dict[str, bool]: Dictionary with tool names as keys and boolean values
                         indicating if they are installed.
    """
    required_tools = {
        "arp-scan": False,
        "nmap": False,
        "snmpwalk": False,
        "arp": False,
        "ip": False,
        "getent": False,
        "avahi-resolve": False,
        "avahi-browse": False,
        "speedtest-cli": False
    }
    
    # Check each tool
    for tool in required_tools:
        # First check if tool is in PATH
        if shutil.which(tool) is not None:
            required_tools[tool] = True
        else:
            # Try running the tool to check if it's available
            try:
                subprocess.run(
                    [tool, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False
                )
                required_tools[tool] = True
            except FileNotFoundError:
                logger.warning(f"Required tool not found: {tool}")
                required_tools[tool] = False
    
    return required_tools

def get_installation_instructions(tool: str) -> str:
    """
    Get installation instructions for a specific tool.
    
    Args:
        tool: Name of the tool
        
    Returns:
        str: Installation instructions
    """
    instructions = {
        "arp-scan": """
To install arp-scan:

Ubuntu/Debian:
```
sudo apt update
sudo apt install arp-scan
```

CentOS/RHEL:
```
sudo yum install arp-scan
```

Fedora:
```
sudo dnf install arp-scan
```

Arch Linux:
```
sudo pacman -S arp-scan
```

macOS:
```
brew install arp-scan
```
""",
        "nmap": """
To install nmap:

Ubuntu/Debian:
```
sudo apt update
sudo apt install nmap
```

CentOS/RHEL:
```
sudo yum install nmap
```

Fedora:
```
sudo dnf install nmap
```

Arch Linux:
```
sudo pacman -S nmap
```

macOS:
```
brew install nmap
```
""",
        "snmpwalk": """
To install snmpwalk (part of net-snmp):

Ubuntu/Debian:
```
sudo apt update
sudo apt install snmp
```

CentOS/RHEL:
```
sudo yum install net-snmp-utils
```

Fedora:
```
sudo dnf install net-snmp-utils
```

Arch Linux:
```
sudo pacman -S net-snmp
```

macOS:
```
brew install net-snmp
```
""",
        "arp": """
To install arp (net-tools):

Ubuntu/Debian:
```
sudo apt update
sudo apt install net-tools
```

CentOS/RHEL:
```
sudo yum install net-tools
```

Fedora:
```
sudo dnf install net-tools
```

Arch Linux:
```
sudo pacman -S net-tools
```

macOS:
```
Already installed by default
```
""",
        "ip": """
To install ip command (iproute2):

Ubuntu/Debian:
```
sudo apt update
sudo apt install iproute2
```

CentOS/RHEL:
```
sudo yum install iproute
```

Fedora:
```
sudo dnf install iproute
```

Arch Linux:
```
sudo pacman -S iproute2
```

macOS:
```
brew install iproute2mac
```
""",
        "getent": """
To install getent:

Ubuntu/Debian:
```
Already installed by default (part of libc-bin)
```

CentOS/RHEL/Fedora:
```
Already installed by default (part of glibc-common)
```

Arch Linux:
```
Already installed by default (part of glibc)
```

macOS:
```
Not directly available on macOS
```
""",
        "avahi-resolve": """
To install avahi-resolve (part of avahi-utils):

Ubuntu/Debian:
```
sudo apt update
sudo apt install avahi-utils
```

CentOS/RHEL:
```
sudo yum install avahi-tools
```

Fedora:
```
sudo dnf install avahi-tools
```

Arch Linux:
```
sudo pacman -S avahi
```

macOS:
```
brew install avahi
```
""",
        "avahi-browse": """
To install avahi-browse (part of avahi-utils):

Ubuntu/Debian:
```
sudo apt update
sudo apt install avahi-utils
```

CentOS/RHEL:
```
sudo yum install avahi-tools
```

Fedora:
```
sudo dnf install avahi-tools
```

Arch Linux:
```
sudo pacman -S avahi
```

macOS:
```
brew install avahi
```
""",
        "speedtest-cli": """
To install speedtest-cli:

Ubuntu/Debian:
```
sudo apt update
sudo apt install speedtest-cli
```

CentOS/RHEL:
```
sudo yum install speedtest-cli
```

Fedora:
```
sudo dnf install speedtest-cli
```

Arch Linux:
```
sudo pacman -S speedtest-cli
```

macOS:
```
brew install speedtest-cli
```

Using pip (all systems):
```
pip install speedtest-cli
```
"""
    }
    
    return instructions.get(tool, f"No installation instructions available for {tool}.")