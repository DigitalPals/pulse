"""
Integration module to connect network scanner with fingerprinting engine.
Provides comprehensive device fingerprinting capabilities.
"""
import logging
import re
import socket
import subprocess
import threading
import time
from abc import ABC, abstractmethod
import requests
import urllib3
import concurrent.futures
from typing import Dict, List, Optional, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, Future, as_completed
from dataclasses import dataclass, field

from cybex_pulse.fingerprinting.engine import FingerprintEngine

# Suppress insecure request warnings for internal network scans
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class ScannerMixin(ABC):
    """Base class for all scanner components."""
    
    @abstractmethod
    def scan(self, ip_address: str) -> Dict[str, Any]:
        """Perform the scan for this component."""
        pass


class PortScanner(ScannerMixin):
    """Scanner component for port scanning."""
    
    def __init__(self, timeout: float, max_threads: int):
        """
        Initialize port scanner.
        
        Args:
            timeout: Connection timeout in seconds
            max_threads: Maximum number of concurrent threads
        """
        self.timeout = timeout
        self.max_threads = max_threads
        # Prioritize the most common ports first
        self.high_priority_ports = [80, 443, 22, 8080, 8443]
        self.default_ports = [
            21, 23, 25, 53, 81, 88, 445, 515, 631,
            1883, 3000, 3306, 3389, 5000, 5001, 5060, 5900, 8000,
            8081, 8123, 8888, 49152, 49153
        ]
        
    def scan(self, ip_address: str, ports: List[int] = None) -> Dict[str, Any]:
        """
        Scan for open ports on a device.
        
        Args:
            ip_address: Device IP address
            ports: List of ports to scan (defaults to common device ports)
            
        Returns:
            Dictionary with scan results
        """
        if ports is None:
            # Combine high priority and default ports
            all_ports = self.high_priority_ports + [p for p in self.default_ports if p not in self.high_priority_ports]
        else:
            all_ports = ports
        
        open_ports = []
        
        # First, scan high priority ports with a shorter timeout
        high_priority_scan_ports = [p for p in all_ports if p in self.high_priority_ports]
        remaining_ports = [p for p in all_ports if p not in self.high_priority_ports]
        
        # Use a shorter timeout for high priority ports to get quick results
        short_timeout = min(0.5, self.timeout / 2)
        
        # Scan high priority ports first with shorter timeout
        if high_priority_scan_ports:
            high_priority_results = self._scan_port_batch(ip_address, high_priority_scan_ports, short_timeout)
            open_ports.extend(high_priority_results)
        
        # If we have time left, scan remaining ports
        if remaining_ports:
            # Use a slightly longer timeout for remaining ports but still less than the full timeout
            regular_timeout = min(1.0, self.timeout * 0.75)
            regular_results = self._scan_port_batch(ip_address, remaining_ports, regular_timeout)
            open_ports.extend(regular_results)
        
        return {'open_ports': open_ports}
    
    def _scan_port_batch(self, ip_address: str, ports: List[int], port_timeout: float) -> List[int]:
        """Scan a batch of ports with the specified timeout."""
        open_ports = []
        
        # Limit the number of threads based on the number of ports
        batch_max_threads = min(self.max_threads, len(ports))
        
        with ThreadPoolExecutor(max_workers=batch_max_threads) as executor:
            futures = {
                executor.submit(self._check_port, ip_address, port, port_timeout): port
                for port in ports
            }
            
            # Use as_completed with a timeout to avoid waiting too long
            done_futures, _ = concurrent.futures.wait(
                futures.keys(),
                timeout=port_timeout * 1.5,  # Give a bit extra time for all threads to complete
                return_when=concurrent.futures.ALL_COMPLETED
            )
            
            # Process completed futures
            for future in done_futures:
                port = futures[future]
                try:
                    is_open = future.result(timeout=0.1)  # Short timeout for result retrieval
                    if is_open:
                        open_ports.append(port)
                except Exception as e:
                    logger.debug(f"Error checking port {port} on {ip_address}: {e}")
            
            # Cancel any remaining futures
            for future in futures:
                if future not in done_futures and not future.done():
                    future.cancel()
        
        return open_ports
    
    def _check_port(self, ip_address: str, port: int, port_timeout: float) -> bool:
        """Check if a specific port is open."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(port_timeout)
        
        try:
            result = sock.connect_ex((ip_address, port))
            return result == 0
        except (socket.timeout, socket.error) as e:
            logger.debug(f"Socket error checking port {port} on {ip_address}: {e}")
            return False
        finally:
            try:
                sock.close()
            except Exception:
                pass


class HttpScanner(ScannerMixin):
    """Scanner component for HTTP services."""
    
    def __init__(self, timeout: float, signatures: Dict[str, Dict[str, Any]]):
        """
        Initialize HTTP scanner.
        
        Args:
            timeout: Request timeout in seconds
            signatures: Device signatures for content matching
        """
        self.timeout = timeout
        self.signatures = signatures
        self.common_ports = [80, 443, 8080, 8443, 8880, 8843]
        self.nas_indicators = {
            'synology': ['synology', 'diskstation', 'dsm'],
            'qnap': ['qnap', 'qts', 'nas'],
            'unraid': ['unraid', 'lime technology'],
            'truenas': ['truenas', 'freenas'],
            'wd_mycloud': ['wd my cloud', 'mycloud', 'western digital'],
            'asustor': ['asustor', 'asus nas'],
            'terramaster': ['terramaster', 'tnas']
        }
        self.login_indicators = ['login', 'signin', 'admin', 'password', 'username']
        # Create a session to reuse connections
        self.session = requests.Session()
        # Configure session with default settings
        self.session.verify = False
        self.session.headers.update({"User-Agent": "Pulse-NetworkScanner/1.0"})
        # Configure connection pooling
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0,
            pool_block=False
        )
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        
    def scan(self, ip_address: str) -> Dict[str, Any]:
        """
        Scan HTTP services on device.
        
        Args:
            ip_address: Device IP address
            
        Returns:
            Dictionary with HTTP headers and custom indicators
        """
        headers = {}
        
        # Use ThreadPoolExecutor to scan ports in parallel
        with ThreadPoolExecutor(max_workers=min(len(self.common_ports), 6)) as executor:
            # Create a dictionary to map futures to their corresponding ports and protocols
            futures = {}
            
            # Submit tasks for each port
            for port in self.common_ports:
                protocol = "https" if port in [443, 8443, 8843] else "http"
                url = f"{protocol}://{ip_address}:{port}"
                
                # Submit HEAD request
                head_future = executor.submit(self._perform_head_request, url)
                futures[head_future] = (port, protocol, "head")
                
                # Submit GET request
                get_future = executor.submit(self._perform_get_request, url)
                futures[get_future] = (port, protocol, "get")
                
                # For certain devices, check specific paths
                if protocol == "https" and port in [443, 8443]:
                    path_future = executor.submit(self._check_management_paths, protocol, ip_address, port)
                    futures[path_future] = (port, protocol, "paths")
            
            # Process results as they complete
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        headers.update(result)
                except Exception as e:
                    # Log the error but continue processing other results
                    port, protocol, req_type = futures[future]
                    logger.debug(f"Error in HTTP scan for {protocol}://{ip_address}:{port} ({req_type}): {e}")
        
        return {'http_headers': headers}
    
    def _perform_head_request(self, url: str) -> Dict[str, str]:
        """Perform HEAD request to URL."""
        headers = {}
        try:
            resp = self.session.head(
                url,
                timeout=self.timeout,
                allow_redirects=False
            )
            
            if resp.status_code < 400:
                for key, value in resp.headers.items():
                    headers[key] = value
        except requests.RequestException:
            pass
        finally:
            # Ensure connection is closed properly
            if 'resp' in locals() and hasattr(resp, 'close'):
                resp.close()
            
        return headers
    
    def _perform_get_request(self, url: str) -> Dict[str, str]:
        """Perform GET request and analyze content."""
        headers = {}
        try:
            # Use a different user agent for GET requests
            custom_headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
            
            resp = self.session.get(
                url,
                timeout=self.timeout,
                headers=custom_headers,
                allow_redirects=True
            )
            
            if resp.status_code in [200, 302, 401]:
                # Use a context manager to ensure proper resource cleanup
                with resp:
                    content = resp.text.lower()
                    
                    # Check for NAS indicators
                    for nas_type, keywords in self.nas_indicators.items():
                        if any(keyword in content for keyword in keywords):
                            headers[f'X-Content-Contains-{nas_type.capitalize()}'] = 'true'
                            break
                                
                    # Check for specific device content indicators
                    for sig_id, signature in self.signatures.items():
                        if 'content_indicators' in signature:
                            indicators = signature.get('content_indicators', [])
                            if any(indicator.lower() in content for indicator in indicators):
                                headers[f'X-Content-Indicator-{sig_id}'] = 'true'
                                break
                    
                    # Extract page title
                    if '<title>' in content and '</title>' in content:
                        try:
                            title = content.split('<title>')[1].split('</title>')[0].strip()
                            headers['X-Page-Title'] = title
                        except IndexError:
                            # Malformed HTML, don't crash
                            pass
                    
                    # Check for login forms
                    if any(indicator in content for indicator in self.login_indicators):
                        headers['X-Has-Login-Form'] = 'true'
        except requests.RequestException:
            pass
        finally:
            # Ensure connection is closed properly
            if 'resp' in locals() and hasattr(resp, 'close') and not hasattr(resp, '__exit__'):
                resp.close()
            
        return headers
    
    def _check_management_paths(self, protocol: str, ip_address: str, port: int) -> Dict[str, str]:
        """Check common management paths for specific devices."""
        headers = {}
        management_paths = ['/manage', '/network', '/login', '/api/auth/login']
        
        # Use ThreadPoolExecutor to check paths in parallel
        with ThreadPoolExecutor(max_workers=len(management_paths)) as executor:
            futures = {}
            
            for path in management_paths:
                path_url = f"{protocol}://{ip_address}:{port}{path}"
                future = executor.submit(self._check_single_path, path_url)
                futures[future] = path
            
            # Process results as they complete
            for future in futures:
                try:
                    result = future.result()
                    if result:
                        headers.update(result)
                except Exception:
                    # Just continue if there's an error with one path
                    pass
                
        return headers
        
    def _check_single_path(self, path_url: str) -> Dict[str, str]:
        """Check a single management path."""
        headers = {}
        try:
            resp = self.session.get(
                path_url,
                timeout=self.timeout,
                allow_redirects=False
            )
            
            if resp.status_code in [200, 302, 401]:
                content = resp.text.lower()
                if 'unifi' in content or 'ubiquiti' in content:
                    headers['X-Content-Contains-UniFi'] = 'true'
                    
                    # Check for specific models
                    for model_id in ["UDM-Pro-Max", "UDMPMAX", "UDM-SE"]:
                        if model_id.lower() in content:
                            headers['X-Content-Contains-Model'] = model_id
                            break
        except requests.RequestException:
            pass
        finally:
            # Ensure connection is closed properly
            if 'resp' in locals() and hasattr(resp, 'close'):
                resp.close()
                
        return headers
        
    def __del__(self):
        """Ensure proper cleanup of resources."""
        if hasattr(self, 'session'):
            try:
                self.session.close()
            except Exception:
                pass


class SnmpScanner(ScannerMixin):
    """Scanner component for SNMP services."""
    
    def __init__(self, timeout: float):
        """
        Initialize SNMP scanner.
        
        Args:
            timeout: Subprocess timeout in seconds
        """
        self.timeout = timeout
        
    def scan(self, ip_address: str) -> Dict[str, Any]:
        """
        Scan SNMP services on device.
        
        Args:
            ip_address: Device IP address
            
        Returns:
            Dictionary with SNMP data
        """
        snmp_data = {}
        
        try:
            # Try SNMP v2c with community string 'public'
            cmd = [
                'snmpwalk', '-v2c', '-c', 'public', '-t', '1', '-r', '1', 
                ip_address, 'system'
            ]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "::" in line:
                        try:
                            oid, value = line.split("::", 1)
                            oid = oid.strip()
                            value = value.strip()
                            snmp_data[oid] = value
                        except ValueError:
                            # Skip malformed lines
                            continue
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
        
        return {'snmp_data': snmp_data}


class MdnsScanner(ScannerMixin):
    """Scanner component for mDNS/Bonjour services."""
    
    def __init__(self, timeout: float):
        """
        Initialize mDNS scanner.
        
        Args:
            timeout: Subprocess timeout in seconds
        """
        self.timeout = timeout
        # Use a shorter timeout for mDNS operations to prevent long waits
        self.mdns_timeout = min(1.0, timeout / 2)
        
    def scan(self, ip_address: str) -> Dict[str, Any]:
        """
        Scan mDNS services for device.
        
        Args:
            ip_address: Device IP address
            
        Returns:
            Dictionary with mDNS data
        """
        mdns_data = {}
        
        # Try to get hostname with a shorter timeout
        try:
            hostname = self._resolve_hostname(ip_address)
            if hostname:
                mdns_data['hostname'] = hostname
                
                # Only try to get service info if we successfully got a hostname
                # and we still have time left in our budget
                service_info = self._get_service_info(ip_address)
                mdns_data.update(service_info)
        except Exception as e:
            logger.debug(f"Error in mDNS scan for {ip_address}: {e}")
            
        return {'mdns_data': mdns_data}
    
    def _resolve_hostname(self, ip_address: str) -> Optional[str]:
        """Resolve hostname using avahi-resolve."""
        try:
            # Check if avahi-resolve is available
            if not self._check_command_exists('avahi-resolve'):
                logger.debug("avahi-resolve command not found, skipping hostname resolution")
                return None
                
            cmd = ['avahi-resolve', '-a', ip_address]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.mdns_timeout
            )
            
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Hostname resolution timed out for {ip_address}: {e}")
            
        return None
    
    def _get_service_info(self, ip_address: str) -> Dict[str, str]:
        """Get service information using avahi-browse."""
        service_info = {}
        
        try:
            # Check if avahi-browse is available
            if not self._check_command_exists('avahi-browse'):
                logger.debug("avahi-browse command not found, skipping service discovery")
                return service_info
                
            cmd = ['avahi-browse', '-a', '-p', '-r', '-t']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.mdns_timeout
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if ip_address in line:
                        parts = line.split(';')
                        if len(parts) >= 7:
                            service_info['service_type'] = parts[0]
                            service_info['service_name'] = parts[3]
                            break
        except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
            logger.debug(f"Service discovery timed out for {ip_address}: {e}")
            
        return service_info
        
    def _check_command_exists(self, command: str) -> bool:
        """Check if a command exists in the system PATH."""
        try:
            # Use 'which' command to check if the command exists
            result = subprocess.run(
                ['which', command],
                capture_output=True,
                text=True,
                timeout=0.5
            )
            return result.returncode == 0
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            return False


@dataclass
class ScanResult:
    """Container for scan results from multiple scanners."""
    ip_address: str
    mac_address: str
    open_ports: List[int] = field(default_factory=list)
    http_headers: Dict[str, str] = field(default_factory=dict)
    snmp_data: Dict[str, str] = field(default_factory=dict)
    mdns_data: Dict[str, str] = field(default_factory=dict)
    hostname: Optional[str] = None
    identification: List[Dict[str, Any]] = field(default_factory=list)


class DeviceFingerprinter:
    """Performs advanced fingerprinting on network devices."""
    
    def __init__(self, max_threads: int = 10, timeout: float = 2, cache_size: int = 1000):
        """
        Initialize the device fingerprinter.
        
        Args:
            max_threads: Maximum number of concurrent threads
            timeout: Timeout for network operations in seconds
            cache_size: Maximum number of MAC addresses to keep in the cache
        """
        logger.info("Initializing DeviceFingerprinter...")
        self.engine = FingerprintEngine()
        self.max_threads = max_threads
        self.timeout = timeout
        self.cache_size = cache_size
        self.fingerprinted_mac_addresses: Set[str] = set()
        self.fingerprint_timestamps: Dict[str, float] = {}  # Track when devices were fingerprinted
        self.cache_lock = threading.RLock()  # Thread-safe cache operations
        
        # Initialize scanner components
        self.port_scanner = PortScanner(timeout, max_threads)
        self.http_scanner = HttpScanner(timeout, self.engine.signatures)
        self.snmp_scanner = SnmpScanner(timeout)
        self.mdns_scanner = MdnsScanner(timeout)
        
        logger.info(f"DeviceFingerprinter initialized with {self.engine.get_signature_count()} signatures")
    
    def fingerprint_device(self, ip_address: str, mac_address: str) -> Dict[str, Any]:
        """
        Perform comprehensive fingerprinting on a single device.
        
        Args:
            ip_address: Device IP address
            mac_address: Device MAC address
            
        Returns:
            Dictionary containing device data and identification results
        """
        logger.info(f"Fingerprinting device {ip_address} ({mac_address})")
        
        # Build base device data
        device_data = {
            'ip_address': ip_address,
            'mac_address': mac_address
        }
        
        # Create a thread pool with a timeout for the entire operation
        scan_timeout = self.timeout * 2  # Double the individual operation timeout
        
        try:
            # Use a more efficient approach - run port scan first, then other scans in parallel
            # This helps identify responsive devices quickly and prioritize further scanning
            
            # Step 1: Run port scan first to quickly determine if device is responsive
            logger.debug(f"Starting port scan for {ip_address}")
            try:
                port_scan_result = self.port_scanner.scan(ip_address)
                device_data.update(port_scan_result)
                
                # If no ports are open, device might be offline or firewalled
                # Still continue with other scans but with shorter timeouts
                if not port_scan_result.get('open_ports', []):
                    logger.debug(f"No open ports found for {ip_address}, device may be offline or firewalled")
                    scan_timeout = self.timeout  # Reduce timeout for potentially offline devices
            except Exception as e:
                logger.error(f"Error in port scan for {ip_address}: {e}")
                device_data['open_ports'] = []
            
            # Step 2: Run other scans in parallel
            logger.debug(f"Starting parallel scans for {ip_address}")
            with ThreadPoolExecutor(max_workers=3) as executor:  # Limit to 3 threads (one per remaining scanner)
                # Submit remaining scanning tasks
                http_future = executor.submit(self.http_scanner.scan, ip_address)
                snmp_future = executor.submit(self.snmp_scanner.scan, ip_address)
                mdns_future = executor.submit(self.mdns_scanner.scan, ip_address)
                
                # Collect results with timeout
                futures_dict = {
                    'http_scan': http_future,
                    'snmp_scan': snmp_future,
                    'mdns_scan': mdns_future
                }
                
                # Use a separate thread to collect results with a timeout
                result_thread = threading.Thread(
                    target=self._collect_future_results_with_timeout,
                    args=(futures_dict, device_data, scan_timeout)
                )
                result_thread.daemon = True
                result_thread.start()
                result_thread.join(timeout=scan_timeout + 1)  # Add 1 second buffer
                
                # Cancel any remaining futures if the thread is still alive
                if result_thread.is_alive():
                    logger.warning(f"Scan timeout for device {ip_address}, cancelling remaining operations")
                    for name, future in futures_dict.items():
                        if not future.done():
                            future.cancel()
        except Exception as e:
            logger.error(f"Error in device fingerprinting thread pool: {e}")
        
        # Extract hostname from mDNS data if available
        if 'mdns_data' in device_data and 'hostname' in device_data['mdns_data']:
            device_data['hostname'] = device_data['mdns_data']['hostname']
        
        # Identify device using fingerprint engine
        try:
            identification = self.engine.identify_device(device_data)
            device_data['identification'] = identification
        except Exception as e:
            logger.error(f"Error identifying device {ip_address}: {e}")
            device_data['identification'] = []
        
        return device_data
    
    def _collect_future_results_with_timeout(self, futures_dict: Dict[str, Future],
                                           device_data: Dict[str, Any],
                                           timeout: float) -> None:
        """
        Collect results from futures with timeout and update device_data in place.
        
        Args:
            futures_dict: Dictionary mapping names to futures
            device_data: Device data dictionary to update with results
            timeout: Maximum time to wait for all futures
        """
        start_time = time.time()
        remaining_futures = list(futures_dict.items())
        
        # Set custom timeouts for specific scan types
        scan_timeouts = {
            'port_scan': timeout,
            'http_scan': timeout,
            'snmp_scan': timeout,
            'mdns_scan': timeout * 0.5  # Reduce mdns_scan timeout to avoid long waits
        }
        
        while remaining_futures and (time.time() - start_time) < timeout:
            # Process any completed futures
            for name, future in list(remaining_futures):
                if future.done():
                    try:
                        result = future.result(timeout=0.1)  # Non-blocking check
                        device_data.update(result)
                    except Exception as e:
                        logger.error(f"Error in {name}: {e}")
                        # Add empty result for this component
                        if name == 'port_scan':
                            device_data.update({'open_ports': []})
                        elif name == 'http_scan':
                            device_data.update({'http_headers': {}})
                        elif name == 'snmp_scan':
                            device_data.update({'snmp_data': {}})
                        elif name == 'mdns_scan':
                            device_data.update({'mdns_data': {}})
                    
                    # Remove processed future
                    remaining_futures.remove((name, future))
                # Check if individual scan timeout has been reached
                elif (time.time() - start_time) > scan_timeouts.get(name, timeout):
                    logger.warning(f"Scan operation {name} timed out (individual timeout)")
                    # Cancel the future
                    future.cancel()
                    # Add empty result for this component
                    if name == 'port_scan':
                        device_data.update({'open_ports': []})
                    elif name == 'http_scan':
                        device_data.update({'http_headers': {}})
                    elif name == 'snmp_scan':
                        device_data.update({'snmp_data': {}})
                    elif name == 'mdns_scan':
                        device_data.update({'mdns_data': {}})
                    # Remove from remaining futures
                    remaining_futures.remove((name, future))
            
            # Short sleep to prevent CPU spinning
            time.sleep(0.1)
        
        # Handle any remaining futures that didn't complete in time
        for name, future in remaining_futures:
            logger.warning(f"Scan operation {name} timed out (global timeout)")
            # Cancel the future to prevent it from running in the background
            future.cancel()
            # Add empty result for this component
            if name == 'port_scan':
                device_data.update({'open_ports': []})
            elif name == 'http_scan':
                device_data.update({'http_headers': {}})
            elif name == 'snmp_scan':
                device_data.update({'snmp_data': {}})
            elif name == 'mdns_scan':
                device_data.update({'mdns_data': {}})

    def fingerprint_network(self, devices: List[Dict[str, str]],
                         force_scan: bool = False) -> List[Dict[str, Any]]:
        """
        Fingerprint multiple devices in a network.
        
        Args:
            devices: List of dictionaries with 'ip_address' and 'mac_address' keys
            force_scan: If True, scan devices even if they've been scanned before
            
        Returns:
            List of fingerprinted devices with identification data
        """
        logger.info(f"Fingerprinting {len(devices)} devices" + (" (forced scan)" if force_scan else ""))
        results = []
        
        # Handle forced scanning
        if force_scan:
            self._clear_device_cache([device.get('mac_address') for device in devices])
        
        # Filter already fingerprinted devices
        filtered_devices = self._filter_fingerprinted_devices(devices, force_scan)
        
        if not filtered_devices:
            logger.info("No new devices to fingerprint")
            return results
            
        logger.info(f"Fingerprinting {len(filtered_devices)} devices after filtering")
        
        # Prioritize devices - put devices with common ports first
        # This helps ensure we get results for the most important devices first
        prioritized_devices = self._prioritize_devices(filtered_devices)
        
        # Limit the number of devices processed in a single batch to avoid resource exhaustion
        batch_size = min(3, len(prioritized_devices))  # Reduced batch size for better stability
        logger.info(f"Processing devices in batches of {batch_size}")
        
        # Process devices in smaller batches to reduce resource usage
        for i in range(0, len(prioritized_devices), batch_size):
            batch = prioritized_devices[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} with {len(batch)} devices")
            
            # Process batch in parallel with proper resource management
            with ThreadPoolExecutor(max_workers=min(self.max_threads, batch_size)) as executor:
                # Submit all tasks and create a mapping of futures to devices
                futures = {}
                for device in batch:
                    future = executor.submit(
                        self.fingerprint_device,
                        device['ip_address'],
                        device['mac_address']
                    )
                    futures[future] = device
                
                # Use wait with a timeout to avoid waiting indefinitely
                # This provides an additional safety net beyond the individual timeouts
                batch_timeout = self.timeout * 3 * batch_size  # Scale timeout with batch size
                done_futures, not_done_futures = concurrent.futures.wait(
                    futures.keys(),
                    timeout=batch_timeout,
                    return_when=concurrent.futures.ALL_COMPLETED
                )
                
                # Cancel any futures that didn't complete in time
                for future in not_done_futures:
                    future.cancel()
                    device = futures[future]
                    logger.warning(f"Cancelled fingerprinting for {device['ip_address']} due to batch timeout")
                    # Add a minimal result for timed-out devices
                    results.append({
                        'ip_address': device['ip_address'],
                        'mac_address': device['mac_address'],
                        'error': "Fingerprinting timed out",
                        'identification': []
                    })
                
                # Process completed futures
                for future in done_futures:
                    device = futures[future]
                    try:
                        # Use a short timeout when getting results to avoid blocking
                        result = future.result(timeout=0.5)
                        results.append(result)
                        
                        # Update timestamp for this device
                        with self.cache_lock:
                            self.fingerprint_timestamps[device['mac_address']] = time.time()
                            
                    except Exception as e:
                        logger.error(f"Error fingerprinting device {device['ip_address']}: {str(e)}")
                        # Create a minimal result for failed devices
                        results.append({
                            'ip_address': device['ip_address'],
                            'mac_address': device['mac_address'],
                            'error': str(e),
                            'identification': []
                        })
            
            # Add a small delay between batches to allow system to recover
            time.sleep(1)
            
            # Prune the cache if it's getting too large
            self._prune_cache_if_needed()
        
        return results
        
    def _prioritize_devices(self, devices: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Prioritize devices for scanning based on IP address patterns.
        Devices with common local IP patterns are prioritized.
        
        Args:
            devices: List of devices to prioritize
            
        Returns:
            Prioritized list of devices
        """
        # Common local IP patterns that often represent important devices
        high_priority_patterns = [
            r'192\.168\.1\.1$',    # Common router IP
            r'192\.168\.0\.1$',    # Common router IP
            r'10\.0\.0\.1$',       # Common router IP
            r'192\.168\.[01]\.(1|254)$',  # Common gateway IPs
        ]
        
        # Medium priority patterns
        medium_priority_patterns = [
            r'192\.168\.[01]\.(2|3|4|5)$',  # Often servers or important devices
            r'10\.0\.0\.[1-9]$',            # Often servers or important devices
        ]
        
        high_priority = []
        medium_priority = []
        normal_priority = []
        
        for device in devices:
            ip = device.get('ip_address', '')
            
            # Check if IP matches high priority patterns
            if any(re.match(pattern, ip) for pattern in high_priority_patterns):
                high_priority.append(device)
            # Check if IP matches medium priority patterns
            elif any(re.match(pattern, ip) for pattern in medium_priority_patterns):
                medium_priority.append(device)
            # Otherwise, normal priority
            else:
                normal_priority.append(device)
        
        # Combine the lists in priority order
        return high_priority + medium_priority + normal_priority
    
    def _prune_cache_if_needed(self) -> None:
        """Prune the fingerprinted devices cache if it exceeds the maximum size."""
        with self.cache_lock:
            if len(self.fingerprinted_mac_addresses) > self.cache_size:
                logger.info(f"Pruning fingerprint cache (current size: {len(self.fingerprinted_mac_addresses)})")
                
                # Sort MAC addresses by timestamp (oldest first)
                sorted_macs = sorted(
                    self.fingerprint_timestamps.keys(),
                    key=lambda mac: self.fingerprint_timestamps.get(mac, 0)
                )
                
                # Remove oldest entries until we're under the limit
                to_remove = len(sorted_macs) - self.cache_size
                if to_remove > 0:
                    for mac in sorted_macs[:to_remove]:
                        self.fingerprinted_mac_addresses.discard(mac)
                        self.fingerprint_timestamps.pop(mac, None)
                    
                    logger.info(f"Pruned {to_remove} entries from fingerprint cache")
    
    def _clear_device_cache(self, mac_addresses: List[str]) -> None:
        """
        Clear specific devices from the fingerprinting cache.
        
        Args:
            mac_addresses: List of MAC addresses to clear
        """
        with self.cache_lock:
            for mac in mac_addresses:
                if mac in self.fingerprinted_mac_addresses:
                    self.fingerprinted_mac_addresses.remove(mac)
                    self.fingerprint_timestamps.pop(mac, None)
                    logger.info(f"Cleared from in-memory cache: {mac} (forced scan)")
    
    def _filter_fingerprinted_devices(self, devices: List[Dict[str, str]],
                                  force_scan: bool) -> List[Dict[str, str]]:
        """
        Filter out already fingerprinted devices.
        
        Args:
            devices: List of devices to filter
            force_scan: Whether to force scan all devices
            
        Returns:
            Filtered list of devices to scan
        """
        if force_scan:
            return devices
            
        filtered_devices = []
        with self.cache_lock:
            for device in devices:
                mac = device.get('mac_address', '')
                if not mac or mac in self.fingerprinted_mac_addresses:
                    logger.info(f"Skipping already fingerprinted device: {mac}")
                    continue
                    
                filtered_devices.append(device)
                # Track this device as processed
                self.fingerprinted_mac_addresses.add(mac)
                self.fingerprint_timestamps[mac] = time.time()
            
        return filtered_devices
        
    def clear_all_caches(self) -> None:
        """Clear all in-memory caches."""
        with self.cache_lock:
            self.fingerprinted_mac_addresses.clear()
            self.fingerprint_timestamps.clear()
            logger.info("Cleared all fingerprinting caches")