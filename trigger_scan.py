#!/usr/bin/env python3
"""
Script to manually trigger a security scan for all devices in the database.
"""
import json
import logging
import sys
from pathlib import Path

# Add the cybex_pulse directory to the Python path
sys.path.append(str(Path.cwd()))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("cybex_pulse.manual_scan")

try:
    # Import required modules from cybex_pulse
    from cybex_pulse.database.db_manager import DatabaseManager
    from cybex_pulse.utils.config import Config
    
    # Initialize configuration
    config_dir = Path.home() / ".cybex_pulse"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = config_dir / "config.json"
    db_path = config_dir / "cybex_pulse.db"
    
    logger.info(f"Using config file: {config_path}")
    logger.info(f"Using database file: {db_path}")
    
    # Initialize database
    db_manager = DatabaseManager(db_path)
    
    # Load configuration
    config = Config(config_path)
    
    # Check if security scanning is enabled
    security_enabled = config.get("monitoring", "security", {}).get("enabled", False)
    logger.info(f"Security scanning is {'enabled' if security_enabled else 'disabled'} in config")
    
    # Get all devices from database
    devices = db_manager.get_all_devices()
    logger.info(f"Found {len(devices)} devices in database")
    
    if not devices:
        logger.warning("No devices found in database. Nothing to scan.")
        sys.exit(0)
    
    # Try to import nmap
    try:
        import nmap
        logger.info("Successfully imported python-nmap")
    except ImportError:
        logger.error("python-nmap not installed. Security scanning disabled.")
        sys.exit(1)
    
    # Run security scan for each device
    for device in devices:
        try:
            ip_address = device["ip_address"]
            if not ip_address:
                logger.warning(f"Device {device['id']} has no IP address. Skipping.")
                continue
            
            logger.info(f"Running security scan for device: {ip_address}")
            
            # Initialize scanner
            nm = nmap.PortScanner()
            
            # Run scan
            logger.info(f"Starting nmap scan for {ip_address}")
            nm.scan(ip_address, arguments="-F")  # Fast scan
            
            # Process results
            if ip_address in nm.all_hosts():
                open_ports = []
                for proto in nm[ip_address].all_protocols():
                    ports = sorted(nm[ip_address][proto].keys())
                    for port in ports:
                        state = nm[ip_address][proto][port]["state"]
                        if state == "open":
                            service = nm[ip_address][proto][port].get("name", "unknown")
                            open_ports.append({
                                "port": port,
                                "protocol": proto,
                                "service": service
                            })
                
                # Save to database
                db_manager.add_security_scan(
                    device["id"],
                    open_ports=json.dumps(open_ports)
                )
                
                # Log results
                logger.info(f"Security scan for {ip_address} found {len(open_ports)} open ports")
                if open_ports:
                    logger.info(f"Open ports: {json.dumps(open_ports, indent=2)}")
            else:
                logger.warning(f"Device {ip_address} not found in nmap scan results")
        except Exception as e:
            logger.error(f"Error scanning device {device.get('ip_address', 'unknown')}: {e}")
    
    logger.info("Manual security scan completed")

except Exception as e:
    logger.error(f"Error during manual security scan: {e}")
    sys.exit(1)