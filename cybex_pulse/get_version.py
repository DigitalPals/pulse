#!/usr/bin/env python3
"""
Simple script to get the current version of Cybex Pulse.

This script demonstrates how to get the current version programmatically.
"""
import time
from datetime import datetime
from cybex_pulse.utils.version_manager import version_manager

def main():
    """Print the current version of Cybex Pulse."""
    version = version_manager.get_version()
    is_dev = version_manager.is_development_version()
    last_modified = version_manager.get_last_modified()
    
    print(f"Cybex Pulse version: {version}")
    
    if last_modified:
        # Convert timestamp to human-readable date
        modified_date = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S')
        print(f"Last updated: {modified_date}")
    
    if is_dev:
        print("This is a development version")

if __name__ == "__main__":
    main()