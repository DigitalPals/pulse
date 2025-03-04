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
from cybex_pulse.utils.version_manager import version_manager

def setup_logging():
    """Configure application logging."""
    # Try to use /var/log/cybex_pulse if running as a service, otherwise fallback to home directory
    if os.access('/var/log', os.W_OK):
        log_dir = Path('/var/log/cybex_pulse')
    else:
        log_dir = Path.home() / ".cybex_pulse" / "logs"
    
    # Create log directory if it doesn't exist
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        # If we can't create the log directory, use stderr only
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stderr)]
        )
        logger = logging.getLogger("cybex_pulse")
        logger.warning("Could not create log directory. Logging to stderr only.")
        return logger
    
    log_file = log_dir / "cybex_pulse.log"
    
    try:
        file_handler = logging.FileHandler(log_file)
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[
                file_handler,
                logging.StreamHandler(sys.stdout)
            ]
        )
    except (PermissionError, OSError):
        # If we can't write to the log file, use stderr only
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler(sys.stderr)]
        )
        logger = logging.getLogger("cybex_pulse")
        logger.warning(f"Could not write to log file {log_file}. Logging to stderr only.")
        return logger
    
    return logging.getLogger("cybex_pulse")

def main():
    """Main function to start the Cybex Pulse application."""
    # Explicitly import os inside the function to avoid any namespace issues
    import os
    from pathlib import Path
    
    logger = setup_logging()
    
    # Get version information
    try:
        version = version_manager.get_version()
        is_dev = version_manager.is_development_version()
        last_modified = version_manager.get_last_modified()
        
        logger.info("Starting Cybex Pulse v%s", version)
        
        if last_modified:
            from datetime import datetime
            modified_date = datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S')
            logger.info("Version last updated: %s", modified_date)
        
        if is_dev:
            logger.info("This is a development version")
    except Exception as e:
        # If there's an error with version detection, log it but continue
        logger.error(f"Error determining version: {e}")
        logger.info("Starting Cybex Pulse")
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Cybex Pulse - Home Network Monitoring")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--reset", action="store_true", help="Reset configuration and start setup wizard")
    parser.add_argument("--console-setup", action="store_true", help="Use console setup wizard instead of web interface")
    args = parser.parse_args()
    
    # Initialize configuration
    # Try to use /var/lib/cybex_pulse if running as a service, otherwise fallback to home directory
    if os.access('/var/lib', os.W_OK):
        data_dir = Path('/var/lib/cybex_pulse')
    else:
        data_dir = Path.home() / ".cybex_pulse"
    
    logger.info(f"Using data directory: {data_dir}")
    
    # Create data directory if it doesn't exist
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
    except (PermissionError, OSError):
        logger.error("Could not create data directory. Using home directory as fallback.")
        data_dir = Path.home() / ".cybex_pulse"
        data_dir.mkdir(parents=True, exist_ok=True)
    
    config_path = args.config if args.config else data_dir / "config.json"
    db_path = data_dir / "cybex_pulse.db"
    
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
        
        # Use a more robust termination approach
        try:
            # First set the stop event to signal threads to stop gracefully
            app.thread_manager.global_stop_event.set()
            
            # Give threads a short time to respond to the stop event
            import time
            import sys  # Import sys module locally to ensure it's available
            time.sleep(0.5)
            
            # Then call cleanup to properly terminate resources
            app.cleanup()
            
            # Reset terminal to canonical mode
            import termios
            import os
            try:
                # Reset terminal to initial state
                fd = sys.stdin.fileno()
                mode = termios.tcgetattr(fd)
                mode[3] = mode[3] | termios.ECHO | termios.ICANON
                termios.tcsetattr(fd, termios.TCSAFLUSH, mode)
                
                # More thorough terminal reset
                os.system('stty sane')  # Reset terminal settings
                
                # Print a newline and flush to ensure prompt appears
                sys.stdout.write("\n")
                sys.stdout.flush()
                
                # Force shell to redisplay prompt by sending a harmless command
                os.system('tput smam')  # Enable automatic margins
                os.system('tput cnorm')  # Make cursor visible
            except Exception as e:
                logger.debug(f"Error resetting terminal: {e}")
                
            logger.info("Application shutdown complete")
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            
        # Force exit if cleanup doesn't complete
        sys.exit(0)
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Ensure terminal is reset on exit
    import atexit
    def reset_terminal():
        try:
            import os
            import sys
            
            # More thorough terminal reset
            os.system('stty sane')  # Reset terminal settings
            
            # Print a newline and flush to ensure prompt appears
            sys.stdout.write("\n")
            sys.stdout.flush()
            
            # Force shell to redisplay prompt
            os.system('tput smam')  # Enable automatic margins
            os.system('tput cnorm')  # Make cursor visible
        except Exception:
            pass
    atexit.register(reset_terminal)
    
    try:
        app.start()
    except KeyboardInterrupt:
        # This should not be needed due to the signal handler, but keep it as a fallback
        logger.info("Application terminated by user")
        # Reset terminal directly here as well
        try:
            import os
            import sys
            
            # More thorough terminal reset
            os.system('stty sane')  # Reset terminal settings
            
            # Print a newline and flush to ensure prompt appears
            sys.stdout.write("\n")
            sys.stdout.flush()
            
            # Force shell to redisplay prompt
            os.system('tput smam')  # Enable automatic margins
            os.system('tput cnorm')  # Make cursor visible
        except Exception as e:
            logger.debug(f"Error resetting terminal: {e}")
    except Exception as e:
        logger.exception("Unhandled exception: %s", str(e))
        return 1
    finally:
        app.cleanup()
        # One final attempt to reset the terminal
        try:
            import os
            import sys
            
            # More thorough terminal reset
            os.system('stty sane')  # Reset terminal settings
            
            # Print a newline and flush to ensure prompt appears
            sys.stdout.write("\n")
            sys.stdout.flush()
            
            # Force shell to redisplay prompt
            os.system('tput smam')  # Enable automatic margins
            os.system('tput cnorm')  # Make cursor visible
        except Exception:
            pass
    
    return 0

if __name__ == "__main__":
    sys.exit(main())