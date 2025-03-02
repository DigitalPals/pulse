#\!/usr/bin/env python3
"""
This script checks and fixes module packaging issues for cybex-pulse.
"""
import os
import sys
import shutil
from pathlib import Path

def main():
    """Check and fix common packaging issues."""
    current_dir = os.getcwd()
    print(f"Current directory: {current_dir}")

    # 1. Check if this is a proper package
    setup_py_exists = os.path.exists('cybex_pulse/setup.py')
    print(f"setup.py exists: {setup_py_exists}")

    # 2. Create __init__.py files where needed
    print("Creating __init__.py files...")
    for root, dirs, files in os.walk(current_dir):
        # Skip hidden directories and the venv directory
        dirs[:] = [d for d in dirs if not d.startswith('.') and d \!= 'venv']
        if os.path.basename(root) \!= '__pycache__':
            init_file = os.path.join(root, '__init__.py')
            if not os.path.exists(init_file):
                print(f"Creating {init_file}")
                with open(init_file, 'a'):
                    pass

    # 3. Fix setup.py if it exists
    if setup_py_exists:
        print("Adjusting setup.py...")
        setup_py_path = os.path.join(current_dir, 'cybex_pulse/setup.py')
        with open(setup_py_path, 'r') as f:
            content = f.read()
        
        # Ensure packages are properly specified
        if 'packages=find_packages(),' in content:
            content = content.replace(
                'packages=find_packages(),',
                "packages=find_packages(include=['cybex_pulse', 'cybex_pulse.*']),"
            )
            with open(setup_py_path, 'w') as f:
                f.write(content)
            print("Updated packages in setup.py")

    # 4. Create a direct module for importing
    print("Creating direct module access...")
    cybex_dir = os.path.join(current_dir, 'cybex_pulse')
    
    # Create a simple wrapper module at the root
    with open(os.path.join(current_dir, 'cybex_pulse.py'), 'w') as f:
        f.write(f'''
# cybex_pulse module wrapper
import sys
import os

# Add the directory to Python path
module_dir = os.path.dirname(os.path.abspath(__file__))
if module_dir not in sys.path:
    sys.path.insert(0, module_dir)

# Import from the actual module
from cybex_pulse import *
''')
    print("Created cybex_pulse.py wrapper")

    print("Fix complete\!")

if __name__ == "__main__":
    main()
