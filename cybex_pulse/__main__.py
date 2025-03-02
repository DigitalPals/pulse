#!/usr/bin/env python3
"""
Main entry point for Cybex Pulse application.
"""
import argparse
import logging
import signal
import sys
import os
from pathlib import Path

from cybex_pulse.core.setup_wizard import SetupWizard
from cybex_pulse.core.app import CybexPulseApp
from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config

def setup_logging():
    """Configure application logging."""
    log_dir = Path.home() / ".cybex_pulse" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / "cybex_pulse.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger("cybex_pulse")

def main():
    """Main function to start the Cybex Pulse application."""
    logger = setup_logging()
    logger.info("Starting Cybex Pulse v%s", __import__("cybex_pulse").__version__)
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Cybex Pulse - Home Network Monitoring")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--reset", action="store_true", help="Reset configuration and start setup wizard")
    parser.add_argument("--console-setup", action="store_true", help="Use console setup wizard instead of web interface")
    args = parser.parse_args()
    
    # Initialize configuration
    config_dir = Path.home() / ".cybex_pulse"
    config_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = args.config if args.config else config_dir / "config.json"
    db_path = config_dir / "cybex_pulse.db"
    
    # Initialize database
    db_manager = DatabaseManager(db_path)
    db_manager.initialize_database()
    
    # Load or create configuration
    config = Config(config_path)
    
    # Only run the setup wizard in console mode if explicitly requested with --console-setup
    if args.reset or (args.console_setup and not config.is_configured()):
        logger.info("Running console setup wizard")
        wizard = SetupWizard(config, db_manager)
        if not wizard.run():
            logger.error("Setup wizard was cancelled. Exiting.")
            return 1
    # Otherwise, the web interface will handle the setup
    
    # Start the application
    app = CybexPulseApp(config, db_manager, logger)
    
    # Set up signal handler for graceful termination
    def signal_handler(sig, frame):
        logger.info("Application terminated by user (SIGINT/SIGTERM)")
        app.stop_event.set()  # Signal threads to stop
        app.cleanup()
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        app.start()
    except KeyboardInterrupt:
        # This should not be needed due to the signal handler, but keep it as a fallback
        logger.info("Application terminated by user")
    except Exception as e:
        logger.exception("Unhandled exception: %s", str(e))
        return 1
    finally:
        app.cleanup()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())