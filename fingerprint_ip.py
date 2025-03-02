#!/usr/bin/env python3
"""
Script to manually trigger fingerprinting for a specific IP address.
"""
import argparse
import logging
import sys
import time
import json
from pathlib import Path

# Add the project directory to the Python path
sys.path.append(str(Path(__file__).parent))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cybex_pulse.manual_fingerprint")

try:
    # Import required modules
    from cybex_pulse.fingerprinting.scanner import DeviceFingerprinter
    from cybex_pulse.database.db_manager import DatabaseManager
    from cybex_pulse.utils.config import Config
    
    def clear_device_fingerprint(db_manager, mac_address):
        """Clear existing fingerprint data for a device."""
        device_info = {
            'device_type': '',
            'device_model': '',
            'device_manufacturer': '',
            'fingerprint_confidence': 0.0,
            'fingerprint_date': 0
        }
        db_manager.update_device_metadata(mac_address, device_info)
        logger.info(f"Cleared previous fingerprint data for {mac_address}")
    
    def main():
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='Manually fingerprint a specific IP address')
        parser.add_argument('ip_address', help='IP address to fingerprint')
        parser.add_argument('--mac', help='MAC address (optional, will be auto-detected if possible)')
        parser.add_argument('--threads', type=int, default=10, help='Maximum number of threads (default: 10)')
        parser.add_argument('--timeout', type=int, default=3, help='Timeout in seconds (default: 3)')
        parser.add_argument('--clear', action='store_true', help='Clear existing fingerprint data before scanning')
        parser.add_argument('--debug', action='store_true', help='Show detailed HTTP headers and content')
        args = parser.parse_args()
        
        # Initialize configuration
        config_dir = Path.home() / ".cybex_pulse"
        config_dir.mkdir(parents=True, exist_ok=True)
        config_path = config_dir / "config.json"
        db_path = config_dir / "cybex_pulse.db"
        
        logger.info(f"Using config file: {config_path}")
        logger.info(f"Using database file: {db_path}")
        
        # Initialize database
        db_manager = DatabaseManager(db_path)
        config = Config(config_path)
        
        # Initialize the fingerprinting engine with fresh cache
        logger.info(f"Initializing fingerprinting engine with {args.threads} threads and {args.timeout}s timeout")
        fingerprinter = DeviceFingerprinter(max_threads=args.threads, timeout=args.timeout)
        
        # Clear fingerprinting cache in memory
        fingerprinter.fingerprinted_mac_addresses.clear()
        logger.info("Cleared in-memory fingerprinting cache")
        
        # If MAC address not provided, try to look it up in the database
        mac_address = args.mac
        found_in_db = False
        if not mac_address:
            # Try to find a device with the given IP address in the database
            devices = db_manager.get_all_devices()
            for device in devices:
                if device.get('ip_address') == args.ip_address:
                    mac_address = device['mac_address']
                    found_in_db = True
                    logger.info(f"Found MAC address {mac_address} for IP {args.ip_address} in database")
                    break
            
            if not mac_address:
                # Generate a placeholder MAC if not found
                import random
                mac_address = f"00:00:00:{random.randint(0, 255):02x}:{random.randint(0, 255):02x}:{random.randint(0, 255):02x}"
                logger.warning(f"MAC address not provided and not found in database. Using placeholder: {mac_address}")
        
        # Clear existing fingerprint if requested
        if args.clear and found_in_db:
            clear_device_fingerprint(db_manager, mac_address)
        
        # Prepare device data for fingerprinting
        device_to_fingerprint = {
            "ip_address": args.ip_address,
            "mac_address": mac_address
        }
        
        # Run the fingerprinting operation
        logger.info(f"Starting fingerprinting for {args.ip_address} ({mac_address})")
        results = fingerprinter.fingerprint_network([device_to_fingerprint], force_scan=True)
        
        if results and len(results) > 0:
            result = results[0]
            
            # Process identification results
            identification = result.get('identification', [])
            if identification:
                logger.info(f"Found {len(identification)} potential matches:")
                
                for i, match in enumerate(identification[:5], 1):  # Show top 5 matches
                    confidence = match.get('confidence', 0) * 100
                    logger.info(f"{i}. {match.get('manufacturer', '')} {match.get('model', '')} "
                               f"({match.get('device_type', '')}) - "
                               f"Confidence: {confidence:.1f}%")
                    
                # If found in database, update the device info
                if found_in_db:
                    best_match = identification[0]
                    confidence = best_match.get('confidence', 0)
                    
                    # Get confidence threshold from config
                    threshold = float(config.get("fingerprinting", "confidence_threshold", default=0.5))
                    logger.info(f"Confidence threshold: {threshold:.2f}")
                    
                    if confidence >= threshold:
                        device_info = {
                            'device_type': best_match.get('device_type', ''),
                            'device_model': best_match.get('model', ''),
                            'device_manufacturer': best_match.get('manufacturer', ''),
                            'fingerprint_confidence': confidence,
                            'fingerprint_date': int(time.time())
                        }
                        db_manager.update_device_metadata(mac_address, device_info)
                        logger.info(f"Updated device information in database with confidence {confidence:.2f}")
                    else:
                        logger.info(f"Best match confidence ({confidence:.2f}) below threshold ({threshold:.2f}), not updating database")
            else:
                logger.info("No matches found for the device")
                
            # Print the data collected for troubleshooting
            logger.info("\nFingerprinting data collected:")
            logger.info(f"Open ports: {result.get('open_ports', [])}")
            
            if 'http_headers' in result and result['http_headers']:
                headers = result['http_headers']
                logger.info(f"HTTP headers: Found {len(headers)} headers")
                
                if args.debug:
                    logger.info("HTTP Headers details:")
                    for key, value in headers.items():
                        logger.info(f"  {key}: {value}")
                    
                    # Show content-related headers specifically for debugging Unraid detection
                    for key in headers:
                        if key.startswith('X-Content-'):
                            logger.info(f"Content header: {key}={headers[key]}")
                    
                    if 'X-Page-Title' in headers:
                        logger.info(f"Page title: {headers['X-Page-Title']}")
            
            if 'snmp_data' in result and result['snmp_data']:
                logger.info(f"SNMP data: Found {len(result['snmp_data'])} entries")
                
            if 'mdns_data' in result and result['mdns_data']:
                logger.info(f"mDNS data: Found {len(result['mdns_data'])} entries")
        else:
            logger.error(f"Fingerprinting failed - no results returned")
    
    if __name__ == "__main__":
        main()
        
except ImportError as e:
    logger.error(f"Error importing required modules: {e}")
    sys.exit(1)
except Exception as e:
    logger.error(f"Unexpected error during fingerprinting: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)