"""
Main application module for Cybex Pulse.

This module contains the main application class for Cybex Pulse, responsible for:
- Initializing and coordinating all system components
- Managing scanning and monitoring threads
- Handling configuration updates
- Providing application lifecycle management
- Checking for application updates
"""
import logging
import threading
import time
from typing import Dict, List, Optional, Set, Tuple, Any, Callable

from cybex_pulse.core.alerting import AlertManager
from cybex_pulse.core.fingerprinting_manager import FingerprintingManager
from cybex_pulse.core.monitoring import InternetHealthMonitor, SecurityMonitor, WebsiteMonitor
from cybex_pulse.core.network_scanner import NetworkScanner
from cybex_pulse.core.thread_manager import ThreadManager
from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config
from cybex_pulse.utils.version_check import UpdateChecker
from cybex_pulse.web.server import WebServer


class CybexPulseApp:
    """Main application class for Cybex Pulse."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager, logger: logging.Logger):
        """Initialize the application.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logger
        
        # Initialize thread manager with config for debug logging
        self.thread_manager = ThreadManager(logger, config)
        
        # Initialize components
        self.alert_manager = AlertManager(config, db_manager, logger)
        self.fingerprinting_manager = FingerprintingManager(config, db_manager, logger)
        self.network_scanner = NetworkScanner(config, db_manager, logger)
        
        # Initialize monitoring features
        self.internet_health_monitor = InternetHealthMonitor(
            config, db_manager, logger, self.thread_manager, self.alert_manager
        )
        self.website_monitor = WebsiteMonitor(
            config, db_manager, logger, self.thread_manager, self.alert_manager
        )
        self.security_monitor = SecurityMonitor(
            config, db_manager, logger, self.thread_manager, self.alert_manager
        )
        
        # Initialize update checker
        self.update_checker = UpdateChecker(
            check_interval=3600,  # Check for updates every hour
            logger=logger
        )
        
        # Initialize web server if enabled
        self.web_server = None
        if config.get("web_interface", "enabled"):
            self.web_server = WebServer(config, db_manager, logger, main_app=self)
    
    def start(self) -> None:
        """Start the application."""
        self.logger.info("Starting Cybex Pulse application")
        
        # Start network scanner
        network_thread = self.thread_manager.start_thread(
            name="NetworkScanner",
            target=self._run_network_scanner
        )
        
        # Start web server if enabled
        if self.web_server:
            web_thread = self.thread_manager.start_thread(
                name="WebServer",
                target=self._run_web_server
            )
        
        # Start update checker
        self.update_checker.start_checker_thread()
        
        # Start optional monitoring features based on configuration
        self.start_monitoring_threads()
        
        # Wait for threads to complete (which they won't unless stop_event is set)
        while not self.thread_manager.global_stop_event.is_set():
            time.sleep(1)
    
    def start_monitoring_threads(self) -> None:
        """Start all monitoring threads based on current configuration."""
        self.logger.info("Starting monitoring threads based on configuration")
        
        # Start internet health check if enabled
        if self.internet_health_monitor.is_enabled():
            self.internet_health_monitor.start()
        
        # Start website monitoring if enabled
        if self.website_monitor.is_enabled():
            self.website_monitor.start()
        
        # Start security scanning if enabled
        if self.security_monitor.is_enabled():
            self.security_monitor.start()
    
    def update_monitoring_state(self) -> None:
        """Update the state of all monitoring threads based on current configuration."""
        self.logger.info("Updating monitoring threads state based on current configuration")
        
        # Dictionary mapping monitoring features to their enable checks
        monitoring_features = [
            self.internet_health_monitor,
            self.website_monitor,
            self.security_monitor
        ]
        
        # Update each monitoring feature based on configuration
        for feature in monitoring_features:
            if feature.is_enabled() and (not feature.thread or not feature.thread.is_alive()):
                self.logger.debug(f"Starting {feature.name} thread (was inactive but enabled in config)")
                feature.start()
            elif not feature.is_enabled() and feature.thread and feature.thread.is_alive():
                self.logger.debug(f"Stopping {feature.name} thread (was active but disabled in config)")
                feature.stop()
        
        # Update fingerprinting state
        self.fingerprinting_manager.update_fingerprinting_state()
    
    def cleanup(self) -> None:
        """Clean up resources before exiting."""
        self.logger.info("Cleaning up resources")
        
        # Stop update checker
        self.update_checker.stop_checker_thread()
        
        # Shutdown web server if it exists
        if self.web_server:
            try:
                self.logger.info("Shutting down web server...")
                self.web_server.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down web server: {e}")
        
        # Shutdown fingerprinting manager to properly close HTTP connections
        try:
            self.logger.info("Shutting down fingerprinting manager...")
            self.fingerprinting_manager.shutdown()
        except Exception as e:
            self.logger.error(f"Error shutting down fingerprinting manager: {e}")
        
        # Stop all threads
        self.thread_manager.stop_all_threads()
        
        # Close database connection
        self.db_manager.close()
        self.logger.info("Cleanup complete")
    
    def _run_network_scanner(self) -> None:
        """Run the network scanner in a loop."""
        self.logger.info("Starting network scanner")
        
        # Counter for periodic checks
        cycle_count = 0
        
        while not self.thread_manager.global_stop_event.is_set():
            try:
                # Run network scan
                self.logger.info("Starting network scan cycle")
                self.network_scanner.scan()
                self.logger.info("Network scan cycle completed")
                
                # Increment cycle count
                cycle_count += 1
                
                # Every 5 cycles, check for deadlocks and resource leaks if debug logging is enabled
                if cycle_count % 5 == 0 and self.config.get("general", "debug_logging", False):
                    self.thread_manager.check_for_deadlocks()
                    self.thread_manager.check_for_resource_leaks()
                
                # Sleep for the configured interval
                scan_interval = self.config.get("general", "scan_interval")
                self.logger.info(f"Sleeping for {scan_interval} seconds until next network scan")
                
                # Use thread manager's sleep with check
                if not self.thread_manager.sleep_with_check(
                    scan_interval,
                    self.thread_manager.global_stop_event
                ):
                    break
            except Exception as e:
                self.logger.error(f"Error in network scanner: {e}")
                # Sleep for a short time before retrying
                if not self.thread_manager.sleep_with_check(
                    10,
                    self.thread_manager.global_stop_event
                ):
                    break
    
    def _run_web_server(self) -> None:
        """Run the web server."""
        self.logger.info("Starting web server")
        
        try:
            self.web_server.start()
        except Exception as e:
            self.logger.error(f"Error in web server: {e}")
    
    def update_application(self, progress_callback: Optional[Callable] = None) -> Tuple[bool, Optional[str]]:
        """Handle the application update process.
        
        Args:
            progress_callback: Optional callback function to receive real-time progress updates
            
        Returns:
            tuple: (success, error_message)
        """
        self.logger.info("Starting application update process")
        
        if progress_callback:
            progress_callback("Starting update process...")
        
        # Check for updates first
        if progress_callback:
            progress_callback("Checking for updates...")
            
        update_available, error = self.update_checker.check_for_updates()
        if error:
            if progress_callback:
                progress_callback(f"Failed to check for updates: {error}", is_error=True)
            return False, f"Failed to check for updates: {error}"
            
        if not update_available:
            if progress_callback:
                progress_callback("No updates available", is_error=False)
            return False, "No updates available"
            
        # Perform update
        if progress_callback:
            progress_callback("Updates available, starting update process...")
            
        success, error = self.update_checker.update_application(progress_callback)
        if not success:
            return False, f"Update failed: {error}"
            
        self.logger.info("Application updated successfully, preparing to restart")
        
        if progress_callback:
            progress_callback("Update successful, preparing to restart...")
        
        # Schedule restart
        restart_thread = threading.Thread(
            target=self._delayed_restart,
            name="RestartThread",
            args=(progress_callback,),
            daemon=True
        )
        restart_thread.start()
        
        return True, "Update successful. Application will restart shortly."
        
    def _delayed_restart(self, progress_callback: Optional[Callable] = None, delay: int = 3) -> None:
        """Restart the application after a short delay.
        
        Args:
            progress_callback: Optional callback function to receive real-time progress updates
            delay: Delay in seconds before restarting
        """
        self.logger.info(f"Application will restart in {delay} seconds")
        
        if progress_callback:
            progress_callback(f"Application will restart in {delay} seconds...")
        
        # Count down
        for i in range(delay, 0, -1):
            if progress_callback:
                progress_callback(f"Restarting in {i} seconds...")
            time.sleep(1)
        
        if progress_callback:
            progress_callback("Cleaning up resources before restart...")
            
        # Clean up resources
        self.cleanup()
        
        if progress_callback:
            progress_callback("Restarting application. The console will reconnect automatically when the system is back online...")
            
        try:
            # Restart the application
            self.update_checker.restart_application()
        except Exception as e:
            self.logger.error(f"Error during restart: {e}")
            if progress_callback:
                progress_callback(f"Error during restart: {e}. Please restart the application manually.", is_error=True)
                
            # Import traceback for detailed error information
            import traceback
            self.logger.error(f"Restart error details: {traceback.format_exc()}")