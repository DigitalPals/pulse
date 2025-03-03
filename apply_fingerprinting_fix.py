#!/usr/bin/env python3
"""
Apply fingerprinting performance fixes to Cybex Pulse.

This script applies the optimizations from fix_fingerprinting.py to the running application.
"""
import os
import sys
import importlib
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """Apply the fingerprinting performance fixes."""
    logger.info("Applying fingerprinting performance fixes to Cybex Pulse...")
    
    # Add the current directory to the path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    
    try:
        # Import the fix module
        fix_module = importlib.import_module('fix_fingerprinting')
        
        # Apply all patches
        fix_module.apply_all_patches()
        
        logger.info("Fingerprinting performance fixes applied successfully")
        print("Fingerprinting performance fixes have been applied successfully.")
        print("The web interface should now be more responsive during fingerprinting operations.")
        
        return 0
    except ImportError as e:
        logger.error(f"Failed to import fix_fingerprinting module: {e}")
        print(f"Error: Failed to import fix_fingerprinting module: {e}")
        return 1
    except Exception as e:
        logger.error(f"Error applying fingerprinting performance fixes: {e}")
        print(f"Error: Failed to apply fingerprinting performance fixes: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())