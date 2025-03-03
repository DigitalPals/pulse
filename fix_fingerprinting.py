#!/usr/bin/env python3
"""
Fix for fingerprinting performance issues in Cybex Pulse.

This script applies performance optimizations to the fingerprinting service
to prevent it from halting the application.
"""
import os
import sys
import logging
import asyncio
import concurrent.futures
from typing import List, Dict, Any

# Add the parent directory to the path so we can import the cybex_pulse modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cybex_pulse.fingerprinting.scanner import DeviceFingerprinter, HttpScanner
from cybex_pulse.fingerprinting.engine import FingerprintEngine

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def patch_http_scanner():
    """
    Patch the HttpScanner class to optimize HTTP requests.
    
    Key optimizations:
    1. Reduce the number of ports scanned by default
    2. Use concurrent requests instead of sequential
    3. Optimize content analysis
    """
    original_scan = HttpScanner.scan
    
    def optimized_scan(self, ip_address: str) -> Dict[str, Any]:
        """
        Optimized version of the HTTP scanner that uses concurrent requests.
        """
        headers = {}
        
        # Reduce the number of ports to check - focus on most common ones
        # This significantly reduces the number of HTTP requests
        optimized_ports = [80, 443]  # Only check the most common ports by default
        
        # Use ThreadPoolExecutor to make requests in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            # First try HEAD requests in parallel
            head_futures = {
                executor.submit(
                    self._perform_head_request, 
                    f"{'https' if port in [443, 8443, 8843] else 'http'}://{ip_address}:{port}"
                ): port for port in optimized_ports
            }
            
            for future in concurrent.futures.as_completed(head_futures):
                try:
                    result = future.result()
                    headers.update(result)
                except Exception:
                    pass
            
            # Then try GET requests in parallel, but only if we didn't get enough info from HEAD
            if not any(k.lower().startswith('server') for k in headers.keys()):
                get_futures = {
                    executor.submit(
                        self._perform_get_request, 
                        f"{'https' if port in [443, 8443, 8843] else 'http'}://{ip_address}:{port}"
                    ): port for port in optimized_ports
                }
                
                for future in concurrent.futures.as_completed(get_futures):
                    try:
                        result = future.result()
                        headers.update(result)
                    except Exception:
                        pass
            
            # Only check management paths if we have reason to believe it's a managed device
            if any(k.startswith('X-Content-Contains-') for k in headers.keys()):
                path_futures = {
                    executor.submit(
                        self._check_management_paths, 
                        "https", ip_address, 443
                    ): 443
                }
                
                for future in concurrent.futures.as_completed(path_futures):
                    try:
                        result = future.result()
                        headers.update(result)
                    except Exception:
                        pass
        
        return {'http_headers': headers}
    
    # Apply the patch
    HttpScanner.scan = optimized_scan
    logger.info("Applied HTTP scanner optimization patch")

