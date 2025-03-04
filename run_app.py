#!/usr/bin/env python3
# Dynamic wrapper to execute the application directly
import os
import sys

# Add the root directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Try to import from different approaches
try:
    # Try to run directly from the module
    from cybex_pulse.__main__ import main
    main()
except ImportError:
    try:
        # Try direct import of individual files
        import __main__
        __main__.main()
    except (ImportError, AttributeError):
        # Last resort - execute the main script directly
        try:
            with open(os.path.join(current_dir, '__main__.py'), 'r') as f:
                exec(f.read())
        except Exception as e:
            print(f"All execution methods failed: {e}")
            sys.exit(1)
