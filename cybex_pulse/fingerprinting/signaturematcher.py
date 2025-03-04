"""
Signature matcher module for the fingerprinting engine.
Provides specialized matching logic for different device attributes.
"""
import re
from typing import Dict, Any, List, Optional, Set, Tuple

class SignatureMatcher:
    """
    Handles the matching of device attributes against signature patterns.
    Each matcher method focuses on a specific attribute type.
    """
    
    @staticmethod
    def match_mac_prefix(device_mac: Optional[str], signature_prefixes: List[str]) -> float:
        """
        Match device MAC address against signature MAC OUI prefixes.
        
        Args:
            device_mac: Device MAC address
            signature_prefixes: List of MAC OUI prefixes to match against
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not device_mac or not signature_prefixes:
            return 0.0
            
        # Optimize by pre-processing the MAC address once
        mac = device_mac.upper().replace(':', '').replace('-', '')
        # Compare only the OUI part (first 6 characters) of the MAC address
        mac_oui = mac[:6]
        
        # Pre-process all prefixes at once to avoid repeated operations
        formatted_prefixes = [prefix.upper().replace(':', '').replace('-', '')[:6]
                             for prefix in signature_prefixes]
        
        # Use any() for more efficient iteration
        if any(mac_oui == prefix for prefix in formatted_prefixes):
            return 1.0
                
        return 0.0
    
    @staticmethod
    def match_open_ports(device_ports: List[int], signature_ports: List[int]) -> float:
        """
        Match device open ports against signature expected ports.
        
        Args:
            device_ports: List of open ports on the device
            signature_ports: List of expected open ports in the signature
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not signature_ports:
            return 0.0
            
        device_port_set = set(device_ports)
        signature_port_set = set(signature_ports)
        
        common_ports = signature_port_set.intersection(device_port_set)
        
        if not common_ports:
            return 0.0
            
        # Calculate port match percentage
        return len(common_ports) / len(signature_port_set)
    
    @staticmethod
    def match_http_signature(device_headers: Dict[str, str], 
                           http_signature: Dict[str, str]) -> float:
        """
        Match device HTTP headers against signature HTTP patterns.
        
        Args:
            device_headers: HTTP headers from the device
            http_signature: HTTP header patterns from the signature
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not http_signature:
            return 0.0
            
        matches = 0
        
        for header, pattern in http_signature.items():
            if header in device_headers and re.search(pattern, device_headers[header], re.IGNORECASE):
                matches += 1
        
        if matches == 0:
            return 0.0
            
        return matches / len(http_signature)
    
    @staticmethod
    def match_content_indicators(device_headers: Dict[str, str], 
                               manufacturer: str,
                               model: str,
                               signature_id: str,
                               content_indicators: Optional[List[str]] = None) -> float:
        """
        Match content indicators in HTTP response.
        
        Args:
            device_headers: HTTP headers including custom X-Content headers
            manufacturer: Device manufacturer name
            model: Device model name
            signature_id: Signature identifier
            content_indicators: Optional list of content indicator strings
            
        Returns:
            Match score between 0.0 and 1.0
        """
        # Check for custom content markers from our enhanced scanner
        content_markers = [
            f'X-Content-Contains-{manufacturer.capitalize()}',
            f'X-Content-Contains-{model.capitalize()}',
            f'X-Content-Indicator-{signature_id}'
        ]
        
        # Check if any of the markers are present
        for marker in content_markers:
            if marker in device_headers and device_headers[marker] == 'true':
                return 1.0
        
        # Check page title for manufacturer/model mentions
        if 'X-Page-Title' in device_headers:
            title = device_headers['X-Page-Title'].lower()
            if manufacturer.lower() in title or model.lower() in title:
                return 0.6  # Partial match
        
        return 0.0
    
    @staticmethod
    def match_snmp_data(device_snmp: Dict[str, str], 
                      snmp_signature: Dict[str, str]) -> float:
        """
        Match device SNMP data against signature SNMP patterns.
        
        Args:
            device_snmp: SNMP data from the device
            snmp_signature: SNMP data patterns from the signature
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not snmp_signature:
            return 0.0
            
        matches = 0
        
        for oid, pattern in snmp_signature.items():
            if oid in device_snmp and re.search(pattern, device_snmp[oid], re.IGNORECASE):
                matches += 1
        
        if matches == 0:
            return 0.0
            
        return matches / len(snmp_signature)
    
    @staticmethod
    def match_mdns_data(device_mdns: Dict[str, str],
                      mdns_signature: Dict[str, str]) -> float:
        """
        Match device mDNS data against signature mDNS patterns.
        
        Args:
            device_mdns: mDNS data from the device
            mdns_signature: mDNS data patterns from the signature
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not mdns_signature:
            return 0.0
            
        matches = 0
        
        for key, pattern in mdns_signature.items():
            if key in device_mdns and re.search(pattern, device_mdns[key], re.IGNORECASE):
                matches += 1
        
        if matches == 0:
            return 0.0
            
        return matches / len(mdns_signature)
    
    @staticmethod
    def match_hostname(device_hostname: Optional[str],
                     hostname_patterns: List[str]) -> float:
        """
        Match device hostname against signature hostname patterns.
        
        Args:
            device_hostname: Device hostname
            hostname_patterns: List of hostname patterns from the signature
            
        Returns:
            Match score between 0.0 and 1.0
        """
        if not device_hostname or not hostname_patterns:
            return 0.0
            
        hostname = device_hostname.lower()
        
        for pattern in hostname_patterns:
            if re.search(pattern, hostname, re.IGNORECASE):
                return 1.0
        
        return 0.0