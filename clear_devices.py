#!/usr/bin/env python3
"""
Script to clear all devices from the Cybex Pulse database.
"""
import argparse
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
logger = logging.getLogger("clear_devices")

def main():
    """Main function to clear all devices from the database."""
    parser = argparse.ArgumentParser(description="Clear all devices from the Cybex Pulse database")
    parser.add_argument("--confirm", action="store_true", 
                        help="Confirm deletion without prompt")
    args = parser.parse_args()
    
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
        
        # Check if the devices table has any entries
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM devices")
        count = cursor.fetchone()[0]
        
        if count == 0:
            logger.info("No devices found in database, nothing to clear.")
            return
        
        # Confirm before deletion if not already confirmed
        if not args.confirm:
            confirm = input(f"This will delete ALL {count} devices from the database. Are you sure? (y/N): ")
            if confirm.lower() != 'y':
                logger.info("Operation cancelled.")
                return
        
        # Clear all devices
        num_deleted = db.clear_all_devices()
        logger.info(f"Successfully deleted {num_deleted} devices from the database.")
    except Exception as e:
        logger.error(f"Error clearing devices: {e}")
        sys.exit(1)
    finally:
        db.close()

if __name__ == "__main__":
    main()