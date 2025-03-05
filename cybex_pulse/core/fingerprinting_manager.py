"""
Fingerprinting manager module for Cybex Pulse.

This module provides centralized device fingerprinting functionality:
- Managing device fingerprinting operations
- Tracking fingerprinting status
- Processing fingerprinting results
- Integrating with the fingerprinting engine
"""
import logging
import time
from typing import Dict, List, Optional, Any

from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config


class FingerprintingManager:
    """Centralized manager for device fingerprinting operations.
    
    This class provides a unified interface for:
    - Initializing and managing the fingerprinting engine
    - Determining which devices need fingerprinting
    - Processing fingerprinting results
    - Tracking fingerprinting status
    """
    
    def __init__(self, config: Config, db_manager: DatabaseManager, logger: logging.Logger):
        """Initialize the fingerprinting manager.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logger
        
        # Initialize fingerprinter if enabled
        self.fingerprinter = None
        self._initialize_fingerprinter()
    
    def _initialize_fingerprinter(self) -> None:
        """Initialize the fingerprinting engine if enabled."""
        fingerprinting_enabled = self.config.get("fingerprinting", "enabled", False)
        
        if fingerprinting_enabled:
            try:
                from cybex_pulse.fingerprinting.scanner import DeviceFingerprinter
                
                # Get configuration values with proper defaults
                max_threads = int(self.config.get("fingerprinting", "max_threads", 10))
                timeout = int(self.config.get("fingerprinting", "timeout", 2))
                scan_interval = int(self.config.get("fingerprinting", "scan_interval", 86400))
                
                # Initialize fingerprinter
                self.logger.info(f"Creating DeviceFingerprinter with max_threads={max_threads}, timeout={timeout}, scan_interval={scan_interval}")
                self.fingerprinter = DeviceFingerprinter(
                    max_threads=max_threads,
                    timeout=timeout,
                    db_manager=self.db_manager,
                    config=self.config
                )
            except Exception as e:
                self.logger.error(f"Failed to initialize device fingerprinter: {e}")
                self.fingerprinter = None
    
    def update_fingerprinting_state(self) -> None:
        """Update the fingerprinting state based on current configuration."""
        fingerprinting_enabled = self.config.get("fingerprinting", "enabled", False)
        
        # Check if fingerprinting configuration has changed
        if self.fingerprinter is None and fingerprinting_enabled:
            self.logger.info("Fingerprinting enabled, initializing fingerprinter")
            self._initialize_fingerprinter()
        elif self.fingerprinter is not None and not fingerprinting_enabled:
            self.logger.info("Fingerprinting disabled, removing fingerprinter")
            self.fingerprinter = None
    
    def is_enabled(self) -> bool:
        """Check if fingerprinting is enabled.
        
        Returns:
            bool: True if fingerprinting is enabled and available, False otherwise
        """
        return (
            self.config.get("fingerprinting", "enabled", False) and
            self.fingerprinter is not None
        )
        
    def shutdown(self) -> None:
        """Shutdown the fingerprinting manager and release resources.
        
        This method should be called during application shutdown to ensure
        all resources are properly released, especially HTTP connections.
        """
        self.logger.info("Shutting down fingerprinting manager")
        
        if self.fingerprinter:
            try:
                # Call the fingerprinter's shutdown method to clean up resources
                self.fingerprinter.shutdown()
                self.fingerprinter = None
            except Exception as e:
                self.logger.error(f"Error shutting down fingerprinter: {e}")
                
        self.logger.info("Fingerprinting manager shutdown complete")
    
    def should_fingerprint_device(self, device: Dict[str, Any], force_scan: bool = False) -> bool:
        """Check if a device should be fingerprinted.
        
        Args:
            device: Device dictionary
            force_scan: If True, scan device even if it's been scanned before
            
        Returns:
            bool: True if device should be fingerprinted, False otherwise
        """
        if not self.is_enabled():
            return False
            
        mac_address = device.get("mac_address")
        if not mac_address:
            self.logger.debug(f"Device has no MAC address, skipping fingerprinting")
            return False
            
        # Get device from database
        db_device = self.db_manager.get_device(mac_address)
        if not db_device:
            self.logger.debug(f"Device {mac_address} not found in database, skipping fingerprinting")
            return False
            
        # Check if device is marked as never fingerprint
        if db_device.get("never_fingerprint"):
            self.logger.debug(f"Device {mac_address} marked as never fingerprint, skipping")
            return False
            
        # For forced scans, we include the device without additional checks
        # This allows manual re-fingerprinting from the device details page
        if force_scan:
            self.logger.debug(f"Force scan enabled for device {mac_address}, will fingerprint")
            return True
            
        # Check if device is already marked as fingerprinted
        # This is the primary check that prevents automatic re-fingerprinting
        if db_device.get("is_fingerprinted"):
            # Check if enough time has passed since the last fingerprinting
            fingerprint_date = db_device.get("fingerprint_date", 0)
            current_time = int(time.time())
            scan_interval = int(self.config.get("fingerprinting", "scan_interval", 86400))
            
            # If the scan interval has passed, allow re-fingerprinting
            if current_time - fingerprint_date > scan_interval:
                self.logger.debug(f"Device {mac_address} scan interval ({scan_interval}s) has passed, will re-fingerprint")
                return True
                
            self.logger.debug(f"Device {mac_address} is already marked as fingerprinted and scan interval has not passed, skipping automatic fingerprinting")
            return False
            
        # If not explicitly marked as fingerprinted, check if it meets the criteria
        # This is a fallback for devices that were fingerprinted before the is_fingerprinted flag was added
        existing_type = db_device.get("device_type", "")
        fingerprint_date = db_device.get("fingerprint_date", 0)
        fingerprint_confidence = db_device.get("fingerprint_confidence", 0)
        
        # Consider a device already fingerprinted only if it has:
        # 1. A non-empty device type that isn't "unknown" or "unidentified"
        # 2. AND a valid fingerprint date with high confidence
        unknown_types = ["", "unknown", "unidentified", None]
        has_valid_type = existing_type not in unknown_types
        has_valid_date = fingerprint_date is not None and fingerprint_date > 0
        
        # Use the same threshold as from config to determine if a device is well-fingerprinted
        threshold = float(self.config.get("fingerprinting", "confidence_threshold", 0.5))
        has_high_confidence = fingerprint_confidence is not None and fingerprint_confidence >= threshold
        
        # Only consider a device fully fingerprinted if it has both valid type, date, and high confidence
        already_fingerprinted = has_valid_type and has_valid_date and has_high_confidence
        
        # If the device meets the fingerprinting criteria but isn't explicitly marked,
        # update the database to set the is_fingerprinted flag
        if already_fingerprinted and not db_device.get("is_fingerprinted"):
            self.logger.debug(f"Device {mac_address} meets fingerprinting criteria but is not explicitly marked. Setting is_fingerprinted flag.")
            self.db_manager.update_device_metadata(mac_address, {'is_fingerprinted': True})
        
        if already_fingerprinted:
            self.logger.debug(
                f"Device {mac_address} already fingerprinted: type={existing_type}, "
                f"confidence={fingerprint_confidence}, date={fingerprint_date}, skipping"
            )
            return False
        else:
            self.logger.debug(
                f"Device {mac_address} needs fingerprinting: type={existing_type}, "
                f"confidence={fingerprint_confidence}, date={fingerprint_date}"
            )
            return True
    
    def fingerprint_devices(self, devices: List[Dict[str, Any]], force_scan: bool = False) -> None:
        """Perform fingerprinting on a list of devices.
        
        Args:
            devices: List of devices to fingerprint
            force_scan: If True, scan devices even if they've been scanned before
        """
        if not self.is_enabled() or not devices:
            return
            
        # Filter devices that need fingerprinting
        devices_to_fingerprint = []
        for device in devices:
            mac_address = device.get('mac_address', '')
            ip_address = device.get('ip_address', '')
            
            if force_scan:
                self.logger.debug(f"Force scan enabled, fingerprinting device: {mac_address} ({ip_address})")
                devices_to_fingerprint.append(device)
            elif self.should_fingerprint_device(device, force_scan):
                self.logger.debug(f"Device needs fingerprinting: {mac_address} ({ip_address})")
                devices_to_fingerprint.append(device)
            else:
                self.logger.debug(f"Skipping already fingerprinted device: {mac_address} ({ip_address})")
        
        if not devices_to_fingerprint:
            self.logger.info("No devices to fingerprint after validation")
            return
            
        self.logger.info(f"Starting device fingerprinting for {len(devices_to_fingerprint)} devices" +
                         (" (forced)" if force_scan else ""))
        start_time = time.time()
        
        try:
            # Run fingerprinting
            results = self.fingerprinter.fingerprint_network(devices_to_fingerprint, force_scan=force_scan)
            
            # Process fingerprinting results
            for result in results:
                self._process_fingerprinting_result(result, force_scan)
            
            elapsed_time = time.time() - start_time
            self.logger.info(f"Fingerprinting completed for {len(results)} devices in {elapsed_time:.2f} seconds")
        
        except Exception as e:
            self.logger.error(f"Error performing device fingerprinting: {e}")
    
    def _process_fingerprinting_result(self, result: Dict[str, Any], force_scan: bool) -> None:
        """Process a single fingerprinting result.
        
        Args:
            result: Fingerprinting result dictionary
            force_scan: Whether this was a forced scan
        """
        mac_address = result['mac_address']
        ip_address = result['ip_address']
        
        # Check if device is already fingerprinted (unless force_scan is True)
        if not force_scan:
            db_device = self.db_manager.get_device(mac_address)
            if db_device:
                # Check if device is already properly fingerprinted
                existing_type = db_device.get("device_type", "")
                fingerprint_date = db_device.get("fingerprint_date", 0)
                fingerprint_confidence = db_device.get("fingerprint_confidence", 0)
                
                unknown_types = ["", "unknown", "unidentified", None]
                has_valid_type = existing_type not in unknown_types
                has_valid_date = fingerprint_date is not None and fingerprint_date > 0
                
                threshold = float(self.config.get("fingerprinting", "confidence_threshold", 0.5))
                has_high_confidence = fingerprint_confidence is not None and fingerprint_confidence >= threshold
                
                already_fingerprinted = has_valid_type and has_valid_date and has_high_confidence
                
                if already_fingerprinted:
                    self.logger.debug(
                        f"Device {mac_address} already fingerprinted in database: type={existing_type}, "
                        f"confidence={fingerprint_confidence}, date={fingerprint_date}, skipping update"
                    )
                    return
        
        # Extract best match if available
        identification = result.get('identification', [])
        if not identification:
            self.logger.info(f"Device {mac_address} fingerprinted but not identified - will retry later")
            return
            
        best_match = identification[0]
        confidence = best_match.get('confidence', 0)
        
        # Only update if confidence is above threshold
        threshold = float(self.config.get("fingerprinting", "confidence_threshold", 0.5))
        if confidence < threshold:
            self.logger.info(f"Device {mac_address} fingerprinted but confidence too low: {confidence:.2f} < {threshold}")
            return
            
        device_type = best_match.get('device_type', '')
        manufacturer = best_match.get('manufacturer', '')
        model = best_match.get('model', '')
        
        # Prepare the device info
        device_info = {
            'device_type': device_type,
            'device_model': model,
            'device_manufacturer': manufacturer,
            'fingerprint_confidence': confidence,
            'fingerprint_date': int(time.time()),
            'is_fingerprinted': True  # Mark the device as fingerprinted to prevent automatic re-fingerprinting
        }
        
        # Update device in database
        self.logger.debug(f"Updating device {mac_address} with fingerprinting data: {device_info}")
        self.db_manager.update_device_metadata(mac_address, device_info)
        
        # Get current device info from database
        device_info_from_db = self.db_manager.get_device(mac_address)
        
        # Log fingerprinting result
        hostname = device_info_from_db.get('hostname', '') if device_info_from_db else ''
        device_name = f"{manufacturer} {model}" if manufacturer and model else (hostname or mac_address)
        
        # Log event for fingerprinting
        event_type = self.db_manager.EVENT_DEVICE_FINGERPRINTED
        event_message = f"Device identified: {device_name} ({ip_address})"
        
        self.logger.info(
            f"Device identified from nmap vendor: {device_name} ({ip_address}) "
            f"as {device_type} with {confidence:.2f} confidence"
        )
        
        # Log event
        import json
        self.db_manager.log_event(
            event_type,
            "info",
            event_message,
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