"""
Network scanner module for Cybex Pulse.

This module provides functionality for:
- Discovering devices on local networks using various scanning methods
- Detecting when devices connect to or disconnect from the network
- Identifying device types through basic vendor detection
- Integration with advanced device fingerprinting system
"""
import json
import logging
import re
import subprocess
import time
from typing import Dict, List, Optional, Set, Tuple, Any

from cybex_pulse.utils.debug_logger import DebugLogger
from cybex_pulse.utils.mac_utils import normalize_mac, normalize_vendor

from cybex_pulse.core.alerting import AlertManager
from cybex_pulse.core.fingerprinting_manager import FingerprintingManager
from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config


class NetworkScanner:
    """Network scanner for detecting and fingerprinting devices on the local network.
    
    This class is responsible for:
    - Discovering devices using nmap or arp-scan
    - Tracking device connections and disconnections
    - Basic device identification using MAC/vendor mapping
    - Integration with advanced fingerprinting system
    - Alerting on new device detection
    """
    
    def __init__(self, config: Config, db_manager: DatabaseManager, logger: logging.Logger):
        """Initialize the network scanner.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logger
        self.alert_manager = AlertManager(config, db_manager, logger)
        
        # Initialize fingerprinting manager
        self.fingerprinting_manager = FingerprintingManager(config, db_manager, logger)
        
        # Keep track of devices seen in the current scan
        self.current_scan_devices = set()
        
        # Keep track of devices seen in the previous scan
        self.previous_scan_devices = set()
        
        # Keep track of devices that are currently being processed
        # to prevent duplicate entries during a single scan
        self.processing_devices = set()
        
        # Debug logger
        self.debug = None
        if config:
            self.debug = DebugLogger(logger, config)
    
    def scan(self) -> None:
        """Scan the network for devices."""
        self.logger.info("Starting network scan")
        
        try:
            if self.debug and self.debug.is_debug_enabled():
                self.debug.start_timer("network_scan")
                self.debug.debug("Starting network scan")
            
            # Get subnet from config
            subnet = self.config.get("network", "subnet")
            if not subnet:
                self.logger.error("Subnet not configured")
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.debug("Network scan aborted: Subnet not configured")
                return
            
            # Clear current scan devices
            self.current_scan_devices = set()
            
            # Clear processing devices for this scan cycle
            self.processing_devices = set()
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Scanning subnet: {subnet}")
                self.debug.start_timer("nmap_scan")
            
            # Run network scan using nmap ping scan (-sn)
            devices = self._run_nmap_scan(subnet)
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.end_timer("nmap_scan")
                if devices:
                    self.debug.debug(f"Nmap scan found {len(devices)} devices")
                else:
                    self.debug.debug("Nmap scan found no devices, falling back to arp-scan")
            
            if not devices and self.config.get("network", "fallback_to_arp_scan", True):
                # Fall back to arp-scan if nmap fails
                self.logger.info("Falling back to arp-scan")
                
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.start_timer("arp_scan")
                    
                devices = self._run_arp_scan(subnet)
                
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.end_timer("arp_scan")
                    if devices:
                        self.debug.debug(f"Arp-scan found {len(devices)} devices")
                    else:
                        self.debug.debug("Arp-scan found no devices")
            
            if devices is None:
                self.logger.error("Network scan failed")
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.debug("Network scan failed: Both nmap and arp-scan returned no results")
                return
            
            # Process scan results
            if self.debug and self.debug.is_debug_enabled():
                self.debug.start_timer("process_scan_results")
                self.debug.debug(f"Processing scan results for {len(devices)} devices")
                
            self._process_scan_results(devices)
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.end_timer("process_scan_results")
                self.debug.debug(f"Processed {len(self.current_scan_devices)} unique devices")
            
            # Check for devices that went offline
            if self.debug and self.debug.is_debug_enabled():
                self.debug.start_timer("check_offline_devices")
                
            self._check_offline_devices()
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.end_timer("check_offline_devices")
            
            # Update previous scan devices
            self.previous_scan_devices = self.current_scan_devices.copy()
            
            self.logger.info(f"Network scan completed, found {len(devices)} devices")
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.end_timer("network_scan")
                self.debug.debug(f"Network scan completed in {self.debug.end_timer('network_scan')} seconds")
        finally:
            # Ensure database connection is closed after scan
            self.db_manager.close()
    
    def _run_nmap_scan(self, subnet: str) -> Optional[List[Dict[str, str]]]:
        """Run nmap ping scan (-sn) on the specified subnet.
        
        Args:
            subnet: Subnet to scan in CIDR notation
            
        Returns:
            List of dictionaries containing device information or None if scan failed
        """
        try:
            self.logger.debug(f"Running nmap ping scan on subnet: {subnet}")
            
            # Run nmap ping scan command
            cmd = ["nmap", "-sn", subnet]
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Executing command: {' '.join(cmd)}")
                self.debug.start_timer("nmap_subprocess")
                self.debug.track_resource(f"nmap_process_{subnet}", "subprocess")
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60
                )
                
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.end_timer("nmap_subprocess")
                    self.debug.debug(f"Command completed with return code: {result.returncode}")
                    self.debug.release_resource(f"nmap_process_{subnet}")
                    
            except (subprocess.SubprocessError, subprocess.TimeoutExpired) as e:
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.debug(f"Command failed: {e}, trying with sudo")
                    self.debug.end_timer("nmap_subprocess")
                    self.debug.release_resource(f"nmap_process_{subnet}")
                    self.debug.start_timer("sudo_nmap_subprocess")
                    self.debug.track_resource(f"sudo_nmap_process_{subnet}", "subprocess")
                
                # If that fails, try with sudo
                cmd = ["sudo", "nmap", "-sn", subnet]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=60
                )
                
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.end_timer("sudo_nmap_subprocess")
                    self.debug.debug(f"Sudo command completed with return code: {result.returncode}")
                    self.debug.release_resource(f"sudo_nmap_process_{subnet}")
            
            # Parse text output
            if self.debug and self.debug.is_debug_enabled():
                self.debug.start_timer("parse_nmap_output")
                
            parsed_results = self._parse_nmap_scan_text(result.stdout)
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.end_timer("parse_nmap_output")
                self.debug.debug(f"Parsed {len(parsed_results) if parsed_results else 0} devices from nmap output")
                
            return parsed_results
            
        except subprocess.SubprocessError as e:
            self.logger.warning(f"Error running nmap scan: {e}")
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Subprocess error in nmap scan: {e}")
                # Make sure to release any tracked resources
                self.debug.release_resource(f"nmap_process_{subnet}")
                self.debug.release_resource(f"sudo_nmap_process_{subnet}")
            
            # Check if command not found
            if isinstance(e, subprocess.CalledProcessError) and e.returncode == 127:
                self.logger.warning("nmap command not found. Please install nmap.")
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.debug("nmap command not found (error code 127)")
            
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error running nmap scan: {e}")
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Unexpected exception in nmap scan: {type(e).__name__}: {e}")
                # Make sure to release any tracked resources
                self.debug.release_resource(f"nmap_process_{subnet}")
                self.debug.release_resource(f"sudo_nmap_process_{subnet}")
                
            return None
    
    def _parse_nmap_scan_text(self, output: str) -> List[Dict[str, str]]:
        """Parse nmap ping scan (-sn) text output.
        
        Args:
            output: nmap -sn command output
            
        Returns:
            List of dictionaries containing device information
        """
        devices = []
        
        # Variables to store current device info
        current_device = {}
        
        for line in output.splitlines():
            # Look for Nmap scan report lines which contain the IP
            ip_match = re.search(r"Nmap scan report for (?:([^\s]+) )?(?:\()?(\d+\.\d+\.\d+\.\d+)(?:\))?", line)
            if ip_match:
                # If we already have a device, add it to our list
                if current_device and "ip" in current_device:
                    devices.append(current_device)
                
                # Start new device
                hostname = ip_match.group(1) or ""
                ip_address = ip_match.group(2)
                current_device = {"ip": ip_address, "hostname": hostname, "vendor": "", "mac": ""}
                continue
            
            # Look for MAC address lines
            mac_match = re.search(r"MAC Address: ([0-9A-F:]{17}) \(([^)]+)\)", line)
            if mac_match and current_device:
                mac_address = mac_match.group(1)
                vendor = mac_match.group(2)
                current_device["mac"] = normalize_mac(mac_address)
                current_device["vendor"] = normalize_vendor(vendor)
                continue
        
        # Add the last device if we have one
        if current_device and "ip" in current_device:
            devices.append(current_device)
            
        # For devices without MAC addresses (which means nmap didn't get the MAC details)
        # we'll try to resolve them using the ARP table
        devices = self._enrich_device_data(devices)
        
        return devices
        
    def _enrich_device_data(self, devices: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """Enrich device data with information from ARP cache.
        
        Args:
            devices: List of dictionaries containing device information
            
        Returns:
            Updated list of devices with more complete information
        """
        # Get all ARP entries
        arp_entries = {}
        try:
            result = subprocess.run(
                ["arp", "-an"],
                capture_output=True,
                text=True,
                check=False
            )
            
            for line in result.stdout.splitlines():
                ip_match = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
                mac_match = re.search(r"at ([0-9a-f:]{17})", line, re.IGNORECASE)
                if ip_match and mac_match:
                    ip = ip_match.group(1)
                    mac = normalize_mac(mac_match.group(1))
                    arp_entries[ip] = mac
        except Exception as e:
            self.logger.debug(f"Error getting ARP entries: {e}")
        
        # Fill in missing MAC addresses
        for device in devices:
            ip = device.get("ip")
            if ip and not device.get("mac") and ip in arp_entries:
                device["mac"] = arp_entries[ip]
                # Also try to get vendor information based on MAC
                device["vendor"] = self._get_vendor_from_mac(arp_entries[ip])
        
        return devices
    
    def _get_vendor_from_mac(self, mac: str) -> str:
        """Get vendor name from MAC address OUI.
        
        Args:
            mac: MAC address
            
        Returns:
            Vendor name if found, otherwise empty string
        """
        # This is a simple implementation
        # In a real system, you'd use the OUI database or an API
        return ""
    
    def _run_arp_scan(self, subnet: str) -> Optional[List[Dict[str, str]]]:
        """Run arp-scan on the specified subnet.
        
        Args:
            subnet: Subnet to scan in CIDR notation
            
        Returns:
            List of dictionaries containing device information or None if scan failed
        """
        # First try arp-scan
        devices = self._try_arp_scan(subnet)
        
        # If arp-scan fails, fall back to using the ARP cache
        if devices is None:
            self.logger.info("Falling back to ARP cache scan")
            devices = self._scan_arp_cache()
            
        return devices
    
    def _try_arp_scan(self, subnet: str) -> Optional[List[Dict[str, str]]]:
        """Try to run arp-scan on the specified subnet.
        
        Args:
            subnet: Subnet to scan in CIDR notation
            
        Returns:
            List of dictionaries containing device information or None if scan failed
        """
        try:
            self.logger.debug(f"Running arp-scan on subnet: {subnet}")
            
            # Run arp-scan command without sudo first
            cmd = ["arp-scan", subnet]
            
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )
            except (subprocess.SubprocessError, subprocess.TimeoutExpired):
                # If that fails, try with sudo
                cmd = ["sudo", "arp-scan", subnet]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=10
                )
            
            # Parse text output directly since arp-scan doesn't support JSON output
            return self._parse_arp_scan_text(result.stdout)
        except subprocess.SubprocessError as e:
            self.logger.warning(f"Error running arp-scan: {e}")
            
            # Check if command not found
            if isinstance(e, subprocess.CalledProcessError) and e.returncode == 127:
                self.logger.warning("arp-scan command not found. Please install arp-scan.")
            
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error running arp-scan: {e}")
            return None
    
    def _scan_arp_cache(self) -> List[Dict[str, str]]:
        """Scan the ARP cache for devices.
        
        Returns:
            List of dictionaries containing device information
        """
        devices = []
        
        try:
            # Run the arp command to get the ARP cache
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                text=True,
                check=False
            )
            
            # Parse the output
            pattern = r"([^\s]+)\s+\((\d+\.\d+\.\d+\.\d+)\)\s+at\s+([0-9a-fA-F:]{17})"
            
            for line in result.stdout.splitlines():
                match = re.search(pattern, line)
                if match:
                    hostname, ip_address, mac_address = match.groups()
                    devices.append({
                        "ip": ip_address,
                        "mac": normalize_mac(mac_address),
                        "vendor": "",
                        "hostname": hostname
                    })
            
            # If arp -a didn't work, try ip neigh
            if not devices:
                result = subprocess.run(
                    ["ip", "neigh"],
                    capture_output=True,
                    text=True,
                    check=False
                )
                
                # Parse the output
                pattern = r"(\d+\.\d+\.\d+\.\d+).*\s+([0-9a-f:]{17})"
                
                for line in result.stdout.splitlines():
                    match = re.search(pattern, line.lower())
                    if match:
                        ip_address, mac_address = match.groups()
                        
                        # Resolve hostname for the IP address
                        hostname = self._resolve_hostname(ip_address)
                        
                        devices.append({
                            "ip": ip_address,
                            "mac": normalize_mac(mac_address),
                            "vendor": "",
                            "hostname": hostname
                        })
        except Exception as e:
            self.logger.warning(f"Error scanning ARP cache: {e}")
        
        return devices
    
    def _resolve_hostname(self, ip_address: str) -> str:
        """Resolve hostname for an IP address using getent hosts.
        
        Args:
            ip_address: IP address to resolve
            
        Returns:
            Hostname if found, empty string otherwise
        """
        try:
            result = subprocess.run(
                ["getent", "hosts", ip_address],
                capture_output=True,
                text=True,
                check=False,
                timeout=2
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Parse the output - format is "IP_ADDRESS HOSTNAME [ALIASES...]"
                parts = result.stdout.strip().split()
                if len(parts) > 1:
                    return parts[1]  # Return the hostname (second field)
        except Exception as e:
            self.logger.debug(f"Error resolving hostname for {ip_address}: {e}")
            
        return ""
    
    def _parse_arp_scan_text(self, output: str) -> List[Dict[str, str]]:
        """Parse arp-scan text output.
        
        Args:
            output: arp-scan command output
            
        Returns:
            List of dictionaries containing device information
        """
        devices = []
        
        # Regular expression to match IP, MAC, and vendor
        pattern = r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]{17})\s+(.*)"
        
        for line in output.splitlines():
            match = re.match(pattern, line)
            if match:
                ip_address, mac_address, vendor = match.groups()
                
                # Resolve hostname for the IP address
                hostname = self._resolve_hostname(ip_address)
                
                devices.append({
                    "ip": ip_address,
                    "mac": normalize_mac(mac_address),
                    "vendor": normalize_vendor(vendor.strip()),
                    "hostname": hostname
                })
        
        return devices
    def _process_scan_results(self, devices: List[Dict[str, str]]) -> None:
        """Process scan results and update database.
        
        Args:
            devices: List of dictionaries containing device information
        """
        # Prepare a list of devices for additional fingerprinting
        devices_to_fingerprint = []
        
        for device in devices:
            mac_address = device.get("mac")
            ip_address = device.get("ip")
            vendor = device.get("vendor", "")
            hostname = device.get("hostname", "")
            
            if not mac_address or not ip_address:
                continue
            
            # Normalize MAC address to lowercase for consistent comparison
            mac_address = normalize_mac(mac_address)
            
            # Normalize vendor name to remove inconsistencies
            vendor = normalize_vendor(vendor)
                
            # Skip if this device is already being processed in this scan cycle
            # This prevents duplicate entries with the same MAC address
            if mac_address in self.processing_devices:
                self.logger.debug(f"Skipping duplicate device: {mac_address} ({ip_address})")
                continue
                
            # Mark this device as being processed
            self.processing_devices.add(mac_address)
            
            # Add to current scan devices
            self.current_scan_devices.add(mac_address)
            self.current_scan_devices.add(mac_address)
            
            # Check if device exists in database
            existing_device = self.db_manager.get_device(mac_address)
            
            # First check if the device is already marked as fingerprinted in the database
            # If it is, skip vendor identification completely
            if existing_device and existing_device.get("is_fingerprinted", False):
                self.logger.info(f"Device {mac_address} is already marked as fingerprinted, skipping vendor identification")
                device_identified = False
            else:
                is_fingerprinted = existing_device.get('is_fingerprinted') if existing_device else False
                self.logger.info(f"Device {mac_address} is NOT marked as fingerprinted (is_fingerprinted={is_fingerprinted}), will check vendor identification")
                # Process vendor information from nmap -sn results
                device_identified = False
                device_type = ""
                manufacturer = ""
                model = ""
                confidence = 0.0
                
                # Try to identify device from vendor string
                if vendor:
                    self.logger.debug(f"Device {mac_address} vendor from nmap: {vendor}")
                    
                    # Extract manufacturer from vendor string
                    manufacturer = vendor.split(" ")[0] if " " in vendor else vendor
                    
                    # Simplified mapping of common vendor names to device types
                    vendor_to_device_mapping = {
                        "Philips": {"type": "lighting", "model": "Hue"},
                        "Phillips": {"type": "lighting", "model": "Hue"},  # Common misspelling
                        "TP-Link": {"type": "networking", "model": ""},
                        "Amazon": {"type": "media", "model": "Echo"},
                        "Apple": {"type": "computer", "model": ""},
                        "Google": {"type": "media", "model": ""},
                        "Samsung": {"type": "media", "model": ""},
                        "Sonos": {"type": "media", "model": "Speaker"},
                        "Nest": {"type": "thermostat", "model": ""},
                        "Ring": {"type": "camera", "model": "Doorbell"},
                        "Wyze": {"type": "camera", "model": ""},
                        "Roku": {"type": "media", "model": ""},
                        "Belkin": {"type": "networking", "model": ""},
                        "Netgear": {"type": "networking", "model": ""},
                        "D-Link": {"type": "networking", "model": ""},
                        "Synology": {"type": "nas", "model": ""},
                        "QNAP": {"type": "nas", "model": ""},
                        "Ubiquiti": {"type": "networking", "model": ""},
                        "Cisco": {"type": "networking", "model": ""},
                        "Linksys": {"type": "networking", "model": ""},
                        "Asus": {"type": "networking", "model": ""},
                        "AVM": {"type": "networking", "model": ""},
                    }
                    
                    # Check if we can identify the device from the vendor alone
                    for v_key, v_info in vendor_to_device_mapping.items():
                        if v_key.lower() in vendor.lower():
                            device_type = v_info["type"]
                            model = v_info["model"]
                            confidence = 0.8  # High confidence for direct vendor match
                            device_identified = True
                            break
                    
                    # If device was identified from vendor, update the fingerprint data
                    if device_identified:
                        device_name = f"{manufacturer} {model}" if manufacturer and model else hostname or mac_address
                        self.logger.info(
                            f"Device identified from nmap vendor: {device_name} ({ip_address}) "
                            f"as {device_type} with {confidence:.2f} confidence"
                        )
            
            if existing_device:
                # Prepare update parameters - always update IP address
                update_params = {"ip_address": ip_address}
                
                # Only update hostname if it's empty in the database
                # This prevents overwriting user-set hostnames
                if not existing_device.get('hostname'):
                    update_params["hostname"] = hostname
                    
                # Only update vendor if it's empty or matches the existing one from the MAC lookup
                # This prevents overwriting user-edited vendor names
                existing_vendor = existing_device.get('vendor', '')
                if not existing_vendor or (vendor and existing_vendor == vendor):
                    update_params["vendor"] = vendor
                
                # Update existing device with the parameters we determined
                self.db_manager.update_device(mac_address, **update_params)
                
                # Check if we should update fingerprinting info based on nmap results
                if device_identified and existing_device:
                    # First check if the device is already marked as fingerprinted
                    if existing_device.get("is_fingerprinted", False):
                        self.logger.debug(f"Device {mac_address} is already marked as fingerprinted, skipping vendor identification")
                    else:
                        # Check if device is already properly fingerprinted
                        existing_type = existing_device.get("device_type", "")
                        fingerprint_date = existing_device.get("fingerprint_date", 0)
                        fingerprint_confidence = existing_device.get("fingerprint_confidence", 0)
                        
                        unknown_types = ["", "unknown", "unidentified", None]
                        has_valid_type = existing_type not in unknown_types
                        has_valid_date = fingerprint_date is not None and fingerprint_date > 0
                        
                        threshold = float(self.config.get("fingerprinting", "confidence_threshold", 0.5))
                        has_high_confidence = fingerprint_confidence is not None and fingerprint_confidence >= threshold
                        
                        already_fingerprinted = has_valid_type and has_valid_date and has_high_confidence
                        
                        # If the device meets fingerprinting criteria but isn't explicitly marked,
                        # update the database to set the is_fingerprinted flag
                        if already_fingerprinted and not existing_device.get("is_fingerprinted"):
                            self.logger.debug(f"Device {mac_address} meets fingerprinting criteria but is not explicitly marked. Setting is_fingerprinted flag.")
                            self.db_manager.update_device_metadata(mac_address, {'is_fingerprinted': True})
                            # Skip further processing since we've marked it as fingerprinted
                            continue
                        
                        # Only update if the device is not already fingerprinted or if the new confidence is higher
                        if not already_fingerprinted or confidence > fingerprint_confidence:
                            self.logger.debug(f"Updating fingerprint info for device {mac_address} from vendor match")
                            device_info = {
                                'device_type': device_type,
                                'device_model': model,
                                'device_manufacturer': manufacturer,
                                'fingerprint_confidence': confidence,
                                'fingerprint_date': int(time.time()),
                                'is_fingerprinted': True  # Mark the device as fingerprinted to prevent automatic re-fingerprinting
                            }
                            self.db_manager.update_device_metadata(mac_address, device_info)
                            
                            # Verify that the is_fingerprinted flag was set
                            updated_device = self.db_manager.get_device(mac_address)
                            if updated_device and updated_device.get("is_fingerprinted"):
                                self.logger.debug(f"Successfully marked device {mac_address} as fingerprinted in database")
                            else:
                                self.logger.warning(f"Failed to mark device {mac_address} as fingerprinted in database")
                            
                            # Log event for identified devices
                            # Use existing_device.get('hostname') to ensure we use the DB-stored hostname value
                            hostname = existing_device.get('hostname', '')
                            device_name = f"{manufacturer} {model}" if manufacturer and model else (hostname or mac_address)
                            self.db_manager.log_event(
                                self.db_manager.EVENT_DEVICE_FINGERPRINTED,
                                "info",
                                f"Device identified: {device_name} ({ip_address})",
                                json.dumps({
                                    'mac': mac_address,
                                    'ip': ip_address,
                                    'hostname': hostname,
                                    'manufacturer': manufacturer,
                                    'model': model,
                                    'device_type': device_type,
                                    'confidence': confidence
                                })
                            )
                        else:
                            self.logger.debug(
                                f"Device {mac_address} already fingerprinted with higher or equal confidence "
                                f"({fingerprint_confidence} >= {confidence}), skipping update"
                            )
                else:
                    # Add to fingerprinting queue only if not already identified and not already fingerprinted
                    if self.fingerprinting_manager.is_enabled():
                        # First check if the device is explicitly marked as fingerprinted
                        if existing_device.get("is_fingerprinted", False):
                            self.logger.debug(f"Device {mac_address} is already marked as fingerprinted, skipping fingerprinting")
                        # Otherwise check if the device should be fingerprinted (not already fingerprinted with high confidence)
                        elif self.fingerprinting_manager.should_fingerprint_device(existing_device):
                            devices_to_fingerprint.append({
                                "ip_address": ip_address,
                                "mac_address": mac_address
                            })
                        else:
                            self.logger.debug(f"Skipping fingerprinting for already fingerprinted device: {mac_address} ({ip_address})")
            else:
                # New device detected
                device_name = hostname or vendor or mac_address
                self.logger.info(f"New device detected: {device_name} ({ip_address})")
                
                # Add to database with any fingerprinting data we may have from nmap
                add_data = {
                    "hostname": hostname,
                    "vendor": vendor,  # For new devices, we set the initial vendor from the scan
                }
                
                # If device was identified from vendor, add the fingerprint data
                if device_identified:
                    add_data.update({
                        "device_type": device_type,
                        "device_model": model,
                        "device_manufacturer": manufacturer,
                        "fingerprint_confidence": confidence,
                        "fingerprint_date": int(time.time()),
                        "is_fingerprinted": True  # Mark the device as fingerprinted to prevent automatic re-fingerprinting
                    })
                
                # Add to database
                self.db_manager.add_device(mac_address, ip_address, **add_data)
                
                # Verify that the is_fingerprinted flag was set for devices identified from vendor
                if device_identified:
                    new_device = self.db_manager.get_device(mac_address)
                    if new_device and new_device.get("is_fingerprinted"):
                        self.logger.debug(f"Successfully marked new device {mac_address} as fingerprinted in database")
                    else:
                        self.logger.warning(f"Failed to mark new device {mac_address} as fingerprinted in database")
                
                # For new devices, add to fingerprinting queue if not identified from vendor
                # (New devices won't have fingerprinting data in the database yet)
                if not device_identified and self.fingerprinting_manager.is_enabled():
                    # Get the newly created device from the database to check if it should be fingerprinted
                    new_device = self.db_manager.get_device(mac_address)
                    if new_device and not new_device.get("is_fingerprinted", False):
                        self.logger.debug(f"Adding new device to fingerprinting queue: {mac_address} ({ip_address})")
                        devices_to_fingerprint.append({
                            "ip_address": ip_address,
                            "mac_address": mac_address
                        })
                    else:
                        is_fingerprinted = new_device.get("is_fingerprinted", False) if new_device else False
                        self.logger.debug(f"New device {mac_address} is {'already marked as fingerprinted' if is_fingerprinted else 'not found in database'}, skipping")
                
                # Log event
                self.db_manager.log_event(
                    self.db_manager.EVENT_DEVICE_DETECTED,
                    "info",
                    f"New device detected: {hostname or mac_address} ({ip_address})",
                    json.dumps({"mac": mac_address, "ip": ip_address, "vendor": vendor, "hostname": hostname})
                )
                
                # Send alert if enabled
                if self.config.get("alerts", "new_device"):
                    self.alert_manager.send_alert(
                        "New Device Detected",
                        f"New device connected to network:\nName: {hostname or 'Unknown'}\nMAC: {mac_address}\nIP: {ip_address}\nVendor: {vendor}"
                    )
        
        # Perform advanced fingerprinting on devices that need it
        if devices_to_fingerprint and self.fingerprinting_manager.is_enabled():
            self.fingerprinting_manager.fingerprint_devices(devices_to_fingerprint)
    
    def _check_offline_devices(self) -> None:
        """Check for devices that went offline."""
        # Get all devices from previous scan that are not in current scan
        offline_devices = self.previous_scan_devices - self.current_scan_devices
        
        for mac_address in offline_devices:
            # Normalize MAC address to lowercase for consistent comparison
            mac_address = normalize_mac(mac_address)
            
            # Double-check that this device is truly offline and not just processed earlier
            # This prevents a device from being marked as both online and offline in the same scan
            if mac_address in self.processing_devices:
                self.logger.debug(f"Device {mac_address} was already processed in this scan, not marking as offline")
                continue
                
            device = self.db_manager.get_device(mac_address)
            if not device:
                continue
            
            ip_address = device.get('ip_address', 'Unknown')
            hostname = device.get('hostname', '')
            vendor = device.get('vendor', '')
            device_name = hostname or vendor or mac_address
            self.logger.info(f"Device went offline: {device_name} ({ip_address})")
            
            # Don't log events for devices without a hostname
            if hostname:
                # Log event with device name and IP
                self.db_manager.log_event(
                    self.db_manager.EVENT_DEVICE_OFFLINE,
                    "info",
                    f"Device went offline: {hostname} ({ip_address})",
                    json.dumps({"mac": mac_address, "ip": ip_address, "hostname": hostname})
                )
            
            # Send alert if enabled
            if device.get("is_important", False) and self.config.get("alerts", "important_device_offline"):
                self.alert_manager.send_alert(
                    "Important Device Offline",
                    f"Important device went offline:\nName: {hostname or 'Unknown'}\nMAC: {mac_address}\nIP: {ip_address}\nVendor: {vendor}"
                )
            elif self.config.get("alerts", "device_offline"):
                self.alert_manager.send_alert(
                    "Device Offline",
                    f"Device went offline:\nName: {hostname or 'Unknown'}\nMAC: {mac_address}\nIP: {ip_address}\nVendor: {vendor}"
                )