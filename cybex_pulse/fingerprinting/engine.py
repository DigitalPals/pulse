"""
Fingerprinting engine for device identification.
Provides core functionality to match device signatures.
"""
import importlib
import logging
import os
import re
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class FingerprintEngine:
    """Engine for device fingerprinting and identification."""
    
    def __init__(self):
        self.signatures = {}
        self.device_modules = {}
        self._load_device_modules()
    
    def _load_device_modules(self):
        """Dynamically load all device modules from the devices directory."""
        devices_dir = os.path.join(os.path.dirname(__file__), 'devices')
        for filename in os.listdir(devices_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                module_name = filename[:-3]  # Remove .py extension
                try:
                    module = importlib.import_module(f'cybex_pulse.fingerprinting.devices.{module_name}')
                    if hasattr(module, 'SIGNATURES'):
                        self.device_modules[module_name] = module
                        self.signatures.update(module.SIGNATURES)
                        logger.info(f"Loaded {len(module.SIGNATURES)} signatures from {module_name}")
                except (ImportError, AttributeError) as e:
                    logger.error(f"Failed to load device module {module_name}: {e}")
    
    def identify_device(self, device_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify a device based on its attributes.
        
        Args:
            device_data: Dictionary containing device attributes like MAC, open ports, 
                        HTTP headers, SNMP data, etc.
        
        Returns:
            List of potential device matches with confidence scores
        """
        matches = []
        
        for signature_id, signature in self.signatures.items():
            confidence = self._calculate_match_confidence(device_data, signature)
            if confidence > 0:
                matches.append({
                    'signature_id': signature_id,
                    'device_type': signature.get('device_type', 'Unknown'),
                    'manufacturer': signature.get('manufacturer', 'Unknown'),
                    'model': signature.get('model', 'Unknown'),
                    'confidence': confidence
                })
        
        # Sort matches by confidence score (descending)
        matches.sort(key=lambda x: x['confidence'], reverse=True)
        return matches
    
    def _calculate_match_confidence(self, device_data: Dict[str, Any], 
                                   signature: Dict[str, Any]) -> float:
        """
        Calculate confidence score for a signature match.
        
        Args:
            device_data: Device attributes from scan
            signature: Device signature to match against
        
        Returns:
            Confidence score (0.0-1.0) where 1.0 is highest confidence
        """
        total_weight = 0
        matched_weight = 0
        
        # Check MAC OUI match
        if 'mac_prefix' in signature and 'mac_address' in device_data:
            total_weight += 25
            mac = device_data['mac_address'].upper().replace(':', '').replace('-', '')
            # Compare only the OUI part (first 6 characters) of the MAC address
            mac_oui = mac[:6]
            if any(mac_oui == prefix.upper().replace(':', '').replace('-', '')[:6] 
                  for prefix in signature['mac_prefix']):
                matched_weight += 25
        
        # Check open ports
        if 'open_ports' in signature and 'open_ports' in device_data:
            sig_ports = set(signature['open_ports'])
            device_ports = set(device_data['open_ports'])
            
            if sig_ports:
                total_weight += 15
                common_ports = sig_ports.intersection(device_ports)
                if common_ports:
                    # Calculate port match percentage
                    port_match_pct = len(common_ports) / len(sig_ports)
                    matched_weight += 15 * port_match_pct
        
        # Check HTTP signature
        if 'http_signature' in signature and 'http_headers' in device_data:
            total_weight += 20
            headers = device_data['http_headers']
            http_sig = signature['http_signature']
            
            matches = 0
            for header, pattern in http_sig.items():
                if header in headers and re.search(pattern, headers[header], re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                matched_weight += 20 * (matches / len(http_sig))
                
        # Check for content markers in HTTP headers/content for ALL device types
        if 'http_headers' in device_data:
            headers = device_data['http_headers']
            manufacturer = signature.get('manufacturer', '').lower()
            signature_id = None
            
            # Find the signature_id by matching the signature
            for sig_id, sig in self.signatures.items():
                if sig == signature:
                    signature_id = sig_id
                    break

            # Different weights based on device type
            if 'device_type' in signature and signature['device_type'] == 'NAS':
                total_weight += 30  # Higher weight for NAS devices
            elif 'content_indicators' in signature:
                total_weight += 25  # Weight for other devices with content indicators
            else:
                total_weight += 0  # Skip this test for devices without content indicators
                
            if total_weight > 0:  # Only do checks if we added to total_weight
                # Check for custom content markers from our enhanced scanner
                content_markers = [
                    f'X-Content-Contains-{manufacturer.capitalize()}',
                    f'X-Content-Contains-{signature.get("model", "").capitalize()}'
                ]
                
                # Add specific content indicator marker for this signature
                if signature_id:
                    content_markers.append(f'X-Content-Indicator-{signature_id}')
                
                # Check if any of the markers are present
                content_matched = False
                for marker in content_markers:
                    if marker in headers and headers[marker] == 'true':
                        if 'device_type' in signature and signature['device_type'] == 'NAS':
                            matched_weight += 30
                        else:
                            matched_weight += 25
                        content_matched = True
                        break
                
                # Check if content_indicators exists and verify explicit required indicators
                if 'content_indicators' in signature and not content_matched:
                    # If signature has content indicators but none matched, this is a strong negative signal
                    # We won't add any matching weight, effectively reducing the confidence score
                    pass
                        
                # Check page title for manufacturer/model mentions
                if 'X-Page-Title' in headers:
                    title = headers['X-Page-Title'].lower()
                    if manufacturer in title or signature.get('model', '').lower() in title:
                        matched_weight += 15
        
        # Check SNMP data
        if 'snmp_signature' in signature and 'snmp_data' in device_data:
            total_weight += 15
            snmp_sig = signature['snmp_signature']
            snmp_data = device_data['snmp_data']
            
            matches = 0
            for oid, pattern in snmp_sig.items():
                if oid in snmp_data and re.search(pattern, snmp_data[oid], re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                matched_weight += 15 * (matches / len(snmp_sig))
        
        # Check mDNS data
        if 'mdns_signature' in signature and 'mdns_data' in device_data:
            total_weight += 10
            mdns_sig = signature['mdns_signature']
            mdns_data = device_data['mdns_data']
            
            matches = 0
            for key, pattern in mdns_sig.items():
                if key in mdns_data and re.search(pattern, mdns_data[key], re.IGNORECASE):
                    matches += 1
            
            if matches > 0:
                matched_weight += 10 * (matches / len(mdns_sig))
        
        # Check hostname patterns
        if 'hostname_patterns' in signature and 'hostname' in device_data and device_data['hostname']:
            total_weight += 15
            hostname = device_data['hostname'].lower()
            hostname_patterns = signature['hostname_patterns']
            
            for pattern in hostname_patterns:
                if re.search(pattern, hostname, re.IGNORECASE):
                    matched_weight += 15
                    break
        
        # Calculate confidence (prevent division by zero)
        if total_weight == 0:
            return 0.0
        
        return matched_weight / total_weight
    
    def get_available_modules(self) -> List[str]:
        """Get list of loaded device modules."""
        return list(self.device_modules.keys())
    
    def get_signature_count(self) -> int:
        """Get total count of loaded signatures."""
        return len(self.signatures)