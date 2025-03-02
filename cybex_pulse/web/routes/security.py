"""
Security routes for the web interface.
"""
import json
import time


def register_security_routes(app, server):
    """Register security routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Network Security route
    @app.route('/network-security')
    @server.login_required
    def network_security():
        # Redirect to dashboard if security scanning is not enabled
        if not server.config.config.get("monitoring", {}).get("security", {}).get("enabled", False):
            server.flash('Network security scanning is not enabled')
            return server.redirect(server.url_for('dashboard'))
            
        devices = server.db_manager.get_all_devices()
        now = int(time.time())
        
        # Count security vulnerabilities
        security_vulnerabilities = 0
        vulnerable_devices = []
        last_scan = None
        
        for device in devices:
            device_id = device.get('id')
            if device_id:
                security_scans = server.db_manager.get_security_scans(device_id, limit=1)
                if security_scans:
                    scan = security_scans[0]
                    
                    # Track the most recent scan time
                    if not last_scan or scan.get('timestamp', 0) > last_scan.get('timestamp', 0):
                        last_scan = scan
                        
                    if scan.get('vulnerabilities'):
                        try:
                            vulnerabilities = json.loads(scan['vulnerabilities'])
                            if vulnerabilities:
                                security_vulnerabilities += len(vulnerabilities)
                                
                                # Add this device to vulnerable devices list
                                device_with_vulns = device.copy()
                                device_with_vulns['vulnerabilities'] = scan['vulnerabilities']
                                device_with_vulns['last_scan'] = scan.get('timestamp')
                                vulnerable_devices.append(device_with_vulns)
                        except (json.JSONDecodeError, TypeError):
                            pass
        
        return server.render_template('network_security.html',
                                  security_vulnerabilities=security_vulnerabilities,
                                  vulnerable_devices=vulnerable_devices,
                                  last_scan=last_scan,
                                  now=now)
                                  
    # Fingerprinting information route
    @app.route('/fingerprinting')
    @server.login_required
    def fingerprinting():
        # Redirect to dashboard if fingerprinting is not enabled
        if not server.config.config.get("fingerprinting", {}).get("enabled", False):
            server.flash('Device fingerprinting is not enabled')
            return server.redirect(server.url_for('dashboard'))
            
        return server.render_template('fingerprinting.html',
                                  config=server.config)