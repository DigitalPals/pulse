"""
Fingerprinting engine for device identification.
Provides core functionality to match device signatures.
"""
import importlib
import logging
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, List, Optional, Any, Mapping, Union, Tuple

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
    
    def __init__(self, lazy_loading: bool = False):
        """
        Initialize the fingerprint engine.
        
        Args:
            lazy_loading: If True, signatures will be loaded on first use instead of at initialization
        """
        self.signatures: Dict[str, Dict[str, Any]] = {}
        self.device_modules: Dict[str, Any] = {}
        self.matcher = SignatureMatcher()
        self._modules_loaded = False
        self._loading_lock = threading.RLock()
        
        # Load modules immediately unless lazy loading is enabled
        if not lazy_loading:
            self._load_device_modules()
    
    def _load_device_modules(self) -> None:
        """Dynamically load all device modules from the devices directory."""
        # Use a lock to prevent multiple threads from loading modules simultaneously
        with self._loading_lock:
            # Check if modules are already loaded
            if self._modules_loaded:
                return
                
            devices_dir = os.path.join(os.path.dirname(__file__), 'devices')
            
            # Use a more efficient approach to load modules
            try:
                # Get all potential module files
                module_files = [
                    filename[:-3] for filename in os.listdir(devices_dir)
                    if filename.endswith('.py') and filename != '__init__.py'
                ]
                
                # Load modules in parallel using ThreadPoolExecutor
                with ThreadPoolExecutor(max_workers=min(10, len(module_files))) as executor:
                    # Create a list to store futures
                    futures = []
                    
                    # Submit tasks to load each module
                    for module_name in module_files:
                        futures.append(executor.submit(self._load_single_module, module_name))
                    
                    # Process results as they complete
                    for future in futures:
                        try:
                            result = future.result()
                            if result:
                                module_name, module = result
                                self.device_modules[module_name] = module
                                self.signatures.update(module.SIGNATURES)
                                logger.info(f"Loaded {len(module.SIGNATURES)} signatures from {module_name}")
                        except Exception as e:
                            logger.error(f"Error loading module: {e}")
                
                # Mark modules as loaded
                self._modules_loaded = True
                logger.info(f"Finished loading {len(self.signatures)} total signatures")
                
            except Exception as e:
                logger.error(f"Failed to load device modules: {e}")
    
    def _load_single_module(self, module_name: str) -> Optional[Tuple[str, Any]]:
        """
        Load a single device module.
        
        Args:
            module_name: Name of the module to load
            
        Returns:
            Tuple of (module_name, module) if successful, None otherwise
        """
        try:
            module = importlib.import_module(f'cybex_pulse.fingerprinting.devices.{module_name}')
            if hasattr(module, 'SIGNATURES'):
                return (module_name, module)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to load device module {module_name}: {e}")
        return None
    
    def identify_device(self, device_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Identify a device based on its attributes.
        
        Args:
            device_data: Dictionary containing device attributes like MAC, open ports,
                        HTTP headers, SNMP data, etc.
        
        Returns:
            List of potential device matches with confidence scores
        """
        # Ensure modules are loaded
        if not self._modules_loaded:
            self._load_device_modules()
            
        matches = []
        
        # Optimize by pre-filtering signatures based on available data
        filtered_signatures = self._prefilter_signatures(device_data)
        
        # Process filtered signatures
        for signature_id, signature in filtered_signatures.items():
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
        
    def _prefilter_signatures(self, device_data: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """
        Pre-filter signatures based on available device data to reduce processing.
        
        Args:
            device_data: Dictionary containing device attributes
            
        Returns:
            Dictionary of filtered signatures
        """
        # If we have very few signatures, don't bother filtering
        if len(self.signatures) < 20:
            return self.signatures
            
        filtered_signatures = {}
        
        # Check for MAC address match first (most efficient filter)
        if 'mac_address' in device_data:
            mac = device_data['mac_address'].upper().replace(':', '').replace('-', '')
            mac_oui = mac[:6]
            
            for sig_id, signature in self.signatures.items():
                # If signature has a MAC prefix that matches, include it
                if 'mac_prefix' in signature:
                    prefixes = signature['mac_prefix']
                    for prefix in prefixes:
                        formatted_prefix = prefix.upper().replace(':', '').replace('-', '')[:6]
                        if mac_oui == formatted_prefix:
                            filtered_signatures[sig_id] = signature
                            break
        
        # If we have open ports, filter by that as well
        if 'open_ports' in device_data and device_data['open_ports'] and len(filtered_signatures) < len(self.signatures) // 2:
            device_ports = set(device_data['open_ports'])
            
            # Add signatures that have matching ports
            for sig_id, signature in self.signatures.items():
                if sig_id in filtered_signatures:
                    continue  # Already included
                    
                if 'open_ports' in signature and signature['open_ports']:
                    sig_ports = set(signature['open_ports'])
                    if sig_ports.intersection(device_ports):
                        filtered_signatures[sig_id] = signature
        
        # If we still don't have enough signatures, include all
        if not filtered_signatures:
            return self.signatures
            
        return filtered_signatures
    
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
        
        # Early exit checks - if critical attributes are missing, return 0
        if 'mac_prefix' in signature and 'mac_address' in device_data:
            # Check MAC OUI match - this is a high-confidence match
            mac_score = self.matcher.match_mac_prefix(
                device_data['mac_address'],
                signature['mac_prefix']
            )
            
            if mac_score > 0:
                # If MAC matches, this is a strong indicator
                total_weight += MatchingWeights.MAC_PREFIX
                matched_weight += MatchingWeights.MAC_PREFIX * mac_score
                match_scores['mac_prefix'] = mac_score
            elif 'mac_required' in signature and signature['mac_required']:
                # If MAC is required but doesn't match, exit early
                return 0.0
        
        # Check open ports - only if we have both signature ports and device ports
        device_ports = device_data.get('open_ports', [])
        signature_ports = signature.get('open_ports', [])
        
        if signature_ports and device_ports:
            total_weight += MatchingWeights.OPEN_PORTS
            ports_score = self.matcher.match_open_ports(device_ports, signature_ports)
            matched_weight += MatchingWeights.OPEN_PORTS * ports_score
            match_scores['open_ports'] = ports_score
            
            # Early exit if no ports match and ports are required
            if ports_score == 0 and signature.get('ports_required', False):
                return 0.0
        
        # Check HTTP signature if available
        http_headers = device_data.get('http_headers', {})
        http_signature = signature.get('http_signature', {})
        
        if http_signature and http_headers:
            total_weight += MatchingWeights.HTTP_SIGNATURE
            http_score = self.matcher.match_http_signature(http_headers, http_signature)
            matched_weight += MatchingWeights.HTTP_SIGNATURE * http_score
            match_scores['http_signature'] = http_score
                
        # Check for content markers in HTTP headers/content
        if http_headers:
            manufacturer = signature.get('manufacturer', '')
            model = signature.get('model', '')
            content_indicators = signature.get('content_indicators', None)
            
            # Determine content weight based on device type
            content_weight = 0
            if 'device_type' in signature:
                if signature['device_type'] == 'NAS':
                    content_weight = MatchingWeights.CONTENT_NAS
                elif content_indicators:
                    content_weight = MatchingWeights.CONTENT_STANDARD
            
            # Only process content indicators if we have a weight
            if content_weight > 0:
                total_weight += content_weight
                content_score = self.matcher.match_content_indicators(
                    http_headers,
                    manufacturer,
                    model,
                    signature_id,
                    content_indicators
                )
                matched_weight += content_weight * content_score
                match_scores['content'] = content_score
                
                # Check page title separately - adds to matched weight but not total weight
                if 'X-Page-Title' in http_headers:
                    title = http_headers['X-Page-Title'].lower()
                    manufacturer_lower = manufacturer.lower()
                    model_lower = model.lower()
                    
                    if manufacturer_lower and manufacturer_lower in title:
                        matched_weight += MatchingWeights.PAGE_TITLE
                        match_scores['page_title'] = 1.0
                    elif model_lower and model_lower in title:
                        matched_weight += MatchingWeights.PAGE_TITLE
                        match_scores['page_title'] = 1.0
        
        # Check SNMP data if available
        snmp_data = device_data.get('snmp_data', {})
        snmp_signature = signature.get('snmp_signature', {})
        
        if snmp_signature and snmp_data:
            total_weight += MatchingWeights.SNMP_DATA
            snmp_score = self.matcher.match_snmp_data(snmp_data, snmp_signature)
            matched_weight += MatchingWeights.SNMP_DATA * snmp_score
            match_scores['snmp'] = snmp_score
        
        # Check mDNS data if available
        mdns_data = device_data.get('mdns_data', {})
        mdns_signature = signature.get('mdns_signature', {})
        
        if mdns_signature and mdns_data:
            total_weight += MatchingWeights.MDNS_DATA
            mdns_score = self.matcher.match_mdns_data(mdns_data, mdns_signature)
            matched_weight += MatchingWeights.MDNS_DATA * mdns_score
            match_scores['mdns'] = mdns_score
        
        # Check hostname patterns if available
        hostname = device_data.get('hostname', '')
        hostname_patterns = signature.get('hostname_patterns', [])
        
        if hostname_patterns and hostname:
            total_weight += MatchingWeights.HOSTNAME
            hostname_score = self.matcher.match_hostname(hostname, hostname_patterns)
            matched_weight += MatchingWeights.HOSTNAME * hostname_score
            match_scores['hostname'] = hostname_score
        
        # Calculate confidence (prevent division by zero)
        if total_weight == 0:
            return 0.0
        
        # Calculate final confidence score
        confidence = matched_weight / total_weight
        
        # Log detailed match scores for debugging at trace level
        if confidence > 0.3 and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Match scores for {signature_id}: {match_scores}, confidence: {confidence:.2f}")
        
        return confidence
    
    def get_available_modules(self) -> List[str]:
        """Get list of loaded device modules."""
        return list(self.device_modules.keys())
    
    def get_signature_count(self) -> int:
        """Get total count of loaded signatures."""
        return len(self.signatures)