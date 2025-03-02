#!/usr/bin/env python3
import json
import os
from pathlib import Path

# Path to the configuration file
config_path = Path.home() / ".cybex_pulse" / "config.json"

print(f"Looking for config file at: {config_path}")
print(f"File exists: {config_path.exists()}")

if not config_path.exists():
    print("Config file not found!")
    exit(1)

# Load the configuration
try:
    with open(config_path, "r") as f:
        config = json.load(f)
    print("Successfully loaded config file")
except Exception as e:
    print(f"Error loading config file: {e}")
    exit(1)

# Print the entire config for debugging
print("\nCurrent configuration:")
print(json.dumps(config, indent=2))

# Check if security scanning is enabled
security_config = config.get("monitoring", {}).get("security", {})
security_enabled = security_config.get("enabled", False)
print(f"\nSecurity scanning is currently: {'ENABLED' if security_enabled else 'DISABLED'}")

if security_config:
    print(f"Security scanning interval: {security_config.get('interval', 'Not set')} seconds")

# Enable security scanning if it's not already enabled
if not security_enabled:
    print("\nEnabling security scanning...")
    if "monitoring" not in config:
        config["monitoring"] = {}
    if "security" not in config["monitoring"]:
        config["monitoring"]["security"] = {}
    
    config["monitoring"]["security"]["enabled"] = True
    config["monitoring"]["security"]["interval"] = 86400  # 24 hours in seconds
    
    # Save the updated configuration
    try:
        with open(config_path, "w") as f:
            json.dump(config, f, indent=4)
        print("Security scanning has been enabled.")
        print("You'll need to restart the application for this change to take effect.")
    except Exception as e:
        print(f"Error saving config file: {e}")
else:
    print("\nSecurity scanning is already enabled.")
    print("If it's not working, there might be another issue.")

# Check if nmap is installed and working
print("\nChecking nmap installation:")
try:
    import nmap
    print("python-nmap package is installed")
except ImportError:
    print("python-nmap package is NOT installed")

# Try to run nmap directly
print("\nTrying to run nmap command:")
exit_code = os.system("nmap --version > /dev/null 2>&1")
print(f"nmap command exit code: {exit_code} (0 means success)")

if exit_code != 0:
    print("nmap command failed. This could be why security scanning isn't working.")
    print("Try installing nmap: sudo apt-get install nmap")
else:
    print("nmap command is working correctly.")

# Check if there are any devices in the database
print("\nNote: Security scanning requires devices in the database to scan.")
print("If no devices have been discovered yet, there's nothing to scan.")