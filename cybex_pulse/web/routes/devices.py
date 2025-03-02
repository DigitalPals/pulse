"""
Device routes for the web interface.
"""
import json
import time


def register_device_routes(app, server):
    """Register device routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Devices route
    @app.route('/devices')
    @server.login_required
    def devices():
        page = int(server.request.args.get('page', 1))
        page_size = 50
        all_devices = server.db_manager.get_all_devices()
        
        # Calculate total pages and ensure current page is valid
        total_devices = len(all_devices)
        total_pages = (total_devices + page_size - 1) // page_size  # Ceiling division
        page = max(1, min(page, total_pages if total_pages > 0 else 1))
        
        # Paginate devices
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_devices = all_devices[start_idx:end_idx]
        
        # Add current timestamp for template
        now = int(time.time())
        return server.render_template('devices.html', 
                                   devices=paginated_devices, 
                                   now=now, 
                                   db_manager=server.db_manager,
                                   current_page=page,
                                   total_pages=total_pages,
                                   total_devices=total_devices)
    
    # Device details route
    @app.route('/devices/<mac_address>')
    @server.login_required
    def device_details(mac_address):
        device = server.db_manager.get_device(mac_address)
        if not device:
            server.flash('Device not found')
            return server.redirect(server.url_for('devices'))
        
        # Get security scans for this device
        security_scans = server.db_manager.get_security_scans(device['id'], limit=10)
        
        # Add current timestamp for template
        now = int(time.time())
        
        # Check if fingerprinting is enabled (for UI purposes)
        fingerprinting_enabled = server.config.config.get("fingerprinting", {}).get("enabled", False)
        
        return server.render_template('device_details.html', device=device, security_scans=security_scans, 
                                  now=now, fingerprinting_enabled=fingerprinting_enabled)
                                  
    # Fingerprint device route
    @app.route('/devices/<mac_address>/fingerprint', methods=['POST'])
    @server.login_required
    def fingerprint_device(mac_address):
        # Get device details
        device = server.db_manager.get_device(mac_address)
        if not device:
            server.flash('Device not found')
            return server.redirect(server.url_for('devices'))
            
        # Check if fingerprinting is enabled
        if not server.config.config.get("fingerprinting", {}).get("enabled", False):
            server.flash('Device fingerprinting is not enabled')
            return server.redirect(server.url_for('device_details', mac_address=mac_address))
            
        # Check if device is marked as never fingerprint
        if device.get('never_fingerprint'):
            server.flash('This device is set to never be fingerprinted')
            return server.redirect(server.url_for('device_details', mac_address=mac_address))
            
        # Check if main app reference exists
        if not server.main_app or not server.main_app.network_scanner or not server.main_app.network_scanner.fingerprinter:
            server.flash('Fingerprinting engine is not available')
            return server.redirect(server.url_for('device_details', mac_address=mac_address))
            
        try:
            # Run fingerprinting on the device
            device_to_fingerprint = {
                "ip_address": device["ip_address"],
                "mac_address": device["mac_address"]
            }
            
            # First, clear the previous fingerprinting data
            device_info = {
                'device_type': '',
                'device_model': '',
                'device_manufacturer': '',
                'fingerprint_confidence': 0.0,
                'fingerprint_date': 0
            }
            server.db_manager.update_device_metadata(device['mac_address'], device_info)
            server.logger.info(f"Cleared previous fingerprinting data for {device['mac_address']}")
            
            # Clear the in-memory fingerprinting cache as well
            if hasattr(server.main_app.network_scanner.fingerprinter, 'fingerprinted_mac_addresses'):
                if device['mac_address'] in server.main_app.network_scanner.fingerprinter.fingerprinted_mac_addresses:
                    server.main_app.network_scanner.fingerprinter.fingerprinted_mac_addresses.remove(device['mac_address'])
                    server.logger.info(f"Removed {device['mac_address']} from in-memory fingerprinting cache")
                
            # Perform fingerprinting - explicitly marking this as a manual operation
            # that should override any previous fingerprinting data and force a scan
            server.logger.info(f"Running manual fingerprinting for device: {device['mac_address']} ({device['ip_address']})")
            server.logger.info(f"This is a user-requested manual fingerprint operation (forced)")
            results = server.main_app.network_scanner.fingerprinter.fingerprint_network([device_to_fingerprint], force_scan=True)
            
            if results and len(results) > 0:
                result = results[0]
                
                # Process fingerprinting result
                identification = result.get('identification', [])
                if identification:
                    best_match = identification[0]
                    confidence = best_match.get('confidence', 0)
                    
                    # Prepare the device info
                    device_info = {
                        'device_type': best_match.get('device_type', ''),
                        'device_model': best_match.get('model', ''),
                        'device_manufacturer': best_match.get('manufacturer', ''),
                        'fingerprint_confidence': confidence,
                        'fingerprint_date': int(time.time())
                    }
                    
                    # Update device in database
                    server.db_manager.update_device_metadata(device['mac_address'], device_info)
                    
                    # Log fingerprinting result
                    hostname = device.get('hostname', '')
                    device_name = f"{device_info['device_manufacturer']} {device_info['device_model']}" if device_info['device_manufacturer'] and device_info['device_model'] else (hostname or device['mac_address'])
                    server.db_manager.log_event(
                        server.db_manager.EVENT_DEVICE_FINGERPRINTED,
                        "info",
                        f"Device manually fingerprinted: {device_name} ({device['ip_address']})",
                        json.dumps({
                            'mac': device['mac_address'], 
                            'ip': device['ip_address'], 
                            'hostname': hostname,
                            'manufacturer': device_info['device_manufacturer'],
                            'model': device_info['device_model'],
                            'device_type': device_info['device_type'],
                            'confidence': confidence
                        })
                    )
                    
                    server.flash(f"Device successfully fingerprinted as {device_info['device_manufacturer']} {device_info['device_model']} with {confidence*100:.0f}% confidence")
                else:
                    server.flash("Fingerprinting completed but no matches were found")
            else:
                server.flash("Fingerprinting failed - no results returned")
        except Exception as e:
            server.logger.error(f"Error fingerprinting device: {e}")
            server.flash(f"Error fingerprinting device: {str(e)}")
            
        return server.redirect(server.url_for('device_details', mac_address=mac_address))
    
    # Mark device as important route
    @app.route('/devices/<mac_address>/important', methods=['POST'])
    @server.login_required
    def mark_device_important(mac_address):
        important = server.request.form.get('important') == 'true'
        server.db_manager.mark_device_important(mac_address, important)
        return server.redirect(server.url_for('device_details', mac_address=mac_address))
        
    # Edit device route
    @app.route('/devices/<mac_address>/edit', methods=['GET', 'POST'])
    @server.login_required
    def edit_device(mac_address):
        device = server.db_manager.get_device(mac_address)
        if not device:
            server.flash('Device not found')
            return server.redirect(server.url_for('devices'))
            
        if server.request.method == 'POST':
            # Get form data
            hostname = server.request.form.get('hostname', '')
            vendor = server.request.form.get('vendor', '')
            notes = server.request.form.get('notes', '')
            
            # Handle never_fingerprint checkbox
            never_fingerprint = 'never_fingerprint' in server.request.form
            
            # Handle clear fingerprint checkbox
            clear_fingerprint = 'clear_fingerprint' in server.request.form
            if clear_fingerprint:
                server.db_manager.clear_device_fingerprint(mac_address)
                server.logger.info(f"Cleared fingerprint data for device: {mac_address}")
                server.db_manager.log_event(
                    server.db_manager.EVENT_SYSTEM,
                    "info",
                    f"Fingerprint data cleared for device: {hostname or mac_address}"
                )
            
            # Update device
            server.db_manager.update_device(
                mac_address=mac_address,
                hostname=hostname,
                vendor=vendor,
                notes=notes,
                never_fingerprint=never_fingerprint
            )
            
            server.logger.info(f"Updated device: {mac_address}")
            server.db_manager.log_event(
                "user",  # Using a custom "user" event type instead of EVENT_SYSTEM
                "info",
                f"Device details updated: {hostname or mac_address}"
            )
            
            server.flash('Device updated successfully')
            return server.redirect(server.url_for('device_details', mac_address=mac_address))
            
        # Current timestamp for template
        now = int(time.time())
        
        # Check if fingerprinting is enabled (for UI purposes)
        fingerprinting_enabled = server.config.config.get("fingerprinting", {}).get("enabled", False)
        
        return server.render_template('edit_device.html', 
                                  device=device, 
                                  now=now, 
                                  fingerprinting_enabled=fingerprinting_enabled)