#!/usr/bin/env python3
"""
Fix module for the 'get_cpu_info' not defined error.
This script adds the missing import to the appropriate module.
"""
import os
import re
import sys

def find_file_with_error():
    """
    Search for files that might be using get_cpu_info without importing it.
    Focus on files that might be involved in system initialization.
    """
    potential_files = [
        'cybex_pulse/web/api/system.py',
        'cybex_pulse/web/routes/dashboard.py',
        'cybex_pulse/core/app.py',
        'cybex_pulse/web/server.py'
    ]
    
    for file_path in potential_files:
        if not os.path.exists(file_path):
            continue
            
        with open(file_path, 'r') as f:
            content = f.read()
            
        # Check if file uses get_cpu_info but doesn't import it
        if 'get_cpu_info' in content and 'from cybex_pulse.utils.system_info import get_cpu_info' not in content:
            # If it imports get_all_system_info but not get_cpu_info directly
            if 'get_all_system_info' in content and 'get_cpu_info' in content:
                return file_path
                
    # If no specific file found, check all Python files in the project
    for root, _, files in os.walk('cybex_pulse'):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                
                if 'get_cpu_info' in content and 'from cybex_pulse.utils.system_info import get_cpu_info' not in content:
                    if 'import get_cpu_info' not in content:
                        return file_path
    
    return None

def fix_import_in_file(file_path):
    """
    Add the missing import to the file.
    """
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Check if the file already imports from system_info
    if 'from cybex_pulse.utils.system_info import' in content:
        # Add get_cpu_info to the existing import
        content = re.sub(
            r'from cybex_pulse.utils.system_info import (.*)',
            r'from cybex_pulse.utils.system_info import \1, get_cpu_info',
            content
        )
    else:
        # Add a new import statement after other imports
        import_section_end = 0
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if line.startswith('import ') or line.startswith('from '):
                import_section_end = i + 1
        
        if import_section_end > 0:
            lines.insert(import_section_end, 'from cybex_pulse.utils.system_info import get_cpu_info')
            content = '\n'.join(lines)
        else:
            # If no imports found, add at the top after docstring
            if '"""' in content:
                docstring_end = content.find('"""', content.find('"""') + 3) + 3
                content = content[:docstring_end] + '\nfrom cybex_pulse.utils.system_info import get_cpu_info\n' + content[docstring_end:]
            else:
                content = 'from cybex_pulse.utils.system_info import get_cpu_info\n' + content
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    return True

def main():
    print("Searching for files with missing get_cpu_info import...")
    file_to_fix = find_file_with_error()
    
    if file_to_fix:
        print(f"Found file with potential error: {file_to_fix}")
        if fix_import_in_file(file_to_fix):
            print(f"Successfully added missing import to {file_to_fix}")
            return 0
        else:
            print(f"Failed to fix import in {file_to_fix}")
            return 1
    else:
        print("No files found with the specific error pattern.")
        print("Creating a general fix module...")
        
        # Create a general fix module that can be imported
        with open('cybex_pulse/utils/cpu_info_fix.py', 'w') as f:
            f.write('''"""
CPU info fix module.
This module ensures that get_cpu_info is properly imported.
"""
from cybex_pulse.utils.system_info import get_cpu_info

# Re-export the function
__all__ = ['get_cpu_info']
''')
        
        print("Created cybex_pulse/utils/cpu_info_fix.py")
        print("You can now import get_cpu_info from this module as a workaround.")
        return 0

if __name__ == "__main__":
    sys.exit(main())
