"""
API routes for device data.
"""
import json

from cybex_pulse.utils.mac_utils import normalize_mac


def register_device_routes(app, server):
    """Register device API routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Get all devices
    @app.route('/api/devices')
    @server.login_required
    def api_devices():
        page = int(server.request.args.get('page', 1))
        page_size = 50
        all_devices = server.db_manager.get_all_devices()
        
        # Deduplicate devices by MAC address
        # This ensures we don't have duplicate entries for the same device
        # In case of duplicates, keep the most recently seen device
        unique_devices = {}
        for device in all_devices:
            mac_address = device.get('mac_address')
            if mac_address:
                # Normalize MAC address to lowercase for consistent comparison
                normalized_mac = normalize_mac(mac_address)
                
                # If this MAC address is already in our unique devices dict,
                # only replace it if the current device was seen more recently
                if normalized_mac not in unique_devices or device.get('last_seen', 0) > unique_devices[normalized_mac].get('last_seen', 0):
                    unique_devices[normalized_mac] = device
        
        # Convert back to a list and sort by last_seen (descending)
        deduplicated_devices = list(unique_devices.values())
        deduplicated_devices.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
        
        # Calculate total pages
        total_devices = len(deduplicated_devices)
        total_pages = (total_devices + page_size - 1) // page_size
        
        # Paginate devices if page parameter is provided
        if 'page' in server.request.args:
            start_idx = (page - 1) * page_size
            end_idx = start_idx + page_size
            paginated_devices = deduplicated_devices[start_idx:end_idx]
            return server.jsonify({
                'devices': paginated_devices,
                'total_pages': total_pages,
                'current_page': page,
                'total_devices': total_devices
            })
        else:
            # For backward compatibility, return all devices if no page specified
            return server.jsonify(deduplicated_devices)
        
    # Get device ports
    @app.route('/api/devices/<int:device_id>/ports')
    @server.login_required
    def api_device_ports(device_id):
        # Return empty array if security scanning is not enabled
        if not server.config.config.get("monitoring", {}).get("security", {}).get("enabled", False):
            return server.jsonify({"ports": []})
            
        security_scans = server.db_manager.get_security_scans(device_id, limit=1)
        
        ports = []
        if security_scans and security_scans[0].get('open_ports'):
            try:
                ports = json.loads(security_scans[0]['open_ports'])
            except (json.JSONDecodeError, TypeError):
                ports = []
            
        return server.jsonify({"ports": ports})
    
    # Get device icon
    @app.route('/api/device-icon')
    @server.login_required
    def api_device_icon():
        vendor = server.request.args.get('vendor', '')
        device_name = server.request.args.get('device_name', '')
        
        from cybex_pulse.utils.icon_mapper import IconMapper
        icon_mapper = IconMapper()
        icon_html = icon_mapper.get_icon_html(vendor, device_name)
        
        return icon_html