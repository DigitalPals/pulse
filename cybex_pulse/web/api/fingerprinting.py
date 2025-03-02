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
        if not server.config.config.get("fingerprinting", {}).get("enabled", False):
            return server.jsonify({
                'error': 'Fingerprinting is not enabled',
                'modules': {},
                'total_signatures': 0
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
            
            return server.jsonify({
                'modules': module_stats,
                'total_signatures': total_signatures
            })
        except ImportError:
            return server.jsonify({
                'error': 'Fingerprinting module not available',
                'modules': {},
                'total_signatures': 0
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