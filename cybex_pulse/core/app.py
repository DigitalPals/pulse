"""
Main application module for Cybex Pulse.

This module contains the main application class for Cybex Pulse, responsible for:
- Initializing and coordinating all system components
- Managing scanning and monitoring threads
- Handling configuration updates
- Providing application lifecycle management
- Checking for application updates
"""
import json
import logging
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Any

from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config
from cybex_pulse.core.network_scanner import NetworkScanner
from cybex_pulse.core.alerting import AlertManager
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
        
        # Initialize components
        self.network_scanner = NetworkScanner(config, db_manager, logger)
        self.alert_manager = AlertManager(config, db_manager, logger)
        
        # Initialize update checker
        self.update_checker = UpdateChecker(
            check_interval=3600,  # Check for updates every hour
            logger=logger
        )
        
        # Initialize web server if enabled
        self.web_server = None
        if config.get("web_interface", "enabled"):
            self.web_server = WebServer(config, db_manager, logger, main_app=self)
        
        # Initialize threads
        self.threads = []
        self.thread_stop_events = {}  # Individual stop events for each thread
        self.stop_event = threading.Event()
        
        # Track active monitoring threads
        self.health_check_thread = None
        self.website_monitoring_thread = None
        self.security_scanning_thread = None
    
    def start(self) -> None:
        """Start the application."""
        self.logger.info("Starting Cybex Pulse application")
        
        # Start network scanner
        network_thread = threading.Thread(
            target=self._run_network_scanner,
            name="NetworkScanner"
        )
        network_thread.daemon = True
        network_thread.start()
        self.threads.append(network_thread)
        
        # Start web server if enabled
        if self.web_server:
            web_thread = threading.Thread(
                target=self._run_web_server,
                name="WebServer"
            )
            web_thread.daemon = True
            web_thread.start()
            self.threads.append(web_thread)
        
        # Start update checker
        self.update_checker.start_checker_thread()
        
        # Start optional monitoring features based on configuration
        self.start_monitoring_threads()
        
        # Wait for threads to complete (which they won't unless stop_event is set)
        while not self.stop_event.is_set():
            time.sleep(1)
    
    def start_monitoring_threads(self) -> None:
        """Start all monitoring threads based on current configuration."""
        self.logger.info("Starting monitoring threads based on configuration")
        
        # Start internet health check if enabled
        if self.config.get("monitoring", "internet_health", {}).get("enabled", False):
            self.start_health_check()
        
        # Start website monitoring if enabled
        if self.config.get("monitoring", "websites", {}).get("enabled", False):
            self.start_website_monitoring()
        
        # Start security scanning if enabled
        if self.config.get("monitoring", "security", {}).get("enabled", False):
            self.start_security_scanning()
            
    def start_health_check(self) -> None:
        """Start the internet health check thread."""
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.logger.info("Health check thread already running")
            return
            
        self.logger.info("Starting health check thread")
        # Create a dedicated stop event for this thread
        health_stop_event = threading.Event()
        self.thread_stop_events["health_check"] = health_stop_event
        
        self.health_check_thread = threading.Thread(
            target=self._run_internet_health_check,
            name="InternetHealthCheck",
            args=(health_stop_event,)
        )
        self.health_check_thread.daemon = True
        self.health_check_thread.start()
        self.threads.append(self.health_check_thread)
        
    def stop_health_check(self) -> None:
        """Stop the internet health check thread."""
        if not self.health_check_thread or not self.health_check_thread.is_alive():
            self.logger.info("No health check thread running to stop")
            return
            
        self.logger.info("Stopping health check thread")
        # Signal the thread to stop
        if "health_check" in self.thread_stop_events:
            self.thread_stop_events["health_check"].set()
            
        # Wait for thread to terminate
        if self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=1.0)
            if self.health_check_thread.is_alive():
                self.logger.warning("Health check thread did not terminate gracefully")
                
        # Remove from active threads list
        if self.health_check_thread in self.threads:
            self.threads.remove(self.health_check_thread)
        self.health_check_thread = None
        
    def start_website_monitoring(self) -> None:
        """Start the website monitoring thread."""
        if self.website_monitoring_thread and self.website_monitoring_thread.is_alive():
            self.logger.info("Website monitoring thread already running")
            return
            
        self.logger.info("Starting website monitoring thread")
        # Create a dedicated stop event for this thread
        website_stop_event = threading.Event()
        self.thread_stop_events["website_monitoring"] = website_stop_event
        
        self.website_monitoring_thread = threading.Thread(
            target=self._run_website_monitoring,
            name="WebsiteMonitoring",
            args=(website_stop_event,)
        )
        self.website_monitoring_thread.daemon = True
        self.website_monitoring_thread.start()
        self.threads.append(self.website_monitoring_thread)
        
    def stop_website_monitoring(self) -> None:
        """Stop the website monitoring thread."""
        if not self.website_monitoring_thread or not self.website_monitoring_thread.is_alive():
            self.logger.info("No website monitoring thread running to stop")
            return
            
        self.logger.info("Stopping website monitoring thread")
        # Signal the thread to stop
        if "website_monitoring" in self.thread_stop_events:
            self.thread_stop_events["website_monitoring"].set()
            
        # Wait for thread to terminate
        if self.website_monitoring_thread.is_alive():
            self.website_monitoring_thread.join(timeout=1.0)
            if self.website_monitoring_thread.is_alive():
                self.logger.warning("Website monitoring thread did not terminate gracefully")
                
        # Remove from active threads list
        if self.website_monitoring_thread in self.threads:
            self.threads.remove(self.website_monitoring_thread)
        self.website_monitoring_thread = None
        
    def start_security_scanning(self) -> None:
        """Start the security scanning thread."""
        if self.security_scanning_thread and self.security_scanning_thread.is_alive():
            self.logger.info("Security scanning thread already running")
            return
            
        self.logger.info("Starting security scanning thread")
        # Create a dedicated stop event for this thread
        security_stop_event = threading.Event()
        self.thread_stop_events["security_scanning"] = security_stop_event
        
        self.security_scanning_thread = threading.Thread(
            target=self._run_security_scanning,
            name="SecurityScanning",
            args=(security_stop_event,)
        )
        self.security_scanning_thread.daemon = True
        self.security_scanning_thread.start()
        self.threads.append(self.security_scanning_thread)
        
    def stop_security_scanning(self) -> None:
        """Stop the security scanning thread."""
        if not self.security_scanning_thread or not self.security_scanning_thread.is_alive():
            self.logger.info("No security scanning thread running to stop")
            return
            
        self.logger.info("Stopping security scanning thread")
        # Signal the thread to stop
        if "security_scanning" in self.thread_stop_events:
            self.thread_stop_events["security_scanning"].set()
            
        # Wait for thread to terminate
        if self.security_scanning_thread.is_alive():
            self.security_scanning_thread.join(timeout=1.0)
            if self.security_scanning_thread.is_alive():
                self.logger.warning("Security scanning thread did not terminate gracefully")
                
        # Remove from active threads list
        if self.security_scanning_thread in self.threads:
            self.threads.remove(self.security_scanning_thread)
        self.security_scanning_thread = None
            
    def update_monitoring_state(self) -> None:
        """Update the state of all monitoring threads based on current configuration."""
        self.logger.info("Updating monitoring threads state based on current configuration")
        
        # Dictionary mapping feature names to their enable checks and start/stop methods
        monitoring_features = {
            "health_check": {
                "enabled": self.config.get("monitoring", "internet_health", {}).get("enabled", False),
                "thread": self.health_check_thread,
                "start": self.start_health_check,
                "stop": self.stop_health_check
            },
            "website_monitoring": {
                "enabled": self.config.get("monitoring", "websites", {}).get("enabled", False),
                "thread": self.website_monitoring_thread,
                "start": self.start_website_monitoring,
                "stop": self.stop_website_monitoring
            },
            "security_scanning": {
                "enabled": self.config.get("monitoring", "security", {}).get("enabled", False),
                "thread": self.security_scanning_thread,
                "start": self.start_security_scanning,
                "stop": self.stop_security_scanning
            }
        }
        
        # Update each monitoring feature based on configuration
        for feature_name, feature in monitoring_features.items():
            if feature["enabled"] and (not feature["thread"] or not feature["thread"].is_alive()):
                self.logger.debug(f"Starting {feature_name} thread (was inactive but enabled in config)")
                feature["start"]()
            elif not feature["enabled"] and feature["thread"] and feature["thread"].is_alive():
                self.logger.debug(f"Stopping {feature_name} thread (was active but disabled in config)")
                feature["stop"]()
        
        # Update fingerprinting state in network scanner
        self.update_fingerprinting_state()
    
    def update_fingerprinting_state(self) -> None:
        """Update the fingerprinting state in the network scanner based on current configuration."""
        fingerprinting_enabled = self.config.get("fingerprinting", "enabled", default=False)
        
        # Check if fingerprinting configuration has changed
        if self.network_scanner.fingerprinter is None and fingerprinting_enabled:
            self.logger.info("Fingerprinting enabled, initializing fingerprinter")
            try:
                from cybex_pulse.fingerprinting.scanner import DeviceFingerprinter
                
                # Get configuration values with proper defaults
                max_threads = int(self.config.get("fingerprinting", "max_threads", default=10))
                timeout = int(self.config.get("fingerprinting", "timeout", default=2))
                
                # Initialize fingerprinter with proper logging
                self.logger.info(f"Creating DeviceFingerprinter with max_threads={max_threads}, timeout={timeout}")
                self.network_scanner.fingerprinter = DeviceFingerprinter(
                    max_threads=max_threads,
                    timeout=timeout
                )
                
                # No need to log again, the fingerprinter constructor already logs this
                # self.logger.info(f"Device fingerprinting enabled with {self.network_scanner.fingerprinter.engine.get_signature_count()} signatures")
            except Exception as e:
                self.logger.error(f"Failed to initialize device fingerprinter: {e}")
        elif self.network_scanner.fingerprinter is not None and not fingerprinting_enabled:
            self.logger.info("Fingerprinting disabled, removing fingerprinter")
            self.network_scanner.fingerprinter = None
            
    def cleanup(self) -> None:
        """Clean up resources before exiting."""
        self.logger.info("Cleaning up resources")
        
        # Signal all threads to stop
        self.stop_event.set()
        for event in self.thread_stop_events.values():
            event.set()
        
        # Stop update checker
        self.update_checker.stop_checker_thread()
        
        # Shutdown web server if it exists
        if self.web_server:
            try:
                self.logger.info("Shutting down web server...")
                self.web_server.shutdown()
            except Exception as e:
                self.logger.error(f"Error shutting down web server: {e}")
        
        # Wait for threads to complete with a longer timeout
        for thread in self.threads:
            if thread.is_alive():
                self.logger.info(f"Waiting for thread {thread.name} to terminate...")
                # Increase timeout to 5 seconds to give threads more time to terminate
                thread.join(timeout=5.0)
                if thread.is_alive():
                    self.logger.warning(f"Thread {thread.name} did not terminate gracefully")
        
        # Close database connection
        self.db_manager.close()
        self.logger.info("Cleanup complete")
    
    def _run_network_scanner(self) -> None:
        """Run the network scanner in a loop."""
        self.logger.info("Starting network scanner")
        
        while not self.stop_event.is_set():
            try:
                # Run network scan
                self.logger.info("Starting network scan cycle")
                self.network_scanner.scan()
                self.logger.info("Network scan cycle completed")
                
                # Sleep for the configured interval
                scan_interval = self.config.get("general", "scan_interval")
                self.logger.info(f"Sleeping for {scan_interval} seconds until next network scan")
                time.sleep(scan_interval)
            except Exception as e:
                self.logger.error(f"Error in network scanner: {e}")
                time.sleep(10)  # Sleep for a short time before retrying
    
    def _run_web_server(self) -> None:
        """Run the web server."""
        self.logger.info("Starting web server")
        
        try:
            self.web_server.start()
        except Exception as e:
            self.logger.error(f"Error in web server: {e}")
    
    def _run_internet_health_check(self, stop_event=None) -> None:
        """Run internet health checks in a loop.
        
        Args:
            stop_event: Optional threading.Event to signal thread termination
        """
        self.logger.info("Starting internet health check")
        
        # Use provided stop event or default to the application stop event
        if stop_event is None:
            stop_event = self.stop_event
        
        # Check if speedtest-cli is installed
        if not shutil.which('speedtest-cli'):
            # Try the Python module as fallback
            try:
                import speedtest
                self.logger.info("Using Python speedtest module for internet health check")
                use_cli = False
            except ImportError:
                self.logger.error("speedtest-cli not installed. Internet health check disabled.")
                return
        else:
            self.logger.info("Using speedtest-cli command line tool for internet health check")
            use_cli = True
        
        while not stop_event.is_set() and not self.stop_event.is_set():
            try:
                # Get interval from config
                interval = self.config.get("monitoring", "internet_health", {}).get("interval", 3600)
                
                # Check for stop event before starting a potentially long-running test
                if stop_event.is_set() or self.stop_event.is_set():
                    self.logger.info("Stop event detected before speed test, exiting health check thread")
                    break
                
                # Run speed test
                self.logger.info("Running internet speed test")
                
                if use_cli:
                    # Use the command line tool
                    import json
                    import subprocess
                    import threading
                    
                    max_retries = 2  # Reduced from 3 to 2
                    retry_count = 0
                    success = False
                    speedtest_process = None
                    
                    # Create a function to kill the process if it takes too long
                    def kill_process_on_timeout(proc, timeout):
                        timer = threading.Timer(timeout, lambda p: p.kill() if p.poll() is None else None, [proc])
                        try:
                            timer.start()
                            proc.wait()
                        finally:
                            timer.cancel()
                    
                    while retry_count < max_retries and not success and not stop_event.is_set() and not self.stop_event.is_set():
                        try:
                            # Run speedtest-cli with JSON output and additional options
                            self.logger.info(f"Running speedtest-cli (attempt {retry_count + 1}/{max_retries})")
                            
                            # Use Popen instead of run to have better control over the process
                            speedtest_process = subprocess.Popen(
                                ['speedtest-cli', '--json', '--secure'],  # Added --secure to use HTTPS
                                stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,
                                text=True
                            )
                            
                            # Start a thread to kill the process if it takes too long
                            kill_thread = threading.Thread(
                                target=kill_process_on_timeout,
                                args=(speedtest_process, 90),  # 90 second timeout
                                daemon=True
                            )
                            kill_thread.start()
                            
                            # Get the output
                            stdout, stderr = speedtest_process.communicate()
                            
                            # Check if command was successful
                            if speedtest_process.returncode != 0:
                                raise subprocess.SubprocessError(f"Command returned non-zero exit status {speedtest_process.returncode}. stderr: {stderr}")
                            
                            # Parse JSON output
                            data = json.loads(stdout)
                            
                            # Extract metrics
                            download_speed = data['download'] / 1_000_000  # Convert to Mbps
                            upload_speed = data['upload'] / 1_000_000  # Convert to Mbps
                            ping = data['ping']
                            
                            # Get connection metadata
                            isp = data.get('client', {}).get('isp', 'Unknown')
                            server_name = data.get('server', {}).get('name', 'Unknown')
                            
                            success = True
                            
                        except (subprocess.SubprocessError, json.JSONDecodeError, ValueError) as e:
                            retry_count += 1
                            self.logger.warning(f"Error running speedtest-cli (attempt {retry_count}/{max_retries}): {e}")
                            
                            # Check if we need to terminate due to stop event
                            if stop_event.is_set() or self.stop_event.is_set():
                                self.logger.info("Stop event detected during speedtest, exiting health check thread")
                                break
                                
                            if retry_count < max_retries:
                                # Wait before retrying
                                self.logger.info(f"Waiting 15 seconds before retry...")  # Reduced from 30 to 15
                                self._sleep_with_check(15, stop_event)
                            else:
                                self.logger.error(f"Failed to run speedtest-cli after {max_retries} attempts. Last error: {e}")
                                # Record a failed speed test in the database
                                self.db_manager.add_speed_test(
                                    download_speed=None,
                                    upload_speed=None,
                                    ping=None,
                                    isp="Unknown",
                                    server_name="Unknown",
                                    error=str(e)
                                )
                                self._sleep_with_check(60, stop_event)
                                continue
                        finally:
                            # Make sure the process is terminated if it's still running
                            if speedtest_process and speedtest_process.poll() is None:
                                try:
                                    speedtest_process.terminate()
                                    # Give it a moment to terminate gracefully
                                    import time
                                    time.sleep(0.5)
                                    # Force kill if still running
                                    if speedtest_process.poll() is None:
                                        speedtest_process.kill()
                                except Exception as e:
                                    self.logger.warning(f"Error terminating speedtest process: {e}")
                else:
                    # Use the Python module
                    import speedtest
                    
                    # Initialize speedtest with timeout settings
                    st = speedtest.Speedtest()
                    st.get_best_server()
                    
                    # Run tests and gather metrics
                    download_speed = st.download() / 1_000_000  # Convert to Mbps
                    upload_speed = st.upload() / 1_000_000  # Convert to Mbps
                    ping = st.results.ping
                    
                    # Get connection metadata
                    isp = st.results.client.get("isp", "Unknown")
                    server_name = st.results.server.get("name", "Unknown")
                
                # Check for stop event again before database operations
                if stop_event.is_set() or self.stop_event.is_set():
                    self.logger.info("Stop event detected after speed test, exiting health check thread")
                    break
                
                # Log results
                self.logger.info(f"Speed test results: {download_speed:.2f}/{upload_speed:.2f} Mbps, {ping:.2f} ms")
                
                # Save to database
                self.db_manager.add_speed_test(download_speed, upload_speed, ping, isp, server_name)
                
                # Check for issues that require alerts
                self._check_internet_health_alerts(download_speed, upload_speed, ping)
                
                # Sleep until next interval, checking for stop events
                self._sleep_with_check(interval, stop_event)
            except Exception as e:
                self.logger.error(f"Error in internet health check: {e}")
                # Sleep for a short time before retrying
                self._sleep_with_check(60, stop_event)
    
    def _check_internet_health_alerts(self, download_speed: float, upload_speed: float, ping: float) -> None:
        """Check internet health metrics and send alerts if thresholds are exceeded.
        
        Args:
            download_speed: Download speed in Mbps
            upload_speed: Upload speed in Mbps
            ping: Ping/latency in ms
        """
        # Check if latency exceeds threshold
        latency_threshold = self.config.get("alerts", "latency_threshold")
        if ping > latency_threshold:
            self.alert_manager.send_alert(
                "High Latency Detected",
                f"Network latency is high: {ping:.2f} ms (threshold: {latency_threshold} ms)"
            )
        
        # TODO: Add additional checks for download/upload speeds
        # These could be implemented in a future version
    
    def _sleep_with_check(self, seconds: int, stop_event: threading.Event) -> None:
        """Sleep for specified seconds while periodically checking stop event.
        
        Args:
            seconds: Number of seconds to sleep
            stop_event: Event to check for termination signal
        """
        for _ in range(seconds):
            if stop_event.is_set() or self.stop_event.is_set():
                break
            time.sleep(1)
    
    def _run_website_monitoring(self, stop_event=None) -> None:
        """Run website monitoring in a loop.
        
        Args:
            stop_event: Optional threading.Event to signal thread termination
        """
        self.logger.info("Starting website monitoring")
        
        # Use provided stop event or default to the application stop event
        if stop_event is None:
            stop_event = self.stop_event
        
        # Import here to avoid dependency if feature is disabled
        try:
            import requests
            import urllib3
            # Suppress insecure request warnings for internal network scans
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except ImportError:
            self.logger.error("requests not installed. Website monitoring disabled.")
            return
        
        while not stop_event.is_set() and not self.stop_event.is_set():
            try:
                # Get interval from config
                interval = self.config.get("monitoring", "websites", {}).get("interval", 300)
                
                # Get websites to monitor
                websites = self.config.get("monitoring", "websites", {}).get("urls", [])
                
                self._check_websites(websites, requests, stop_event)
                
                # Sleep until next interval, checking for stop events
                self._sleep_with_check(interval, stop_event)
            except Exception as e:
                self.logger.error(f"Error in website monitoring: {e}")
                # Sleep for a short time before retrying
                self._sleep_with_check(60, stop_event)
    
    def _check_websites(self, websites: List[str], requests_module: Any, stop_event: threading.Event) -> None:
        """Check a list of websites and log/alert on issues.
        
        Args:
            websites: List of website URLs to check
            requests_module: Imported requests module
            stop_event: Threading event to check for termination
        """
        for url in websites:
            # Check if stop requested during processing
            if stop_event.is_set() or self.stop_event.is_set():
                break
                
            try:
                # Ensure URL has a scheme
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                    
                self.logger.debug(f"Checking website: {url}")
                
                # Send request with timeout
                start_time = time.time()
                response = requests_module.get(url, timeout=10, verify=False)
                response_time = time.time() - start_time
                
                # Check if response is successful
                is_up = response.status_code < 400
                
                # Save to database
                self.db_manager.add_website_check(
                    url, 
                    status_code=response.status_code,
                    response_time=response_time,
                    is_up=is_up
                )
                
                # Send alert if website is down
                if not is_up and self.config.get("alerts", "website_error"):
                    self.alert_manager.send_alert(
                        "Website Error",
                        f"Website {url} returned error status: {response.status_code}"
                    )
            except requests_module.RequestException as e:
                # Website is unreachable
                self.logger.warning(f"Error checking website {url}: {e}")
                
                # Save error to database
                self.db_manager.add_website_check(
                    url,
                    is_up=False,
                    error_message=str(e)
                )
                
                # Send alert
                if self.config.get("alerts", "website_error"):
                    self.alert_manager.send_alert(
                        "Website Unreachable",
                        f"Website {url} is unreachable: {str(e)}"
                    )
    
    def _run_security_scanning(self, stop_event=None) -> None:
        """Run security scanning in a loop.
        
        Args:
            stop_event: Optional threading.Event to signal thread termination
        """
        self.logger.info("Starting security scanning")
        
        # Use provided stop event or default to the application stop event
        if stop_event is None:
            stop_event = self.stop_event
        
        # Import here to avoid dependency if feature is disabled
        try:
            import nmap
        except ImportError:
            self.logger.error("python-nmap not installed. Security scanning disabled.")
            return
        
        while not stop_event.is_set() and not self.stop_event.is_set():
            try:
                # Get interval from config
                interval = self.config.get("monitoring", "security", {}).get("interval", 86400)
                
                # Get all devices from database
                devices = self.db_manager.get_all_devices()
                
                # Scan all devices
                self._scan_devices_security(devices, nmap, stop_event)
                
                # Sleep until next interval, checking for stop events
                self._sleep_with_check(interval, stop_event)
            except Exception as e:
                self.logger.error(f"Error in security scanning: {e}")
                # Sleep for a short time before retrying
                self._sleep_with_check(60, stop_event)
    
    def _scan_devices_security(self, devices: List[Dict[str, Any]], nmap_module: Any, stop_event: threading.Event) -> None:
        """Scan devices for security vulnerabilities.
        
        Args:
            devices: List of device dictionaries from database
            nmap_module: Imported nmap module
            stop_event: Threading event to check for termination
        """
        for device in devices:
            # Check if stop requested during processing
            if stop_event.is_set() or self.stop_event.is_set():
                break
                
            try:
                ip_address = device["ip_address"]
                if not ip_address:
                    continue
                
                self.logger.info(f"Running security scan for device: {ip_address}")
                
                # Initialize scanner
                nm = nmap_module.PortScanner()
                
                # Run scan with appropriate arguments
                # -F: Fast mode - scan fewer ports than the default scan
                nm.scan(ip_address, arguments="-F")
                
                # Process results
                if ip_address in nm.all_hosts():
                    open_ports = self._process_nmap_results(nm, ip_address)
                    
                    # Save to database
                    self.db_manager.add_security_scan(
                        device["id"],
                        open_ports=json.dumps(open_ports)
                    )
                    
                    # Log results and potentially alert on suspicious ports
                    self._handle_security_scan_results(ip_address, open_ports, device)
            except Exception as e:
                self.logger.error(f"Error scanning device {ip_address}: {e}")
    
    def _process_nmap_results(self, nm: Any, ip_address: str) -> List[Dict[str, Any]]:
        """Process nmap scan results for a device.
        
        Args:
            nm: Nmap scanner object with results
            ip_address: IP address of the scanned device
            
        Returns:
            List of dictionaries containing open port information
        """
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
        return open_ports
    
    def _handle_security_scan_results(self, ip_address: str, open_ports: List[Dict[str, Any]], device: Dict[str, Any]) -> None:
        """Process and log security scan results, sending alerts if necessary.
        
        Args:
            ip_address: IP address of the scanned device
            open_ports: List of open ports found during scan
            device: Device dictionary from database
        """
        self.logger.info(f"Security scan for {ip_address} found {len(open_ports)} open ports")
        
        # TODO: Add logic to detect suspicious ports and send alerts
        # This could be implemented in a future version
        
    def update_application(self, progress_callback=None) -> Tuple[bool, Optional[str]]:
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
        
    def _delayed_restart(self, progress_callback=None, delay: int = 3) -> None:
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