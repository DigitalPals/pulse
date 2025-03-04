"""
Monitoring features module for Cybex Pulse.

This module provides base classes and implementations for various monitoring features:
- Internet health monitoring
- Website availability monitoring
- Security scanning
- Base classes for extending monitoring capabilities
"""
import json
import logging
import shutil
import subprocess
import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple

from cybex_pulse.core.alerting import AlertManager
from cybex_pulse.core.thread_manager import ThreadManager
from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config


class MonitoringFeature(ABC):
    """Base class for monitoring features.
    
    This abstract class defines the interface and common functionality for all
    monitoring features in Cybex Pulse.
    """
    
    def __init__(
        self, 
        name: str,
        config: Config, 
        db_manager: DatabaseManager, 
        logger: logging.Logger,
        thread_manager: ThreadManager,
        alert_manager: AlertManager
    ):
        """Initialize the monitoring feature.
        
        Args:
            name: Feature name
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
            thread_manager: Thread manager
            alert_manager: Alert manager
        """
        self.name = name
        self.config = config
        self.db_manager = db_manager
        self.logger = logger
        self.thread_manager = thread_manager
        self.alert_manager = alert_manager
        
        # Thread management
        self.thread = None
        self.stop_event = None
        
        # Configuration paths
        self.enabled_config_path = self._get_enabled_config_path()
        self.interval_config_path = self._get_interval_config_path()
    
    def _get_enabled_config_path(self) -> List[str]:
        """Get the configuration path for the enabled setting.
        
        Returns:
            List[str]: Configuration path components
        """
        return ["monitoring", self.name, "enabled"]
    
    def _get_interval_config_path(self) -> List[str]:
        """Get the configuration path for the interval setting.
        
        Returns:
            List[str]: Configuration path components
        """
        return ["monitoring", self.name, "interval"]
    
    def is_enabled(self) -> bool:
        """Check if the monitoring feature is enabled.
        
        Returns:
            bool: True if enabled, False otherwise
        """
        # Access nested config values based on path
        section = self.enabled_config_path[0]
        if len(self.enabled_config_path) == 2:
            key = self.enabled_config_path[1]
            return self.config.get(section, key, False)
        elif len(self.enabled_config_path) == 3:
            subsection = self.config.get(section, self.enabled_config_path[1], {})
            if isinstance(subsection, dict):
                return subsection.get(self.enabled_config_path[2], False)
        return False
    
    def get_interval(self) -> int:
        """Get the monitoring interval in seconds.
        
        Returns:
            int: Interval in seconds
        """
        # Access nested config values based on path
        section = self.interval_config_path[0]
        if len(self.interval_config_path) == 2:
            key = self.interval_config_path[1]
            return self.config.get(section, key, 3600)
        elif len(self.interval_config_path) == 3:
            subsection = self.config.get(section, self.interval_config_path[1], {})
            if isinstance(subsection, dict):
                return subsection.get(self.interval_config_path[2], 3600)
        return 3600
    
    def start(self) -> None:
        """Start the monitoring feature."""
        if self.thread and self.thread.is_alive():
            self.logger.info(f"{self.name} thread already running")
            return
            
        self.logger.info(f"Starting {self.name} thread")
        
        # Create a dedicated stop event for this thread
        self.stop_event = self.thread_manager.create_stop_event(self.name)
        
        # Create and start the thread
        self.thread = self.thread_manager.start_thread(
            name=self.name,
            target=self._run_monitoring_loop,
            args=(self.stop_event,)
        )
    
    def stop(self) -> None:
        """Stop the monitoring feature."""
        if not self.thread or not self.thread.is_alive():
            self.logger.info(f"No {self.name} thread running to stop")
            return
            
        self.thread_manager.stop_thread(self.name, self.thread)
        self.thread = None
    
    def _run_monitoring_loop(self, stop_event: threading.Event) -> None:
        """Run the monitoring loop.
        
        Args:
            stop_event: Event to signal thread termination
        """
        self.logger.info(f"Starting {self.name} monitoring")
        
        while not stop_event.is_set() and not self.thread_manager.global_stop_event.is_set():
            try:
                # Get interval from config
                interval = self.get_interval()
                
                # Check for stop event before starting monitoring
                if stop_event.is_set() or self.thread_manager.global_stop_event.is_set():
                    self.logger.info(f"Stop event detected before {self.name} monitoring, exiting thread")
                    break
                
                # Run monitoring
                self.logger.info(f"Running {self.name} monitoring")
                self._run_monitoring_cycle()
                
                # Sleep until next interval, checking for stop events
                self.thread_manager.sleep_with_check(interval, stop_event)
            except Exception as e:
                self.logger.error(f"Error in {self.name} monitoring: {e}")
                # Sleep for a short time before retrying
                self.thread_manager.sleep_with_check(60, stop_event)
    
    @abstractmethod
    def _run_monitoring_cycle(self) -> None:
        """Run a single monitoring cycle.
        
        This method must be implemented by subclasses.
        """
        pass


