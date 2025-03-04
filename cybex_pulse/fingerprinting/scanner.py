"""
Integration module to connect network scanner with fingerprinting engine.
Provides comprehensive device fingerprinting capabilities.
"""
import logging
import socket
import subprocess
import threading
import time
from abc import ABC, abstractmethod
import requests
import urllib3
from typing import Dict, List, Optional, Any, Set, Tuple
from concurrent.futures import ThreadPoolExecutor, Future
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
        self.default_ports = [
            21, 22, 23, 25, 53, 80, 81, 88, 443, 445, 515, 631, 
            1883, 3000, 3306, 3389, 5000, 5001, 5060, 5900, 8000, 8080, 8443, 
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
            ports = self.default_ports
        
        open_ports = []
        
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(self._check_port, ip_address, port): port 
                for port in ports
            }
            
            for future in futures:
                port = futures[future]
                try:
                    is_open = future.result()
                    if is_open:
                        open_ports.append(port)
                except Exception as e:
                    logger.debug(f"Error checking port {port} on {ip_address}: {e}")
        
        return {'open_ports': open_ports}
    
    def _check_port(self, ip_address: str, port: int) -> bool:
        """Check if a specific port is open."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        try:
            result = sock.connect_ex((ip_address, port))
            return result == 0
        finally:
            sock.close()


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
        
    def scan(self, ip_address: str) -> Dict[str, Any]:
        """
        Scan mDNS services for device.
        
        Args:
            ip_address: Device IP address
            
        Returns:
            Dictionary with mDNS data
        """
        mdns_data = {}
        hostname = self._resolve_hostname(ip_address)
        
        if hostname:
            mdns_data['hostname'] = hostname
            service_info = self._get_service_info(ip_address)
            mdns_data.update(service_info)
            
        return {'mdns_data': mdns_data}
    
    def _resolve_hostname(self, ip_address: str) -> Optional[str]:
        """Resolve hostname using avahi-resolve."""
        try:
            cmd = ['avahi-resolve', '-a', ip_address]
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=self.timeout
            )
            
            if result.returncode == 0 and result.stdout:
                return result.stdout.strip()
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
            
        return None
    
    def _get_service_info(self, ip_address: str) -> Dict[str, str]:
        """Get service information using avahi-browse."""
        service_info = {}
        
        try:
            cmd = ['avahi-browse', '-a', '-p', '-r', '-t']
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if ip_address in line:
                        parts = line.split(';')
                        if len(parts) >= 7:
                            service_info['service_type'] = parts[0]
                            service_info['service_name'] = parts[3]
                            break
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
            
        return service_info


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
            # Perform all fingerprinting operations in parallel with a timeout
            with ThreadPoolExecutor(max_workers=4) as executor:  # Limit to 4 threads (one per scanner)
                # Submit all scanning tasks
                port_future = executor.submit(self.port_scanner.scan, ip_address)
                http_future = executor.submit(self.http_scanner.scan, ip_address)
                snmp_future = executor.submit(self.snmp_scanner.scan, ip_address)
                mdns_future = executor.submit(self.mdns_scanner.scan, ip_address)
                
                # Collect results with timeout
                futures_dict = {
                    'port_scan': port_future,
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
        identification = self.engine.identify_device(device_data)
        device_data['identification'] = identification
        
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
            
            # Short sleep to prevent CPU spinning
            time.sleep(0.1)
        
        # Handle any remaining futures that didn't complete in time
        for name, future in remaining_futures:
            logger.warning(f"Scan operation {name} timed out")
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
        
        # Limit the number of devices processed in a single batch to avoid resource exhaustion
        batch_size = min(5, len(filtered_devices))
        logger.info(f"Processing devices in batches of {batch_size}")
        
        # Process devices in smaller batches to reduce resource usage
        for i in range(0, len(filtered_devices), batch_size):
            batch = filtered_devices[i:i+batch_size]
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
                
                # Process results as they complete with proper error handling
                for future in concurrent.futures.as_completed(futures):
                    device = futures[future]
                    try:
                        result = future.result()
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