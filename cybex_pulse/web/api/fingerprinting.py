"""
API routes for fingerprinting data.
"""


def register_fingerprinting_routes(app, server):
    """Register fingerprinting API routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Get fingerprinting modules and signature counts
    @app.route('/api/fingerprinting/modules')
    @server.login_required
    def api_fingerprinting_modules():
        # Return empty data if fingerprinting is not enabled
        if not server.config.get("fingerprinting", "enabled", False):
            return server.jsonify({
                'error': 'Fingerprinting is not enabled',
                'modules': {},
                'total_signatures': 0,
                'fingerprinted_devices': 0,
                'total_devices': 0
            })
            
        try:
            from cybex_pulse.fingerprinting.engine import FingerprintEngine
            engine = FingerprintEngine()
            
            modules = engine.get_available_modules()
            module_stats = {}
            
            for module in modules:
                if module in engine.device_modules:
                    module_obj = engine.device_modules[module]
                    if hasattr(module_obj, 'SIGNATURES'):
                        signature_count = len(module_obj.SIGNATURES)
                        module_stats[module] = {
                            'name': module.capitalize(),
                            'signatures': signature_count,
                            'device_types': get_unique_device_types(module_obj.SIGNATURES)
                        }
            
            total_signatures = engine.get_signature_count()
            
            # Get fingerprinting progress (identified devices vs total devices)
            all_devices = server.db_manager.get_all_devices()
            total_devices = len(all_devices)
            
            # Count devices that have been successfully fingerprinted
            # A device is considered fingerprinted if it has:
            # 1. A non-empty device type that isn't "unknown" or "unidentified"
            # 2. A valid fingerprint date
            # 3. A confidence score above the threshold
            threshold = float(server.config.get("fingerprinting", "confidence_threshold", 0.5))
            unknown_types = ["", "unknown", "unidentified", None]
            
            fingerprinted_devices = 0
            for device in all_devices:
                device_type = device.get("device_type", "")
                fingerprint_date = device.get("fingerprint_date", 0)
                fingerprint_confidence = device.get("fingerprint_confidence", 0)
                
                has_valid_type = device_type not in unknown_types
                has_valid_date = fingerprint_date is not None and fingerprint_date > 0
                has_high_confidence = fingerprint_confidence is not None and fingerprint_confidence >= threshold
                
                if has_valid_type and has_valid_date and has_high_confidence:
                    fingerprinted_devices += 1
            
            return server.jsonify({
                'modules': module_stats,
                'total_signatures': total_signatures,
                'fingerprinted_devices': fingerprinted_devices,
                'total_devices': total_devices
            })
        except ImportError:
            return server.jsonify({
                'error': 'Fingerprinting module not available',
                'modules': {},
                'total_signatures': 0,
                'fingerprinted_devices': 0,
                'total_devices': 0
            })


def get_unique_device_types(signatures):
    """Get unique device types from signatures dictionary.
    
    Args:
        signatures: Dictionary of signatures
        
    Returns:
        list: Unique device types
    """
    device_types = set()
    for sig_id, signature in signatures.items():
        if 'device_type' in signature:
            device_types.add(signature['device_type'])
    return list(device_types)