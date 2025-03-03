#!/bin/bash
# Script to apply the fingerprinting performance fix to Cybex Pulse

echo "Applying fingerprinting performance fix to Cybex Pulse..."

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required but not found."
    exit 1
fi

# Run the fix script
python3 apply_fingerprinting_fix.py

# Check if the fix was applied successfully
if [ $? -eq 0 ]; then
    echo "Fingerprinting performance fix applied successfully!"
    echo "The web interface should now be more responsive during fingerprinting operations."
    echo ""
    echo "To test the fix, you can run:"
    echo "  python3 test_fingerprinting.py <ip_address> --compare"
    echo ""
    echo "For more information, see README_FINGERPRINTING_FIX.md"
else
    echo "Error: Failed to apply fingerprinting performance fix."
    echo "Please check the logs for more information."
    exit 1
fi

exit 0