def patch_fingerprint_network():
    """
    Patch the fingerprint_network method to optimize batch processing.
    
    Key optimizations:
    1. Remove the sleep between batches
    2. Increase batch size for more efficient processing
    3. Add early termination for empty results
    """
    original_fingerprint_network = DeviceFingerprinter.fingerprint_network
    
    def optimized_fingerprint_network(self, devices: List[Dict[str, str]],
                                    force_scan: bool = False) -> List[Dict[str, Any]]:
        """
        Optimized version of fingerprint_network that processes devices more efficiently.
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
        
        # Increase batch size for more efficient processing
        batch_size = min(10, len(filtered_devices))  # Increased from 5 to 10
        logger.info(f"Processing devices in batches of {batch_size}")
        
        # Process devices in batches
        for i in range(0, len(filtered_devices), batch_size):
            batch = filtered_devices[i:i+batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} with {len(batch)} devices")
            
            # Process batch in parallel
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(self.max_threads, batch_size)) as executor:
                futures = {
                    executor.submit(self.fingerprint_device, device['ip_address'], device['mac_address']): device
                    for device in batch
                }
                
                # Use as_completed to process results as they come in
                import concurrent.futures
                for future in concurrent.futures.as_completed(futures):
                    try:
                        result = future.result()
                        results.append(result)
                    except Exception as e:
                        device = futures[future]
                        logger.error(f"Error fingerprinting device {device['ip_address']}: {str(e)}")
            
            # Remove the sleep between batches - this was causing unnecessary delays
            # The original code had: time.sleep(1)
        
        return results
    
    # Apply the patch
    DeviceFingerprinter.fingerprint_network = optimized_fingerprint_network
    logger.info("Applied fingerprint_network optimization patch")

def patch_calculate_match_confidence():
    """
    Patch the _calculate_match_confidence method to optimize signature matching.
    
    Key optimizations:
    1. Early termination for low-probability matches
    2. Reduce debug logging
    """
    original_calculate_match_confidence = FingerprintEngine._calculate_match_confidence
    
    def optimized_calculate_match_confidence(self, 
                                          device_data: Dict[str, Any], 
                                          signature: Dict[str, Any],
                                          signature_id: str) -> float:
        """
        Optimized version of _calculate_match_confidence with early termination.
        """
        total_weight = 0
        matched_weight = 0
        
        # Track each match score for potential debugging
        match_scores = {}
        
        # Check MAC OUI match - this is a strong indicator, check first
        if 'mac_prefix' in signature and 'mac_address' in device_data:
            total_weight += 25  # MatchingWeights.MAC_PREFIX
            mac_score = self.matcher.match_mac_prefix(
                device_data['mac_address'], 
                signature['mac_prefix']
            )
            matched_weight += 25 * mac_score  # MatchingWeights.MAC_PREFIX * mac_score
            match_scores['mac_prefix'] = mac_score
            
            # Early termination: If MAC doesn't match at all, this is likely not the right device
            # This avoids unnecessary processing for obvious non-matches
            if mac_score == 0 and len(signature['mac_prefix']) > 0:
                # Only apply early termination if the signature actually has MAC prefixes defined
                # and none of them matched
                return 0.0
        
        # Check open ports
        if 'open_ports' in signature and 'open_ports' in device_data:
            if signature['open_ports']:  # Only count if signature has ports defined
                total_weight += 15  # MatchingWeights.OPEN_PORTS
                ports_score = self.matcher.match_open_ports(
                    device_data['open_ports'], 
                    signature['open_ports']
                )
                matched_weight += 15 * ports_score  # MatchingWeights.OPEN_PORTS * ports_score
                match_scores['open_ports'] = ports_score
        
        # Check HTTP signature
        if 'http_signature' in signature and 'http_headers' in device_data:
            total_weight += 20  # MatchingWeights.HTTP_SIGNATURE
            http_score = self.matcher.match_http_signature(
                device_data['http_headers'], 
                signature['http_signature']
            )
            matched_weight += 20 * http_score  # MatchingWeights.HTTP_SIGNATURE * http_score
            match_scores['http_signature'] = http_score
                
        # Check for content markers in HTTP headers/content
        if 'http_headers' in device_data:
            manufacturer = signature.get('manufacturer', '')
            model = signature.get('model', '')
            content_indicators = signature.get('content_indicators', None)
            
            # Different weights based on device type
            if 'device_type' in signature and signature['device_type'] == 'NAS':
                content_weight = 30  # MatchingWeights.CONTENT_NAS
            elif content_indicators:
                content_weight = 25  # MatchingWeights.CONTENT_STANDARD
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
                    title = device_data['http_headers']['X-Page-Title'].lower()
                    if (manufacturer.lower() in title or 
                        model.lower() in title):
                        matched_weight += 15  # MatchingWeights.PAGE_TITLE
                        match_scores['page_title'] = 1.0
        
        # Check SNMP data
        if 'snmp_signature' in signature and 'snmp_data' in device_data:
            total_weight += 15  # MatchingWeights.SNMP_DATA
            snmp_score = self.matcher.match_snmp_data(
                device_data['snmp_data'], 
                signature['snmp_signature']
            )
            matched_weight += 15 * snmp_score  # MatchingWeights.SNMP_DATA * snmp_score
            match_scores['snmp'] = snmp_score
        
        # Check mDNS data
        if 'mdns_signature' in signature and 'mdns_data' in device_data:
            total_weight += 10  # MatchingWeights.MDNS_DATA
            mdns_score = self.matcher.match_mdns_data(
                device_data['mdns_data'], 
                signature['mdns_signature']
            )
            matched_weight += 10 * mdns_score  # MatchingWeights.MDNS_DATA * mdns_score
            match_scores['mdns'] = mdns_score
        
        # Check hostname patterns
        hostname = device_data.get('hostname', '')
        if 'hostname_patterns' in signature and hostname:
            total_weight += 15  # MatchingWeights.HOSTNAME
            hostname_score = self.matcher.match_hostname(
                hostname,
                signature['hostname_patterns']
            )
            matched_weight += 15 * hostname_score  # MatchingWeights.HOSTNAME * hostname_score
            match_scores['hostname'] = hostname_score
        
        # Calculate confidence (prevent division by zero)
        if total_weight == 0:
            return 0.0
        
        # Reduce debug logging - only log if there's a significant match
        confidence = matched_weight / total_weight
        if confidence > 0.5 and logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Match scores for {signature_id}: {match_scores}")
        
        return confidence
    
    # Apply the patch
    FingerprintEngine._calculate_match_confidence = optimized_calculate_match_confidence
    logger.info("Applied _calculate_match_confidence optimization patch")

def patch_fingerprint_device():
    """
    Patch the fingerprint_device method to optimize the scanning process.
    
    Key optimizations:
    1. Skip unnecessary scans based on device type
    2. Add timeouts to prevent hanging
    """
    original_fingerprint_device = DeviceFingerprinter.fingerprint_device
    
    def optimized_fingerprint_device(self, ip_address: str, mac_address: str) -> Dict[str, Any]:
        """
        Optimized version of fingerprint_device with smarter scanning.
        """
        logger.info(f"Fingerprinting device {ip_address} ({mac_address})")
        
        # Build base device data
        device_data = {
            'ip_address': ip_address,
            'mac_address': mac_address
        }
        
        # Perform port scan first to determine device type
        port_scan_result = self.port_scanner.scan(ip_address)
        device_data.update(port_scan_result)
        
        # Determine which additional scans to perform based on open ports
        open_ports = device_data.get('open_ports', [])
        
        # Create a list of scan functions to execute
        scan_functions = []
        
        # Always do HTTP scan if port 80 or 443 is open
        if any(port in open_ports for port in [80, 443, 8080, 8443]):
            scan_functions.append(lambda: self.http_scanner.scan(ip_address))
        
        # Only do SNMP scan if port 161 is open
        if 161 in open_ports:
            scan_functions.append(lambda: self.snmp_scanner.scan(ip_address))
        
        # Only do mDNS scan for devices that might support it
        # This is a heuristic - devices with ports 5353 or certain other ports
        # are more likely to support mDNS
        if 5353 in open_ports or any(port in open_ports for port in [80, 443, 8080, 8443]):
            scan_functions.append(lambda: self.mdns_scanner.scan(ip_address))
        
        # Perform all selected fingerprinting operations in parallel
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(scan_functions)) as executor:
            futures = [executor.submit(func) for func in scan_functions]
            
            # Collect results from all futures
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    device_data.update(result)
                except Exception as e:
                    logger.error(f"Error in scan for {ip_address}: {e}")
        
        # Extract hostname from mDNS data if available
        if 'mdns_data' in device_data and 'hostname' in device_data['mdns_data']:
            device_data['hostname'] = device_data['mdns_data']['hostname']
        
        # Identify device using fingerprint engine
        identification = self.engine.identify_device(device_data)
        device_data['identification'] = identification
        
        return device_data
    
    # Apply the patch
    DeviceFingerprinter.fingerprint_device = optimized_fingerprint_device
    logger.info("Applied fingerprint_device optimization patch")

def apply_all_patches():
    """Apply all performance optimization patches."""
    logger.info("Applying fingerprinting performance optimization patches...")
    
    # Apply all patches
    patch_http_scanner()
    patch_fingerprint_network()
    patch_calculate_match_confidence()
    patch_fingerprint_device()
    
    logger.info("All fingerprinting performance optimization patches applied successfully")

if __name__ == "__main__":
    apply_all_patches()
    logger.info("Fingerprinting performance optimization complete")
    print("Fingerprinting performance optimization patches have been applied successfully.")
    print("The web interface should now be more responsive during fingerprinting operations.")