"""
Integration module to connect network scanner with fingerprinting engine.
"""
import logging
import socket
import subprocess
import time
import requests
import urllib3
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor

from cybex_pulse.fingerprinting.engine import FingerprintEngine

# Suppress insecure request warnings for internal network scans
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)

class DeviceFingerprinter:
    """Performs advanced fingerprinting on network devices."""
    
    def __init__(self, max_threads=10, timeout=2):
        logger.info("Initializing DeviceFingerprinter...")
        self.engine = FingerprintEngine()
        self.max_threads = max_threads
        self.timeout = timeout
        self.fingerprinted_mac_addresses = set()  # Track devices we've fingerprinted
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
        
        # Build device data with all available fingerprinting data
        device_data = {
            'ip_address': ip_address,
            'mac_address': mac_address
        }
        
        # Perform all fingerprinting operations in parallel
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            port_scan_future = executor.submit(self._scan_ports, ip_address)
            http_scan_future = executor.submit(self._get_http_headers, ip_address)
            snmp_scan_future = executor.submit(self._get_snmp_data, ip_address)
            mdns_scan_future = executor.submit(self._get_mdns_data, ip_address)
            
            # Get results from completed futures
            device_data['open_ports'] = port_scan_future.result()
            device_data['http_headers'] = http_scan_future.result()
            device_data['snmp_data'] = snmp_scan_future.result()
            device_data['mdns_data'] = mdns_scan_future.result()
        
        # Identify device using fingerprint engine
        identification = self.engine.identify_device(device_data)
        device_data['identification'] = identification
        
        return device_data

    def fingerprint_network(self, devices: List[Dict[str, str]], force_scan: bool = False) -> List[Dict[str, Any]]:
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
        
        # If force_scan is True, clear the fingerprinting cache for these devices
        if force_scan:
            for device in devices:
                mac = device.get('mac_address')
                if mac in self.fingerprinted_mac_addresses:
                    self.fingerprinted_mac_addresses.remove(mac)
                    logger.info(f"Cleared from in-memory cache: {mac} (forced scan)")
        
        # Filter out devices we've already fingerprinted in this session (unless force_scan is True)
        filtered_devices = []
        for device in devices:
            mac = device['mac_address']
            if not force_scan and mac in self.fingerprinted_mac_addresses:
                logger.info(f"Skipping already fingerprinted device in this session: {mac}")
                continue
            filtered_devices.append(device)
            # Add to our tracking set (after filtering, to track processed devices)
            self.fingerprinted_mac_addresses.add(mac)
        
        if not filtered_devices:
            logger.info("No new devices to fingerprint")
            return results
            
        logger.info(f"Fingerprinting {len(filtered_devices)} devices after filtering")
        
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
                    logger.error(f"Error fingerprinting device {device['ip_address']}: {e}")
        
        return results
    
    def _scan_ports(self, ip_address: str, ports: List[int] = None) -> List[int]:
        """
        Scan for open ports on a device.
        
        Args:
            ip_address: Device IP address
            ports: List of ports to scan (defaults to common device ports)
            
        Returns:
            List of open ports
        """
        # Default to common device ports if not specified
        if ports is None:
            ports = [
                21, 22, 23, 25, 53, 80, 81, 88, 443, 445, 515, 631, 
                1883, 3000, 3306, 3389, 5000, 5001, 5060, 5900, 8000, 8080, 8443, 
                8081, 8123, 8888, 49152, 49153
            ]
        
        open_ports = []
        
        with ThreadPoolExecutor(max_workers=self.max_threads) as executor:
            futures = {executor.submit(self._check_port, ip_address, port): port for port in ports}
            
            for future in futures:
                port = futures[future]
                try:
                    is_open = future.result()
                    if is_open:
                        open_ports.append(port)
                except Exception as e:
                    logger.debug(f"Error checking port {port} on {ip_address}: {e}")
        
        return open_ports
    
    def _check_port(self, ip_address: str, port: int) -> bool:
        """Check if a specific port is open."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        
        try:
            result = sock.connect_ex((ip_address, port))
            return result == 0
        finally:
            sock.close()
    
    def _get_http_headers(self, ip_address: str) -> Dict[str, str]:
        """Get HTTP headers from web server(s) on device."""
        headers = {}
        
        # Common HTTP ports to check
        ports = [80, 443, 8080, 8443, 8880, 8843]
        
        for port in ports:
            protocol = "https" if port in [443, 8443, 8843] else "http"
            
            try:
                # Try HEAD request first (more efficient)
                resp = requests.head(
                    f"{protocol}://{ip_address}:{port}", 
                    timeout=self.timeout,
                    headers={"User-Agent": "Pulse-NetworkScanner/1.0"},
                    verify=False,
                    allow_redirects=False
                )
                
                # If we get a response, add headers to our collection
                if resp.status_code < 400:
                    for key, value in resp.headers.items():
                        headers[key] = value
                
                # Now check for NAS and other devices by checking the response content
                try:
                    get_resp = requests.get(
                        f"{protocol}://{ip_address}:{port}", 
                        timeout=self.timeout,
                        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"},
                        verify=False,
                        allow_redirects=True  # Allow redirects to catch login pages
                    )
                    
                    if get_resp.status_code in [200, 302, 401]:
                        content = get_resp.text.lower()
                        
                        # Check for NAS device indicators in content
                        nas_indicators = {
                            'synology': ['synology', 'diskstation', 'dsm'],
                            'qnap': ['qnap', 'qts', 'nas'],
                            'unraid': ['unraid', 'lime technology'],
                            'truenas': ['truenas', 'freenas'],
                            'wd_mycloud': ['wd my cloud', 'mycloud', 'western digital'],
                            'asustor': ['asustor', 'asus nas'],
                            'terramaster': ['terramaster', 'tnas']
                        }
                        
                        for nas_type, keywords in nas_indicators.items():
                            for keyword in keywords:
                                if keyword in content:
                                    headers[f'X-Content-Contains-{nas_type.capitalize()}'] = 'true'
                                    break
                                    
                        # Check for specific content indicators from ALL device signatures, not just NAS
                        for sig_id, signature in self.engine.signatures.items():
                            if 'content_indicators' in signature:
                                for indicator in signature['content_indicators']:
                                    if indicator.lower() in content:
                                        headers[f'X-Content-Indicator-{sig_id}'] = 'true'
                                        break
                        
                        # Check title for device name clues
                        if '<title>' in content and '</title>' in content:
                            title = content.split('<title>')[1].split('</title>')[0].strip().lower()
                            headers['X-Page-Title'] = title
                        
                        # Look for login forms that might indicate NAS devices
                        login_indicators = ['login', 'signin', 'admin', 'password', 'username']
                        for indicator in login_indicators:
                            if indicator in content:
                                headers['X-Has-Login-Form'] = 'true'
                                break
                except requests.RequestException:
                    pass
                
                # For some devices like UniFi, need to check common management paths
                # and examine response for fingerprinting
                if protocol == "https" and port in [443, 8443]:
                    # Try management paths for Dream Machine devices
                    management_paths = ['/manage', '/network', '/login', '/api/auth/login']
                    for path in management_paths:
                        try:
                            path_url = f"{protocol}://{ip_address}:{port}{path}"
                            path_resp = requests.get(
                                path_url,
                                timeout=self.timeout,
                                headers={"User-Agent": "Pulse-NetworkScanner/1.0"},
                                verify=False,
                                allow_redirects=False
                            )
                            
                            if path_resp.status_code in [200, 302, 401]:
                                # Check content for device identifiers
                                content = path_resp.text.lower()
                                if 'unifi' in content or 'ubiquiti' in content:
                                    # Add a special header to indicate this
                                    headers['X-Content-Contains-UniFi'] = 'true'
                                    
                                    # Check for UDM Pro Max specific strings
                                    for model_id in ["UDM-Pro-Max", "UDMPMAX", "UDM-SE"]:
                                        if model_id.lower() in content:
                                            headers['X-Content-Contains-Model'] = model_id
                                            break
                        except requests.RequestException:
                            continue
            except requests.RequestException:
                pass
        
        return headers
    
    def _get_snmp_data(self, ip_address: str) -> Dict[str, str]:
        """Get SNMP data if available (basic implementation)."""
        snmp_data = {}
        
        # This is a simplified implementation
        # In a real system, you'd use a proper SNMP library like pysnmp
        try:
            # Try SNMP v2c with community string 'public'
            cmd = [
                'snmpwalk', '-v2c', '-c', 'public', '-t', '1', '-r', '1', 
                ip_address, 'system'
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode == 0:
                for line in result.stdout.splitlines():
                    if "::" in line:
                        oid, value = line.split("::", 1)
                        oid = oid.strip()
                        value = value.strip()
                        snmp_data[oid] = value
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
        
        return snmp_data
    
    def _get_mdns_data(self, ip_address: str) -> Dict[str, str]:
        """Get mDNS/bonjour service information."""
        mdns_data = {}
        
        # This is a simplified implementation
        # In a real system, you'd use a proper mDNS library like zeroconf
        try:
            cmd = ['avahi-resolve', '-a', ip_address]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout)
            
            if result.returncode == 0 and result.stdout:
                hostname = result.stdout.strip()
                if hostname:
                    mdns_data['hostname'] = hostname
                
                # Try to get service info for this hostname
                cmd = ['avahi-browse', '-a', '-p', '-r', '-t']
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                
                for line in result.stdout.splitlines():
                    if ip_address in line:
                        parts = line.split(';')
                        if len(parts) >= 7:
                            service_type = parts[0]
                            service_name = parts[3]
                            mdns_data['service_type'] = service_type
                            mdns_data['service_name'] = service_name
        except (subprocess.SubprocessError, subprocess.TimeoutExpired):
            pass
        
        return mdns_data