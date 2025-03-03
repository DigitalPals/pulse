#!/usr/bin/env python3
"""
Test script for the optimized fingerprinting service.

This script tests the performance of the fingerprinting service
before and after applying the optimizations.
"""
import os
import sys
import time
import logging
import argparse
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the cybex_pulse modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_fingerprinting(ip_address: str, apply_fix: bool = False):
    """
    Test the fingerprinting service on a single IP address.
    
    Args:
        ip_address: The IP address to fingerprint
        apply_fix: Whether to apply the performance fixes before testing
    """
    try:
        # Import the necessary modules
        from cybex_pulse.fingerprinting.scanner import DeviceFingerprinter
        
        # Apply the fix if requested
        if apply_fix:
            logger.info("Applying performance fixes before testing...")
            import fix_fingerprinting
            fix_fingerprinting.apply_all_patches()
            logger.info("Performance fixes applied")
        
        # Create a fingerprinter instance
        logger.info("Creating fingerprinter instance...")
        fingerprinter = DeviceFingerprinter(max_threads=10, timeout=2)
        
        # Generate a random MAC address for testing
        import random
        mac_bytes = [random.randint(0, 255) for _ in range(6)]
        mac_address = ':'.join([f'{b:02x}' for b in mac_bytes])
        
        # Measure the time taken to fingerprint the device
        logger.info(f"Starting fingerprinting of {ip_address} ({mac_address})...")
        start_time = time.time()
        
        result = fingerprinter.fingerprint_device(ip_address, mac_address)
        
        end_time = time.time()
        elapsed_time = end_time - start_time
        
        # Print the results
        logger.info(f"Fingerprinting completed in {elapsed_time:.2f} seconds")
        
        # Check if the device was identified
        identification = result.get('identification', [])
        if identification:
            best_match = identification[0]
            logger.info(f"Device identified as: {best_match.get('manufacturer', 'Unknown')} {best_match.get('model', 'Unknown')}")
            logger.info(f"Device type: {best_match.get('device_type', 'Unknown')}")
            logger.info(f"Confidence: {best_match.get('confidence', 0):.2f}")
        else:
            logger.info("Device not identified")
        
        # Print the open ports
        open_ports = result.get('open_ports', [])
        logger.info(f"Open ports: {', '.join(map(str, open_ports)) if open_ports else 'None'}")
        
        return elapsed_time
    
    except Exception as e:
        logger.error(f"Error testing fingerprinting: {e}")
        return None

def main():
    """Main function to run the test."""
    parser = argparse.ArgumentParser(description='Test the fingerprinting service performance')
    parser.add_argument('ip_address', help='IP address to fingerprint')
    parser.add_argument('--apply-fix', action='store_true', help='Apply performance fixes before testing')
    parser.add_argument('--compare', action='store_true', help='Compare performance with and without fixes')
    
    args = parser.parse_args()
    
    if args.compare:
        # Test without fixes
        logger.info("Testing fingerprinting WITHOUT performance fixes...")
        time_without_fix = test_fingerprinting(args.ip_address, apply_fix=False)
        
        # Test with fixes
        logger.info("\nTesting fingerprinting WITH performance fixes...")
        time_with_fix = test_fingerprinting(args.ip_address, apply_fix=True)
        
        # Compare results
        if time_without_fix is not None and time_with_fix is not None:
            improvement = (time_without_fix - time_with_fix) / time_without_fix * 100
            logger.info(f"\nPerformance comparison:")
            logger.info(f"Time without fixes: {time_without_fix:.2f} seconds")
            logger.info(f"Time with fixes: {time_with_fix:.2f} seconds")
            logger.info(f"Improvement: {improvement:.2f}%")
    else:
        # Just run the test once
        test_fingerprinting(args.ip_address, apply_fix=args.apply_fix)

if __name__ == "__main__":
    main()