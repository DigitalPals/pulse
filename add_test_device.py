#!/usr/bin/env python3
"""
Script to add a test device to the Cybex Pulse database.
"""
import logging
import os
import sys
from pathlib import Path

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Now we can import from cybex_pulse
from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger("add_test_device")

def main():
    """Main function to add a test device to the database."""
    # Define default config and database paths
    config_path = Path("~/.cybex_pulse/config.json").expanduser()
    db_path = Path("~/.cybex_pulse/pulse.db").expanduser()
    
    # Load config to get database path if available
    if config_path.exists():
        try:
            config = Config(config_path)
            db_path_from_config = config.get("database", "path")
            if db_path_from_config:
                db_path = Path(db_path_from_config).expanduser()
        except Exception as e:
            logger.warning(f"Failed to load config, using default database path: {e}")
    
    logger.info(f"Using database at: {db_path}")
    
    # Initialize the database manager
    db = DatabaseManager(db_path)
    
    try:
        # Initialize the database to ensure tables exist
        db.initialize_database()
        
        # Add some test devices
        for i in range(5):
            mac = f"00:11:22:33:44:{i:02d}"
            ip = f"192.168.1.{10+i}"
            hostname = f"test-device-{i}"
            vendor = "Test Vendor"
            
            db.add_device(
                mac_address=mac,
                ip_address=ip,
                hostname=hostname,
                vendor=vendor,
                is_important=(i == 0),  # Make the first device important
                device_type="test",
                device_model=f"Model-{i}",
                device_manufacturer="Test Inc."
            )
            
        # List the devices that were added
        devices = db.get_all_devices()
        logger.info(f"Added {len(devices)} test devices to the database:")
        
        for device in devices:
            logger.info(f"  - {device['hostname']} ({device['ip_address']}, {device['mac_address']})")
            
    except Exception as e:
        logger.error(f"Error adding test devices: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()