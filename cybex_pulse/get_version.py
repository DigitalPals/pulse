#!/usr/bin/env python3
"""
Simple script to get the current version of Cybex Pulse.

This script demonstrates how to get the current version programmatically.
The version is stored in a VERSION file in the repository root.
"""
import os
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
    
    # Print the location of the VERSION file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.abspath(os.path.join(script_dir, ".."))
    version_file = os.path.join(repo_root, "VERSION")
    if os.path.exists(version_file):
        print(f"Version file: {version_file}")
    else:
        print("Version file not found")

if __name__ == "__main__":
    main()