class InternetHealthMonitor(MonitoringFeature):
    """Internet health monitoring feature.
    
    This class provides functionality for:
    - Monitoring internet connection health
    - Running speed tests
    - Detecting latency issues
    - Alerting on connectivity problems
    """
    
    def __init__(
        self, 
        config: Config, 
        db_manager: DatabaseManager, 
        logger: logging.Logger,
        thread_manager: ThreadManager,
        alert_manager: AlertManager
    ):
        """Initialize the internet health monitor.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
            thread_manager: Thread manager
            alert_manager: Alert manager
        """
        super().__init__(
            name="internet_health",
            config=config,
            db_manager=db_manager,
            logger=logger,
            thread_manager=thread_manager,
            alert_manager=alert_manager
        )
        
        # Check if speedtest-cli is installed
        self.use_cli = False
        self.speedtest_available = False
        
        if shutil.which('speedtest-cli'):
            self.use_cli = True
            self.speedtest_available = True
            self.logger.info("Using speedtest-cli command line tool for internet health check")
        else:
            # Try the Python module as fallback
            try:
                import speedtest
                self.speedtest_available = True
                self.logger.info("Using Python speedtest module for internet health check")
            except ImportError:
                self.logger.error("speedtest-cli not installed. Internet health check disabled.")
    
    def _run_monitoring_cycle(self) -> None:
        """Run a single internet health monitoring cycle."""
        if not self.speedtest_available:
            self.logger.error("Speedtest not available. Internet health check skipped.")
            return
            
        if self.use_cli:
            self._run_cli_speedtest()
        else:
            self._run_python_speedtest()
    
    def _run_cli_speedtest(self) -> None:
        """Run speedtest using the command line tool."""
        import json
        import subprocess
        import threading
        
        max_retries = 2
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
        
        while retry_count < max_retries and not success and not self.stop_event.is_set():
            try:
                # Run speedtest-cli with JSON output and additional options
                self.logger.info(f"Running speedtest-cli (attempt {retry_count + 1}/{max_retries})")
                
                # Use Popen instead of run to have better control over the process
                speedtest_process = subprocess.Popen(
                    ['speedtest-cli', '--json', '--secure'],
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
                    raise subprocess.SubprocessError(
                        f"Command returned non-zero exit status {speedtest_process.returncode}. stderr: {stderr}"
                    )
                
                # Check if stdout is empty or whitespace only
                if not stdout or stdout.isspace():
                    raise ValueError("Empty response from speedtest-cli")
                    
                # Parse JSON output with better error handling
                try:
                    data = json.loads(stdout)
                    
                    # Extract metrics
                    download_speed = data['download'] / 1_000_000  # Convert to Mbps
                    upload_speed = data['upload'] / 1_000_000  # Convert to Mbps
                    ping = data['ping']
                except json.JSONDecodeError as json_err:
                    self.logger.error(f"Invalid JSON response from speedtest-cli: {json_err}")
                    self.logger.debug(f"Raw output: {stdout[:200]}...")  # Log first 200 chars of output
                    raise
                
                # Get connection metadata
                isp = data.get('client', {}).get('isp', 'Unknown')
                server_name = data.get('server', {}).get('name', 'Unknown')
                
                success = True
                
                # Process results
                self._process_speedtest_results(download_speed, upload_speed, ping, isp, server_name)
                
            except (subprocess.SubprocessError, json.JSONDecodeError, ValueError) as e:
                retry_count += 1
                self.logger.warning(f"Error running speedtest-cli (attempt {retry_count}/{max_retries}): {e}")
                
                # Check if we need to terminate due to stop event
                if self.stop_event.is_set():
                    self.logger.info("Stop event detected during speedtest, exiting health check thread")
                    break
                    
                if retry_count < max_retries:
                    # Wait before retrying
                    self.logger.info(f"Waiting 15 seconds before retry...")
                    self.thread_manager.sleep_with_check(15, self.stop_event)
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
            finally:
                # Make sure the process is terminated if it's still running
                if speedtest_process and speedtest_process.poll() is None:
                    try:
                        speedtest_process.terminate()
                        # Give it a moment to terminate gracefully
                        time.sleep(0.5)
                        # Force kill if still running
                        if speedtest_process.poll() is None:
                            speedtest_process.kill()
                    except Exception as e:
                        self.logger.warning(f"Error terminating speedtest process: {e}")
    
    def _run_python_speedtest(self) -> None:
        """Run speedtest using the Python module."""
        try:
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
            
            # Process results
            self._process_speedtest_results(download_speed, upload_speed, ping, isp, server_name)
            
        except Exception as e:
            self.logger.error(f"Error running Python speedtest: {e}")
            # Record a failed speed test in the database
            self.db_manager.add_speed_test(
                download_speed=None,
                upload_speed=None,
                ping=None,
                isp="Unknown",
                server_name="Unknown",
                error=str(e)
            )
    
    def _process_speedtest_results(
        self, 
        download_speed: float, 
        upload_speed: float, 
        ping: float, 
        isp: str, 
        server_name: str
    ) -> None:
        """Process speedtest results.
        
        Args:
            download_speed: Download speed in Mbps
            upload_speed: Upload speed in Mbps
            ping: Ping/latency in ms
            isp: Internet Service Provider name
            server_name: Speedtest server name
        """
        # Log results
        self.logger.info(f"Speed test results: {download_speed:.2f}/{upload_speed:.2f} Mbps, {ping:.2f} ms")
        
        # Save to database
        self.db_manager.add_speed_test(download_speed, upload_speed, ping, isp, server_name)
        
        # Check for issues that require alerts
        self._check_internet_health_alerts(download_speed, upload_speed, ping)
    
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
        
        # Check if download speed is below threshold
        download_threshold = self.config.get("alerts", "download_speed_threshold", default=0)
        if download_threshold > 0 and download_speed < download_threshold:
            self.alert_manager.send_alert(
                "Low Download Speed",
                f"Download speed is low: {download_speed:.2f} Mbps (threshold: {download_threshold} Mbps)"
            )
        
        # Check if upload speed is below threshold
        upload_threshold = self.config.get("alerts", "upload_speed_threshold", default=0)
        if upload_threshold > 0 and upload_speed < upload_threshold:
            self.alert_manager.send_alert(
                "Low Upload Speed",
                f"Upload speed is low: {upload_speed:.2f} Mbps (threshold: {upload_threshold} Mbps)"
            )


class WebsiteMonitor(MonitoringFeature):
    """Website monitoring feature.
    
    This class provides functionality for:
    - Monitoring website availability
    - Checking response times
    - Detecting website errors
    - Alerting on website issues
    """
    
    def __init__(
        self, 
        config: Config, 
        db_manager: DatabaseManager, 
        logger: logging.Logger,
        thread_manager: ThreadManager,
        alert_manager: AlertManager
    ):
        """Initialize the website monitor.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
            thread_manager: Thread manager
            alert_manager: Alert manager
        """
        super().__init__(
            name="websites",
            config=config,
            db_manager=db_manager,
            logger=logger,
            thread_manager=thread_manager,
            alert_manager=alert_manager
        )
        
        # Check if requests is installed
        try:
            import requests
            import urllib3
            # Suppress insecure request warnings for internal network scans
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            self.requests_available = True
        except ImportError:
            self.logger.error("requests not installed. Website monitoring disabled.")
            self.requests_available = False
    
    def get_websites(self) -> List[str]:
        """Get the list of websites to monitor.
        
        Returns:
            List[str]: List of website URLs
        """
        return self.config.get("monitoring", "websites", {}).get("urls", [])
    
    def _run_monitoring_cycle(self) -> None:
        """Run a single website monitoring cycle."""
        if not self.requests_available:
            self.logger.error("Requests not available. Website monitoring skipped.")
            return
            
        # Import here to avoid dependency if feature is disabled
        import requests
        
        # Get websites to monitor
        websites = self.get_websites()
        
        for url in websites:
            # Check if stop requested during processing
            if self.stop_event.is_set():
                break
                
            try:
                # Ensure URL has a scheme
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                    
                self.logger.debug(f"Checking website: {url}")
                
                # Send request with timeout
                start_time = time.time()
                response = requests.get(url, timeout=10, verify=False)
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
            except requests.RequestException as e:
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


class SecurityMonitor(MonitoringFeature):
    """Security monitoring feature.
    
    This class provides functionality for:
    - Scanning devices for open ports
    - Detecting security vulnerabilities
    - Identifying suspicious services
    - Alerting on security issues
    """
    
    def __init__(
        self, 
        config: Config, 
        db_manager: DatabaseManager, 
        logger: logging.Logger,
        thread_manager: ThreadManager,
        alert_manager: AlertManager
    ):
        """Initialize the security monitor.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
            thread_manager: Thread manager
            alert_manager: Alert manager
        """
        super().__init__(
            name="security",
            config=config,
            db_manager=db_manager,
            logger=logger,
            thread_manager=thread_manager,
            alert_manager=alert_manager
        )
        
        # Check if nmap is installed
        try:
            import nmap
            self.nmap_available = True
        except ImportError:
            self.logger.error("python-nmap not installed. Security scanning disabled.")
            self.nmap_available = False
    
    def _run_monitoring_cycle(self) -> None:
        """Run a single security monitoring cycle."""
        if not self.nmap_available:
            self.logger.error("Nmap not available. Security scanning skipped.")
            return
            
        # Import here to avoid dependency if feature is disabled
        import nmap
        
        # Get all devices from database
        devices = self.db_manager.get_all_devices()
        
        for device in devices:
            # Check if stop requested during processing
            if self.stop_event.is_set():
                break
                
            try:
                ip_address = device["ip_address"]
                if not ip_address:
                    continue
                
                self.logger.info(f"Running security scan for device: {ip_address}")
                
                # Initialize scanner
                nm = nmap.PortScanner()
                
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
    
    def _handle_security_scan_results(
        self, 
        ip_address: str, 
        open_ports: List[Dict[str, Any]], 
        device: Dict[str, Any]
    ) -> None:
        """Process and log security scan results, sending alerts if necessary.
        
        Args:
            ip_address: IP address of the scanned device
            open_ports: List of open ports found during scan
            device: Device dictionary from database
        """
        self.logger.info(f"Security scan for {ip_address} found {len(open_ports)} open ports")
        
        # Check for suspicious ports
        suspicious_ports = self._check_suspicious_ports(open_ports)
        
        if suspicious_ports and self.config.get("alerts", "suspicious_ports"):
            device_name = device.get('hostname') or device.get('vendor') or ip_address
            
            # Format suspicious ports for alert
            port_details = "\n".join([
                f"- Port {p['port']}/{p['protocol']} ({p['service']}): {p['reason']}"
                for p in suspicious_ports
            ])
            
            self.alert_manager.send_alert(
                "Suspicious Ports Detected",
                f"Device: {device_name} ({ip_address})\n"
                f"The following suspicious ports were detected:\n{port_details}"
            )
    
    def _check_suspicious_ports(self, open_ports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Check for suspicious ports.
        
        Args:
            open_ports: List of open ports
            
        Returns:
            List of suspicious ports with reasons
        """
        suspicious_ports = []
        
        # Define suspicious port ranges and services
        suspicious_port_ranges = [
            (0, 1023, "System port"),  # Well-known ports
            (3389, 3389, "Remote Desktop"),
            (22, 22, "SSH"),
            (23, 23, "Telnet (insecure)"),
            (445, 445, "SMB"),
            (135, 139, "NetBIOS"),
            (5900, 5909, "VNC"),
        ]
        
        suspicious_services = [
            "telnet", "ftp", "rsh", "rlogin", "rexec", "vnc", "rdp", "mysql", "mssql", "oracle", "postgres"
        ]
        
        for port_info in open_ports:
            port = port_info["port"]
            service = port_info["service"].lower()
            
            # Check port ranges
            for start, end, reason in suspicious_port_ranges:
                if start <= port <= end:
                    suspicious_ports.append({
                        **port_info,
                        "reason": reason
                    })
                    break
            
            # Check services
            for suspicious_service in suspicious_services:
                if suspicious_service in service:
                    suspicious_ports.append({
                        **port_info,
                        "reason": f"Potentially insecure service: {service}"
                    })
                    break
        
        return suspicious_ports