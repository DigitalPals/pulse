"""
Integration module to connect network scanner with fingerprinting engine.
Provides comprehensive device fingerprinting capabilities.
"""
import logging
import socket
import subprocess
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
        
    def scan(self, ip_address: str) -> Dict[str, Any]:
        """
        Scan HTTP services on device.
        
        Args:
            ip_address: Device IP address
            
        Returns:
            Dictionary with HTTP headers and custom indicators
        """
        headers = {}
        
        for port in self.common_ports:
            protocol = "https" if port in [443, 8443, 8843] else "http"
            url = f"{protocol}://{ip_address}:{port}"
            
            # First try HEAD request
            head_headers = self._perform_head_request(url)
            headers.update(head_headers)
                
            # Then try GET request
            content_headers = self._perform_get_request(url)
            headers.update(content_headers)
                
            # For certain devices, check specific paths
            if protocol == "https" and port in [443, 8443]:
                path_headers = self._check_management_paths(protocol, ip_address, port)
                headers.update(path_headers)
        
        return {'http_headers': headers}
    
    def _perform_head_request(self, url: str) -> Dict[str, str]:
        """Perform HEAD request to URL."""
        headers = {}
        try:
            resp = requests.head(
                url, 
                timeout=self.timeout,
                headers={"User-Agent": "Pulse-NetworkScanner/1.0"},
                verify=False,
                allow_redirects=False
            )
            
            if resp.status_code < 400:
                for key, value in resp.headers.items():
                    headers[key] = value
        except requests.RequestException:
            pass
            
        return headers
    
    def _perform_get_request(self, url: str) -> Dict[str, str]:
        """Perform GET request and analyze content."""
        headers = {}
        try:
            resp = requests.get(
                url, 
                timeout=self.timeout,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"},
                verify=False,
                allow_redirects=True
            )
            
            if resp.status_code in [200, 302, 401]:
                content = resp.text.lower()
                
                # Check for NAS indicators
                for nas_type, keywords in self.nas_indicators.items():
                    for keyword in keywords:
                        if keyword in content:
                            headers[f'X-Content-Contains-{nas_type.capitalize()}'] = 'true'
                            break
                            
                # Check for specific device content indicators
                for sig_id, signature in self.signatures.items():
                    if 'content_indicators' in signature:
                        for indicator in signature['content_indicators']:
                            if indicator.lower() in content:
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
                for indicator in self.login_indicators:
                    if indicator in content:
                        headers['X-Has-Login-Form'] = 'true'
                        break
        except requests.RequestException:
            pass
            
        return headers
    
    def _check_management_paths(self, protocol: str, ip_address: str, port: int) -> Dict[str, str]:
        """Check common management paths for specific devices."""
        headers = {}
        management_paths = ['/manage', '/network', '/login', '/api/auth/login']
        
        for path in management_paths:
            try:
                path_url = f"{protocol}://{ip_address}:{port}{path}"
                resp = requests.get(
                    path_url,
                    timeout=self.timeout,
                    headers={"User-Agent": "Pulse-NetworkScanner/1.0"},
                    verify=False,
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
                continue
                
        return headers


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
    
    def __init__(self, max_threads: int = 10, timeout: float = 2):
        """
        Initialize the device fingerprinter.
        
        Args:
            max_threads: Maximum number of concurrent threads
            timeout: Timeout for network operations in seconds
        """
        logger.info("Initializing DeviceFingerprinter...")
        self.engine = FingerprintEngine()
        self.max_threads = max_threads
        self.timeout = timeout
        self.fingerprinted_mac_addresses: Set[str] = set()
        
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
        
        # Perform all fingerprinting operations in parallel
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            port_future = executor.submit(self.port_scanner.scan, ip_address)
            http_future = executor.submit(self.http_scanner.scan, ip_address)
            snmp_future = executor.submit(self.snmp_scanner.scan, ip_address)
            mdns_future = executor.submit(self.mdns_scanner.scan, ip_address)
            
            # Collect results from all futures
            scan_results = self._collect_future_results({
                'port_scan': port_future,
                'http_scan': http_future,
                'snmp_scan': snmp_future,
                'mdns_scan': mdns_future
            })
            
            # Update device data with scan results
            for result in scan_results:
                device_data.update(result)
        
        # Extract hostname from mDNS data if available
        if 'mdns_data' in device_data and 'hostname' in device_data['mdns_data']:
            device_data['hostname'] = device_data['mdns_data']['hostname']
        
        # Identify device using fingerprint engine
        identification = self.engine.identify_device(device_data)
        device_data['identification'] = identification
        
        return device_data
    
    def _collect_future_results(self, futures_dict: Dict[str, Future]) -> List[Dict[str, Any]]:
        """
        Safely collect results from futures with error handling.
        
        Args:
            futures_dict: Dictionary mapping names to futures
            
        Returns:
            List of successfully completed future results
        """
        results = []
        
        for name, future in futures_dict.items():
            try:
                result = future.result()
                results.append(result)
            except Exception as e:
                logger.error(f"Error in {name}: {e}")
                # Add empty result for this component
                if name == 'port_scan':
                    results.append({'open_ports': []})
                elif name == 'http_scan':
                    results.append({'http_headers': {}})
                elif name == 'snmp_scan':
                    results.append({'snmp_data': {}})
                elif name == 'mdns_scan':
                    results.append({'mdns_data': {}})
        
        return results

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
        
        # Process devices in parallel
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {
                executor.submit(self.fingerprint_device, device['ip_address'], device['mac_address']): device
                for device in filtered_devices
            }
            
            for future in futures:
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    device = futures[future]
                    logger.error(f"Error fingerprinting device {device['ip_address']}: {str(e)}")
        
        return results
    
    def _clear_device_cache(self, mac_addresses: List[str]) -> None:
        """
        Clear specific devices from the fingerprinting cache.
        
        Args:
            mac_addresses: List of MAC addresses to clear
        """
        for mac in mac_addresses:
            if mac in self.fingerprinted_mac_addresses:
                self.fingerprinted_mac_addresses.remove(mac)
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
        for device in devices:
            mac = device.get('mac_address', '')
            if not mac or mac in self.fingerprinted_mac_addresses:
                logger.info(f"Skipping already fingerprinted device: {mac}")
                continue
                
            filtered_devices.append(device)
            # Track this device as processed
            self.fingerprinted_mac_addresses.add(mac)
            
        return filtered_devices