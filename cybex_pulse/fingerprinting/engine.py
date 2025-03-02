"""
Fingerprinting engine for device identification.
Provides core functionality to match device signatures.
"""
import importlib
import logging
import os
from typing import Dict, List, Optional, Any, Mapping, Union

from cybex_pulse.fingerprinting.signaturematcher import SignatureMatcher

logger = logging.getLogger(__name__)

class MatchingWeights:
    """
    Standard weights used for different matching methods.
    These determine the relative importance of each matching method.
    """
    MAC_PREFIX = 25
    OPEN_PORTS = 15
    HTTP_SIGNATURE = 20
    CONTENT_NAS = 30
    CONTENT_STANDARD = 25
    PAGE_TITLE = 15
    SNMP_DATA = 15
    MDNS_DATA = 10
    HOSTNAME = 15


class FingerprintEngine:
    """Engine for device fingerprinting and identification."""
    
    def __init__(self):
        """Initialize the fingerprint engine."""
        self.signatures: Dict[str, Dict[str, Any]] = {}
        self.device_modules: Dict[str, Any] = {}
        self.matcher = SignatureMatcher()
        self._load_device_modules()
    
    def _load_device_modules(self) -> None:
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
            confidence = self._calculate_match_confidence(device_data, signature, signature_id)
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
    
    def _calculate_match_confidence(self, 
                                   device_data: Dict[str, Any], 
                                   signature: Dict[str, Any],
                                   signature_id: str) -> float:
        """
        Calculate confidence score for a signature match.
        
        Args:
            device_data: Device attributes from scan
            signature: Device signature to match against
            signature_id: ID of the signature being matched
        
        Returns:
            Confidence score (0.0-1.0) where 1.0 is highest confidence
        """
        total_weight = 0
        matched_weight = 0
        
        # Track each match score for potential debugging
        match_scores = {}
        
        # Check MAC OUI match
        if 'mac_prefix' in signature and 'mac_address' in device_data:
            total_weight += MatchingWeights.MAC_PREFIX
            mac_score = self.matcher.match_mac_prefix(
                device_data['mac_address'], 
                signature['mac_prefix']
            )
            matched_weight += MatchingWeights.MAC_PREFIX * mac_score
            match_scores['mac_prefix'] = mac_score
        
        # Check open ports
        if 'open_ports' in signature and 'open_ports' in device_data:
            if signature['open_ports']:  # Only count if signature has ports defined
                total_weight += MatchingWeights.OPEN_PORTS
                ports_score = self.matcher.match_open_ports(
                    device_data['open_ports'], 
                    signature['open_ports']
                )
                matched_weight += MatchingWeights.OPEN_PORTS * ports_score
                match_scores['open_ports'] = ports_score
        
        # Check HTTP signature
        if 'http_signature' in signature and 'http_headers' in device_data:
            total_weight += MatchingWeights.HTTP_SIGNATURE
            http_score = self.matcher.match_http_signature(
                device_data['http_headers'], 
                signature['http_signature']
            )
            matched_weight += MatchingWeights.HTTP_SIGNATURE * http_score
            match_scores['http_signature'] = http_score
                
        # Check for content markers in HTTP headers/content
        if 'http_headers' in device_data:
            manufacturer = signature.get('manufacturer', '')
            model = signature.get('model', '')
            content_indicators = signature.get('content_indicators', None)
            
            # Different weights based on device type
            if 'device_type' in signature and signature['device_type'] == 'NAS':
                content_weight = MatchingWeights.CONTENT_NAS
            elif content_indicators:
                content_weight = MatchingWeights.CONTENT_STANDARD
            else:
                content_weight = 0  # Skip this test for devices without content indicators
                
            if content_weight > 0:
                total_weight += content_weight
                content_score = self.matcher.match_content_indicators(
                    device_data['http_headers'],
                    manufacturer,
                    model,
                    signature_id,
                    content_indicators
                )
                matched_weight += content_weight * content_score
                match_scores['content'] = content_score
                        
                # Check page title separately - adds to matched weight but not total weight
                if 'X-Page-Title' in device_data.get('http_headers', {}):
                    title_score = 0
                    title = device_data['http_headers']['X-Page-Title'].lower()
                    if (manufacturer.lower() in title or 
                        model.lower() in title):
                        matched_weight += MatchingWeights.PAGE_TITLE
                        match_scores['page_title'] = 1.0
        
        # Check SNMP data
        if 'snmp_signature' in signature and 'snmp_data' in device_data:
            total_weight += MatchingWeights.SNMP_DATA
            snmp_score = self.matcher.match_snmp_data(
                device_data['snmp_data'], 
                signature['snmp_signature']
            )
            matched_weight += MatchingWeights.SNMP_DATA * snmp_score
            match_scores['snmp'] = snmp_score
        
        # Check mDNS data
        if 'mdns_signature' in signature and 'mdns_data' in device_data:
            total_weight += MatchingWeights.MDNS_DATA
            mdns_score = self.matcher.match_mdns_data(
                device_data['mdns_data'], 
                signature['mdns_signature']
            )
            matched_weight += MatchingWeights.MDNS_DATA * mdns_score
            match_scores['mdns'] = mdns_score
        
        # Check hostname patterns
        hostname = device_data.get('hostname', '')
        if 'hostname_patterns' in signature and hostname:
            total_weight += MatchingWeights.HOSTNAME
            hostname_score = self.matcher.match_hostname(
                hostname,
                signature['hostname_patterns']
            )
            matched_weight += MatchingWeights.HOSTNAME * hostname_score
            match_scores['hostname'] = hostname_score
        
        # Calculate confidence (prevent division by zero)
        if total_weight == 0:
            return 0.0
        
        # Log detailed match scores for debugging at trace level
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Match scores for {signature_id}: {match_scores}")
        
        return matched_weight / total_weight
    
    def get_available_modules(self) -> List[str]:
        """Get list of loaded device modules."""
        return list(self.device_modules.keys())
    
    def get_signature_count(self) -> int:
        """Get total count of loaded signatures."""
        return len(self.signatures)