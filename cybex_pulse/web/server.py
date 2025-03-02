"""
Web server module for Cybex Pulse.
"""
import hashlib
import json
import logging
import os
import time
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from cybex_pulse import __version__
from cybex_pulse.database.db_manager import DatabaseManager
from cybex_pulse.utils.config import Config
from cybex_pulse.utils.system_check import check_required_tools, get_installation_instructions

class WebServer:
    """Web server for Cybex Pulse application."""
    
    def __init__(self, config: Config, db_manager: DatabaseManager, logger: logging.Logger, main_app=None):
        """Initialize the web server.
        
        Args:
            config: Configuration manager
            db_manager: Database manager
            logger: Logger instance
            main_app: The main CybexPulseApp instance for callbacks
        """
        self.config = config
        self.db_manager = db_manager
        self.logger = logger
        self.main_app = main_app  # Reference to main application for callbacks
        self.server = None  # Will hold the Flask server instance
        
        # Check required tools
        self.tool_status = check_required_tools()
        self.logger.info(f"Required tools status: {self.tool_status}")
        
        # Import Flask here to avoid dependency if web interface is disabled
        try:
            from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
            import werkzeug.serving
            self.flask = Flask
            self.jsonify = jsonify
            self.render_template = render_template
            self.request = request
            self.redirect = redirect
            self.url_for = url_for
            self.session = session
            self.flash = flash
            self.werkzeug = werkzeug
        except ImportError:
            self.logger.error("Flask not installed. Web interface disabled.")
            return
        
        # Initialize Flask app
        self.app = self.flask(__name__)
        self.app.secret_key = os.urandom(24)
        
        # Register custom filters
        self._register_filters()
        
        # Register routes
        self._register_routes()
    
    def start(self) -> None:
        """Start the web server."""
        if not hasattr(self, 'app'):
            self.logger.error("Flask not installed. Web interface not started.")
            return
        
        host = self.config.get("web_interface", "host")
        port = self.config.get("web_interface", "port")
        
        # Display appropriate message based on host binding
        if host == "0.0.0.0":
            import socket
            try:
                # Try to get the actual IP address of this machine for display purposes
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                actual_ip = s.getsockname()[0]
                s.close()
                self.logger.info(f"Starting web server on all interfaces - access at http://{actual_ip}:{port}")
            except:
                self.logger.info(f"Starting web server on all interfaces - access at http://YOUR_IP_ADDRESS:{port}")
        else:
            self.logger.info(f"Starting web server on {host}:{port}")
        
        # Use Werkzeug's make_server instead of app.run() for better shutdown control
        self.server = self.werkzeug.serving.make_server(
            host, port, self.app, threaded=True
        )
        self.server.serve_forever()
    
    def shutdown(self) -> None:
        """Shutdown the web server gracefully."""
        if self.server:
            self.logger.info("Shutting down web server gracefully")
            self.server.shutdown()
    
    def _register_routes(self) -> None:
        """Register Flask routes."""
        app = self.app
        
        # Make config and version available to all templates
        @app.context_processor
        def inject_config():
            return {
                'config_obj': self.config,
                'version': __version__
            }
        
        # Authentication decorator
        def login_required(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self._is_authenticated():
                    return self.redirect(self.url_for('login'))
                return f(*args, **kwargs)
            return decorated_function
        
        # Configuration check decorator
        def configuration_required(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if not self.config.is_configured():
                    return self.redirect(self.url_for('setup_wizard'))
                return f(*args, **kwargs)
            return decorated_function
        
        # Setup wizard route
        @app.route('/setup', methods=['GET', 'POST'])
        def setup_wizard():
            # If already configured, redirect to dashboard
            if self.config.is_configured() and not self.request.args.get('force'):
                return self.redirect(self.url_for('dashboard'))
            
            # Get current step (default to 1)
            step = int(self.session.get('setup_step', 1))
            
            # Handle form submission
            if self.request.method == 'POST':
                # Handle step navigation
                if 'prev_step' in self.request.form:
                    step = int(self.request.form['prev_step'])
                    self.session['setup_step'] = step
                    return self.redirect(self.url_for('setup_wizard'))
                
                if 'next_step' in self.request.form:
                    # Process current step data
                    self._process_setup_step(step)
                    
                    # Move to next step
                    step = int(self.request.form['next_step'])
                    self.session['setup_step'] = step
                    return self.redirect(self.url_for('setup_wizard'))
                
                if 'complete_setup' in self.request.form:
                    # Process final step data
                    self._process_setup_step(step)
                    
                    # Mark as configured
                    self.config.mark_as_configured()
                    
                    # Clear session
                    self.session.pop('setup_step', None)
                    
                    # Redirect to dashboard
                    self.flash('Setup completed successfully!')
                    return self.redirect(self.url_for('dashboard'))
            
            # For GET requests or after processing POST
            # Detect subnet for network configuration step
            detected_subnet = None
            if step == 1:
                from cybex_pulse.core.setup_wizard import SetupWizard
                wizard = SetupWizard(self.config, self.db_manager)
                detected_subnet = wizard._detect_subnet()
            
            # Initialize fingerprinting config if needed
            if "fingerprinting" not in self.config.config and step >= 4:
                self.config.config["fingerprinting"] = {
                    "enabled": False,
                    "confidence_threshold": 0.5,
                    "max_threads": 10,
                    "timeout": 2
                }
            
            return self.render_template('setup_wizard.html',
                                       step=step,
                                       config=self.config,
                                       detected_subnet=detected_subnet)
        
        # Login route
        @app.route('/login', methods=['GET', 'POST'])
        def login():
            # If not configured, redirect to setup wizard
            if not self.config.is_configured():
                return self.redirect(self.url_for('setup_wizard'))
                
            if self.request.method == 'POST':
                username = self.request.form.get('username')
                password = self.request.form.get('password')
                
                if self._check_credentials(username, password):
                    self.session['logged_in'] = True
                    return self.redirect(self.url_for('dashboard'))
                else:
                    self.flash('Invalid credentials')
            
            return self.render_template('login.html')
        
        # Logout route
        @app.route('/logout')
        def logout():
            self.session.pop('logged_in', None)
            return self.redirect(self.url_for('login'))
        
        # Dashboard route
        @app.route('/')
        @login_required
        @configuration_required
        def dashboard():
            devices = self.db_manager.get_all_devices()
            # Add current timestamp for template
            now = int(time.time())
            
            # Get missing tools and their installation instructions
            missing_tools = {}
            for tool, installed in self.tool_status.items():
                if not installed:
                    missing_tools[tool] = get_installation_instructions(tool)
            
            # Get recent speed tests for Internet Health status
            speed_tests = self.db_manager.get_recent_speed_tests(limit=10)
            
            # Get recent events for dashboard display
            events = self.db_manager.get_recent_events(limit=5)
            
            # Get website monitoring data
            website_checks = []
            if self.config.config.get("monitoring", {}).get("websites", {}).get("enabled", False):
                # Get the most recent check for each website
                all_checks = self.db_manager.get_website_checks()
                url_to_latest_check = {}
                
                for check in all_checks:
                    url = check.get('url')
                    if url not in url_to_latest_check or check.get('timestamp', 0) > url_to_latest_check[url].get('timestamp', 0):
                        url_to_latest_check[url] = check
                
                website_checks = list(url_to_latest_check.values())
            
            # Count security vulnerabilities for Network Security status
            security_vulnerabilities = 0
            for device in devices:
                device_id = device.get('id')
                if device_id:
                    security_scans = self.db_manager.get_security_scans(device_id, limit=1)
                    if security_scans and security_scans[0].get('vulnerabilities'):
                        try:
                            vulnerabilities = json.loads(security_scans[0]['vulnerabilities'])
                            if vulnerabilities:
                                security_vulnerabilities += len(vulnerabilities)
                        except (json.JSONDecodeError, TypeError):
                            pass
            
            return self.render_template('dashboard.html',
                                       devices=devices,
                                       now=now,
                                       missing_tools=missing_tools,
                                       speed_tests=speed_tests,
                                       events=events,
                                       website_checks=website_checks,
                                       security_vulnerabilities=security_vulnerabilities,
                                       config=self.config)
        
        # Devices route
        @app.route('/devices')
        @login_required
        def devices():
            page = int(self.request.args.get('page', 1))
            page_size = 50
            all_devices = self.db_manager.get_all_devices()
            
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
            return self.render_template('devices.html', 
                                       devices=paginated_devices, 
                                       now=now, 
                                       db_manager=self.db_manager,
                                       current_page=page,
                                       total_pages=total_pages,
                                       total_devices=total_devices)
        
        # Device details route
        @app.route('/devices/<mac_address>')
        @login_required
        def device_details(mac_address):
            device = self.db_manager.get_device(mac_address)
            if not device:
                self.flash('Device not found')
                return self.redirect(self.url_for('devices'))
            
            # Get security scans for this device
            security_scans = self.db_manager.get_security_scans(device['id'], limit=10)
            
            # Add current timestamp for template
            now = int(time.time())
            
            # Check if fingerprinting is enabled (for UI purposes)
            fingerprinting_enabled = self.config.config.get("fingerprinting", {}).get("enabled", False)
            
            return self.render_template('device_details.html', device=device, security_scans=security_scans, 
                                      now=now, fingerprinting_enabled=fingerprinting_enabled)
                                      
        # Fingerprint device route
        @app.route('/devices/<mac_address>/fingerprint', methods=['POST'])
        @login_required
        def fingerprint_device(mac_address):
            # Get device details
            device = self.db_manager.get_device(mac_address)
            if not device:
                self.flash('Device not found')
                return self.redirect(self.url_for('devices'))
                
            # Check if fingerprinting is enabled
            if not self.config.config.get("fingerprinting", {}).get("enabled", False):
                self.flash('Device fingerprinting is not enabled')
                return self.redirect(self.url_for('device_details', mac_address=mac_address))
                
            # Check if device is marked as never fingerprint
            if device.get('never_fingerprint'):
                self.flash('This device is set to never be fingerprinted')
                return self.redirect(self.url_for('device_details', mac_address=mac_address))
                
            # Check if main app reference exists
            if not self.main_app or not self.main_app.network_scanner or not self.main_app.network_scanner.fingerprinter:
                self.flash('Fingerprinting engine is not available')
                return self.redirect(self.url_for('device_details', mac_address=mac_address))
                
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
                self.db_manager.update_device_metadata(device['mac_address'], device_info)
                self.logger.info(f"Cleared previous fingerprinting data for {device['mac_address']}")
                
                # Clear the in-memory fingerprinting cache as well
                if hasattr(self.main_app.network_scanner.fingerprinter, 'fingerprinted_mac_addresses'):
                    if device['mac_address'] in self.main_app.network_scanner.fingerprinter.fingerprinted_mac_addresses:
                        self.main_app.network_scanner.fingerprinter.fingerprinted_mac_addresses.remove(device['mac_address'])
                        self.logger.info(f"Removed {device['mac_address']} from in-memory fingerprinting cache")
                    
                # Perform fingerprinting - explicitly marking this as a manual operation
                # that should override any previous fingerprinting data and force a scan
                self.logger.info(f"Running manual fingerprinting for device: {device['mac_address']} ({device['ip_address']})")
                self.logger.info(f"This is a user-requested manual fingerprint operation (forced)")
                results = self.main_app.network_scanner.fingerprinter.fingerprint_network([device_to_fingerprint], force_scan=True)
                
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
                        self.db_manager.update_device_metadata(device['mac_address'], device_info)
                        
                        # Log fingerprinting result
                        hostname = device.get('hostname', '')
                        device_name = f"{device_info['device_manufacturer']} {device_info['device_model']}" if device_info['device_manufacturer'] and device_info['device_model'] else (hostname or device['mac_address'])
                        self.db_manager.log_event(
                            self.db_manager.EVENT_DEVICE_FINGERPRINTED,
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
                        
                        self.flash(f"Device successfully fingerprinted as {device_info['device_manufacturer']} {device_info['device_model']} with {confidence*100:.0f}% confidence")
                    else:
                        self.flash("Fingerprinting completed but no matches were found")
                else:
                    self.flash("Fingerprinting failed - no results returned")
            except Exception as e:
                self.logger.error(f"Error fingerprinting device: {e}")
                self.flash(f"Error fingerprinting device: {str(e)}")
                
            return self.redirect(self.url_for('device_details', mac_address=mac_address))
        
        # Mark device as important route
        @app.route('/devices/<mac_address>/important', methods=['POST'])
        @login_required
        def mark_device_important(mac_address):
            important = self.request.form.get('important') == 'true'
            self.db_manager.mark_device_important(mac_address, important)
            return self.redirect(self.url_for('device_details', mac_address=mac_address))
            
        # Edit device route
        @app.route('/devices/<mac_address>/edit', methods=['GET', 'POST'])
        @login_required
        def edit_device(mac_address):
            device = self.db_manager.get_device(mac_address)
            if not device:
                self.flash('Device not found')
                return self.redirect(self.url_for('devices'))
                
            if self.request.method == 'POST':
                # Get form data
                hostname = self.request.form.get('hostname', '')
                vendor = self.request.form.get('vendor', '')
                notes = self.request.form.get('notes', '')
                
                # Handle never_fingerprint checkbox
                never_fingerprint = 'never_fingerprint' in self.request.form
                
                # Handle clear fingerprint checkbox
                clear_fingerprint = 'clear_fingerprint' in self.request.form
                if clear_fingerprint:
                    self.db_manager.clear_device_fingerprint(mac_address)
                    self.logger.info(f"Cleared fingerprint data for device: {mac_address}")
                    self.db_manager.log_event(
                        self.db_manager.EVENT_SYSTEM,
                        "info",
                        f"Fingerprint data cleared for device: {hostname or mac_address}"
                    )
                
                # Update device
                self.db_manager.update_device(
                    mac_address=mac_address,
                    hostname=hostname,
                    vendor=vendor,
                    notes=notes,
                    never_fingerprint=never_fingerprint
                )
                
                self.logger.info(f"Updated device: {mac_address}")
                self.db_manager.log_event(
                    "user",  # Using a custom "user" event type instead of EVENT_SYSTEM
                    "info",
                    f"Device details updated: {hostname or mac_address}"
                )
                
                self.flash('Device updated successfully')
                return self.redirect(self.url_for('device_details', mac_address=mac_address))
                
            # Current timestamp for template
            now = int(time.time())
            
            # Check if fingerprinting is enabled (for UI purposes)
            fingerprinting_enabled = self.config.config.get("fingerprinting", {}).get("enabled", False)
            
            return self.render_template('edit_device.html', 
                                      device=device, 
                                      now=now, 
                                      fingerprinting_enabled=fingerprinting_enabled)
        
        # Events route
        @app.route('/events')
        @login_required
        def events():
            limit = int(self.request.args.get('limit', 100))
            event_type = self.request.args.get('type')
            severity = self.request.args.get('severity')
            
            events = self.db_manager.get_recent_events(limit, event_type, severity)
            
            # Add current timestamp for template
            now = int(time.time())
            
            return self.render_template('events.html', events=events, now=now)
        
        # Speed tests route
        @app.route('/speed-tests')
        @login_required
        def speed_tests():
            # Redirect to dashboard if internet health checks are not enabled
            if not self.config.config.get("monitoring", {}).get("internet_health", {}).get("enabled", False):
                self.flash('Internet health monitoring is not enabled')
                return self.redirect(self.url_for('dashboard'))
                
            tests = self.db_manager.get_recent_speed_tests()
            
            # Calculate averages and max values
            avg_download = 0
            avg_upload = 0
            avg_ping = 0
            max_download = 0
            max_upload = 0
            min_ping = 0
            
            if tests:
                download_speeds = [test['download_speed'] for test in tests if test['download_speed']]
                upload_speeds = [test['upload_speed'] for test in tests if test['upload_speed']]
                pings = [test['ping'] for test in tests if test['ping']]
                
                if download_speeds:
                    avg_download = sum(download_speeds) / len(download_speeds)
                    max_download = max(download_speeds)
                if upload_speeds:
                    avg_upload = sum(upload_speeds) / len(upload_speeds)
                    max_upload = max(upload_speeds)
                if pings:
                    avg_ping = sum(pings) / len(pings)
                    min_ping = min(pings)
            
            # Add current timestamp for template
            now = int(time.time())
            
            return self.render_template('speed_tests.html', tests=tests,
                                       avg_download=avg_download,
                                       avg_upload=avg_upload,
                                       avg_ping=avg_ping,
                                       max_download=max_download,
                                       max_upload=max_upload,
                                       min_ping=min_ping,
                                       now=now)
        
        # Website checks route
        @app.route('/websites')
        @login_required
        def websites():
            # Redirect to dashboard if website monitoring is not enabled
            if not self.config.config.get("monitoring", {}).get("websites", {}).get("enabled", False):
                self.flash('Website monitoring is not enabled')
                return self.redirect(self.url_for('dashboard'))
                
            checks = self.db_manager.get_website_checks()
            
            # Get configured website URLs from config
            configured_urls = self.config.config.get("monitoring", {}).get("websites", {}).get("urls", [])
            
            # Process checks to create a list of website statuses
            websites = []
            url_latest_checks = {}
            
            # Group checks by URL and find the latest check for each URL
            for check in checks:
                url = check['url']
                if url not in url_latest_checks or check['timestamp'] > url_latest_checks[url]['timestamp']:
                    url_latest_checks[url] = check
            
            # Create website objects from the latest checks
            for url, check in url_latest_checks.items():
                websites.append(check)
            
            # Add any configured URLs that don't have checks yet
            for url in configured_urls:
                if url not in url_latest_checks:
                    websites.append({
                        'url': url,
                        'is_up': False,
                        'status_code': None,
                        'response_time': None,
                        'timestamp': None,
                        'error_message': 'No checks performed yet'
                    })
            
            # Add current timestamp for template
            now = int(time.time())
            
            return self.render_template('websites.html', websites=websites, checks=checks, now=now)
            
        # Network Security route
        @app.route('/network-security')
        @login_required
        def network_security():
            # Redirect to dashboard if security scanning is not enabled
            if not self.config.config.get("monitoring", {}).get("security", {}).get("enabled", False):
                self.flash('Network security scanning is not enabled')
                return self.redirect(self.url_for('dashboard'))
                
            devices = self.db_manager.get_all_devices()
            now = int(time.time())
            
            # Count security vulnerabilities
            security_vulnerabilities = 0
            vulnerable_devices = []
            last_scan = None
            
            for device in devices:
                device_id = device.get('id')
                if device_id:
                    security_scans = self.db_manager.get_security_scans(device_id, limit=1)
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
            
            return self.render_template('network_security.html',
                                      security_vulnerabilities=security_vulnerabilities,
                                      vulnerable_devices=vulnerable_devices,
                                      last_scan=last_scan,
                                      now=now)
                                      
        # Fingerprinting information route
        @app.route('/fingerprinting')
        @login_required
        def fingerprinting():
            # Redirect to dashboard if fingerprinting is not enabled
            if not self.config.config.get("fingerprinting", {}).get("enabled", False):
                self.flash('Device fingerprinting is not enabled')
                return self.redirect(self.url_for('dashboard'))
                
            return self.render_template('fingerprinting.html',
                                      config=self.config)
            
        # Website history route
        @app.route('/websites/history/<path:url>')
        @login_required
        def website_history(url):
            # Redirect to dashboard if website monitoring is not enabled
            if not self.config.config.get("monitoring", {}).get("websites", {}).get("enabled", False):
                self.flash('Website monitoring is not enabled')
                return self.redirect(self.url_for('dashboard'))
                
            # Get checks for the specific URL
            checks = self.db_manager.get_website_checks(url=url, limit=100)
            
            if not checks:
                self.flash(f'No history found for {url}')
                return self.redirect(self.url_for('websites'))
            
            # Prepare data for response time chart
            timestamps = []
            response_times = []
            
            for check in checks:
                if check['timestamp'] and check['response_time']:
                    timestamps.append(self.app.jinja_env.filters['timestamp_to_time'](check['timestamp']))
                    response_times.append(check['response_time'])
            
            # Reverse the lists to show oldest first
            timestamps.reverse()
            response_times.reverse()
            
            response_times_data = {
                'labels': timestamps,
                'datasets': {
                    url: response_times
                }
            }
            
            # Add current timestamp for template
            now = int(time.time())
            
            return self.render_template('websites.html',
                                       checks=checks,
                                       now=now,
                                       response_times=response_times_data,
                                       website_url=url)
        
        # About route
        @app.route('/about')
        @login_required
        def about():
            return self.render_template('about.html')
            
        # Settings route
        @app.route('/settings', methods=['GET', 'POST'])
        @login_required
        def settings():
            if self.request.method == 'POST':
                # Update settings
                self._update_settings_from_form(self.request.form)
                self.flash('Settings updated successfully')
                return self.redirect(self.url_for('settings'))
            
            # Get missing tools and their installation instructions
            missing_tools = {}
            for tool, installed in self.tool_status.items():
                if not installed:
                    missing_tools[tool] = get_installation_instructions(tool)
            
            # Ensure fingerprinting config section exists
            if 'fingerprinting' not in self.config.config:
                self.config.config['fingerprinting'] = {
                    'enabled': False,
                    'confidence_threshold': 0.5,
                    'max_threads': 10,
                    'timeout': 2
                }
                
            return self.render_template('settings.html',
                                      config=self.config.config,
                                      missing_tools=missing_tools,
                                      tool_status=self.tool_status)
        
        # API routes for AJAX requests
        
        # API: Get all devices
        @app.route('/api/devices')
        @login_required
        def api_devices():
            page = int(self.request.args.get('page', 1))
            page_size = 50
            all_devices = self.db_manager.get_all_devices()
            
            # Calculate total pages
            total_devices = len(all_devices)
            total_pages = (total_devices + page_size - 1) // page_size
            
            # Paginate devices if page parameter is provided
            if 'page' in self.request.args:
                start_idx = (page - 1) * page_size
                end_idx = start_idx + page_size
                paginated_devices = all_devices[start_idx:end_idx]
                return self.jsonify({
                    'devices': paginated_devices,
                    'total_pages': total_pages,
                    'current_page': page,
                    'total_devices': total_devices
                })
            else:
                # For backward compatibility, return all devices if no page specified
                return self.jsonify(all_devices)
            
        # API: Get device ports
        @app.route('/api/devices/<int:device_id>/ports')
        @login_required
        def api_device_ports(device_id):
            # Return empty array if security scanning is not enabled
            if not self.config.config.get("monitoring", {}).get("security", {}).get("enabled", False):
                return self.jsonify({"ports": []})
                
            security_scans = self.db_manager.get_security_scans(device_id, limit=1)
            
            ports = []
            if security_scans and security_scans[0].get('open_ports'):
                try:
                    ports = json.loads(security_scans[0]['open_ports'])
                except (json.JSONDecodeError, TypeError):
                    ports = []
                
            return self.jsonify({"ports": ports})
        
        # API: Get recent events
        @app.route('/api/events')
        @login_required
        def api_events():
            limit = int(self.request.args.get('limit', 100))
            event_type = self.request.args.get('type')
            severity = self.request.args.get('severity')
            
            events = self.db_manager.get_recent_events(limit, event_type, severity)
            return self.jsonify(events)
        
        # API: Get recent speed tests
        @app.route('/api/speed-tests')
        @login_required
        def api_speed_tests():
            # Return empty array if internet health checks are not enabled
            if not self.config.config.get("monitoring", {}).get("internet_health", {}).get("enabled", False):
                return self.jsonify([])
                
            limit = int(self.request.args.get('limit', 10))
            tests = self.db_manager.get_recent_speed_tests(limit)
            return self.jsonify(tests)
            
        # API: Get device icon
        @app.route('/api/device-icon')
        @login_required
        def api_device_icon():
            vendor = self.request.args.get('vendor', '')
            device_name = self.request.args.get('device_name', '')
            
            from cybex_pulse.utils.icon_mapper import IconMapper
            icon_mapper = IconMapper()
            icon_html = icon_mapper.get_icon_html(vendor, device_name)
            
            return icon_html
            
        # API: Get fingerprinting modules and signature counts
        @app.route('/api/fingerprinting/modules')
        @login_required
        def api_fingerprinting_modules():
            # Return empty data if fingerprinting is not enabled
            if not self.config.config.get("fingerprinting", {}).get("enabled", False):
                return self.jsonify({
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
                                'device_types': self.get_unique_device_types(module_obj.SIGNATURES)
                            }
                
                total_signatures = engine.get_signature_count()
                
                return self.jsonify({
                    'modules': module_stats,
                    'total_signatures': total_signatures
                })
            except ImportError:
                return self.jsonify({
                    'error': 'Fingerprinting module not available',
                    'modules': {},
                    'total_signatures': 0
                })
                
    def get_unique_device_types(self, signatures):
        """Get unique device types from signatures dictionary."""
        device_types = set()
        for sig_id, signature in signatures.items():
            if 'device_type' in signature:
                device_types.add(signature['device_type'])
        return list(device_types)
        
        # Error handlers
        @app.errorhandler(404)
        def page_not_found(e):
            return self.render_template('404.html'), 404
        
        @app.errorhandler(500)
        def server_error(e):
            return self.render_template('500.html'), 500
    
    def _is_authenticated(self) -> bool:
        """Check if user is authenticated.
        
        Returns:
            bool: True if authenticated, False otherwise
        """
        # If no authentication is configured, allow access
        username = self.config.get("web_interface", "username")
        password_hash = self.config.get("web_interface", "password_hash")
        
        if not username or not password_hash:
            return True
        
        return self.session.get('logged_in', False)
    
    def _check_credentials(self, username: str, password: str) -> bool:
        """Check if credentials are valid.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        config_username = self.config.get("web_interface", "username")
        config_password_hash = self.config.get("web_interface", "password_hash")
        
        if not config_username or not config_password_hash:
            return True
        
        # Hash the provided password
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        return username == config_username and password_hash == config_password_hash
    
    def _register_filters(self) -> None:
        """Register custom Jinja2 filters."""
        @self.app.template_filter('timestamp_to_time')
        def timestamp_to_time(timestamp):
            """Convert Unix timestamp to human-readable time."""
            if not timestamp:
                return "N/A"
            return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(timestamp))
        
        @self.app.template_filter('timestamp_to_relative_time')
        def timestamp_to_relative_time(timestamp):
            """Convert Unix timestamp to relative time (e.g., '5m ago')."""
            if not timestamp:
                return "N/A"
            
            now = time.time()
            diff = now - timestamp
            
            if diff < 60:
                return "Just now"
            elif diff < 3600:
                minutes = int(diff / 60)
                return f"{minutes}m ago"
            elif diff < 86400:
                hours = int(diff / 3600)
                return f"{hours}h ago" 
            else:
                days = int(diff / 86400)
                return f"{days}d ago"
        
        @self.app.template_filter('from_json')
        def from_json(json_string):
            """Convert JSON string to Python object."""
            import json
            if not json_string:
                return []
            try:
                return json.loads(json_string)
            except (json.JSONDecodeError, TypeError):
                return []
        
        @self.app.template_filter('device_icon')
        def device_icon(vendor, device_name=None):
            """Get the appropriate Font Awesome icon HTML for a device based on vendor and device name."""
            from cybex_pulse.utils.icon_mapper import IconMapper
            icon_mapper = IconMapper()
            return icon_mapper.get_icon_html(vendor, device_name)
    
    def _process_setup_step(self, step: int) -> None:
        """Process setup wizard step data.
        
        Args:
            step: Current setup step
        """
        form = self.request.form
        
        # Step 1: Network Configuration
        if step == 1:
            # Handle subnet
            use_detected = form.get('use_detected_subnet') == 'on'
            if use_detected:
                from cybex_pulse.core.setup_wizard import SetupWizard
                wizard = SetupWizard(self.config, self.db_manager)
                subnet = wizard._detect_subnet()
                if subnet:
                    self.config.set("network", "subnet", subnet)
            else:
                subnet = form.get('subnet')
                if subnet:
                    self.config.set("network", "subnet", subnet)
            
            # Handle scan interval
            scan_interval = form.get('scan_interval')
            if scan_interval and scan_interval.isdigit() and int(scan_interval) > 0:
                self.config.set("general", "scan_interval", int(scan_interval))
        
        # Step 2: Alert Configuration
        elif step == 2:
            # Telegram configuration
            enable_telegram = form.get('enable_telegram') == 'on'
            self.config.set("telegram", "enabled", enable_telegram)
            
            if enable_telegram:
                api_token = form.get('telegram_api_token')
                if api_token:
                    self.config.set("telegram", "api_token", api_token)
                
                chat_id = form.get('telegram_chat_id')
                if chat_id:
                    self.config.set("telegram", "chat_id", chat_id)
            
            # Alert settings
            new_device_alert = form.get('new_device_alert') == 'on'
            self.config.set("alerts", "new_device", new_device_alert)
            
            device_offline_alert = form.get('device_offline_alert') == 'on'
            self.config.set("alerts", "device_offline", device_offline_alert)
            
            important_device_alert = form.get('important_device_alert') == 'on'
            self.config.set("alerts", "important_device_offline", important_device_alert)
        
        # Step 3: Web Interface Configuration
        elif step == 3:
            # Web interface is always enabled in this implementation
            self.config.set("web_interface", "enabled", True)
            
            # Host configuration
            host = form.get('web_host')
            if host:
                self.config.set("web_interface", "host", host)
            
            # Port configuration
            port = form.get('web_port')
            if port and port.isdigit() and 1024 <= int(port) <= 65535:
                self.config.set("web_interface", "port", int(port))
            
            # Authentication
            setup_auth = form.get('setup_auth') == 'on'
            if setup_auth:
                import hashlib
                
                username = form.get('web_username')
                if username:
                    self.config.set("web_interface", "username", username)
                
                password = form.get('web_password')
                if password:
                    # Hash the password
                    password_hash = hashlib.sha256(password.encode()).hexdigest()
                    self.config.set("web_interface", "password_hash", password_hash)
        
        # Step 4: Fingerprinting Configuration
        elif step == 4:
            # Setup fingerprinting options
            enable_fingerprinting = form.get('enable_fingerprinting') == 'on'
            
            # Initialize fingerprinting config if it doesn't exist
            if "fingerprinting" not in self.config.config:
                self.config.config["fingerprinting"] = {
                    "enabled": False,
                    "confidence_threshold": 0.5,
                    "max_threads": 10,
                    "timeout": 2
                }
            
            # Set fingerprinting enabled state
            self.config.set("fingerprinting", "enabled", enable_fingerprinting)
            
            if enable_fingerprinting:
                # Confidence threshold
                fingerprinting_confidence = form.get('fingerprinting_confidence')
                if fingerprinting_confidence and 0.1 <= float(fingerprinting_confidence) <= 1.0:
                    self.config.set("fingerprinting", "confidence_threshold", float(fingerprinting_confidence))
                
                # Max threads
                fingerprinting_max_threads = form.get('fingerprinting_max_threads')
                if fingerprinting_max_threads and fingerprinting_max_threads.isdigit() and 1 <= int(fingerprinting_max_threads) <= 20:
                    self.config.set("fingerprinting", "max_threads", int(fingerprinting_max_threads))
                
                # Timeout
                fingerprinting_timeout = form.get('fingerprinting_timeout')
                if fingerprinting_timeout and fingerprinting_timeout.isdigit() and 1 <= int(fingerprinting_timeout) <= 10:
                    self.config.set("fingerprinting", "timeout", int(fingerprinting_timeout))
        
        # Step 5: Additional Features Configuration
        elif step == 5:
            # Internet health check
            enable_health = form.get('enable_health') == 'on'
            internet_health = self.config.get("monitoring", "internet_health", {})
            internet_health["enabled"] = enable_health
            self.config.set("monitoring", "internet_health", internet_health)
            
            # Website monitoring
            enable_websites = form.get('enable_websites') == 'on'
            websites = self.config.get("monitoring", "websites", {})
            websites["enabled"] = enable_websites
            
            if enable_websites:
                website_urls = []
                for i in range(5):
                    url = form.get(f'website_url_{i}')
                    if url:
                        website_urls.append(url)
                
                websites["urls"] = website_urls
            
            self.config.set("monitoring", "websites", websites)
            
            # Security scanning
            enable_security = form.get('enable_security') == 'on'
            security = self.config.get("monitoring", "security", {})
            security["enabled"] = enable_security
            self.config.set("monitoring", "security", security)
    
    def _update_settings_from_form(self, form: Dict[str, str]) -> None:
        """Update settings from form data.
        
        Args:
            form: Form data
        """
        # Track changes in monitoring settings to update threads later
        original_settings = {
            "health_check": self.config.get("monitoring", "internet_health", {}).get("enabled", False),
            "website_monitoring": self.config.get("monitoring", "websites", {}).get("enabled", False),
            "security_scanning": self.config.get("monitoring", "security", {}).get("enabled", False)
        }
        
        # Network settings
        subnet = form.get('subnet')
        if subnet:
            self.config.set("network", "subnet", subnet)
        
        scan_interval = form.get('scan_interval')
        if scan_interval and scan_interval.isdigit() and int(scan_interval) > 0:
            self.config.set("general", "scan_interval", int(scan_interval))
        
        # Alert settings
        alerts_enabled = form.get('alerts_enabled') == 'on'
        self.config.set("alerts", "enabled", alerts_enabled)
        
        new_device_alert = form.get('new_device_alert') == 'on'
        self.config.set("alerts", "new_device", new_device_alert)
        
        device_offline_alert = form.get('device_offline_alert') == 'on'
        self.config.set("alerts", "device_offline", device_offline_alert)
        
        important_device_offline_alert = form.get('important_device_offline_alert') == 'on'
        self.config.set("alerts", "important_device_offline", important_device_offline_alert)
        
        latency_threshold = form.get('latency_threshold')
        if latency_threshold and latency_threshold.isdigit() and int(latency_threshold) > 0:
            self.config.set("alerts", "latency_threshold", int(latency_threshold))
        
        website_error_alert = form.get('website_error_alert') == 'on'
        self.config.set("alerts", "website_error", website_error_alert)
        
        # Fingerprinting settings
        original_fingerprinting_enabled = self.config.get("fingerprinting", "enabled", default=False)
        fingerprinting_enabled = form.get('fingerprinting_enabled') == 'on'
        self.config.set("fingerprinting", "enabled", fingerprinting_enabled)
        
        fingerprinting_settings_changed = original_fingerprinting_enabled != fingerprinting_enabled
        
        fingerprinting_confidence = form.get('fingerprinting_confidence')
        if fingerprinting_confidence and float(fingerprinting_confidence) >= 0.1 and float(fingerprinting_confidence) <= 1.0:
            original_confidence = self.config.get("fingerprinting", "confidence_threshold", default=0.5)
            if float(fingerprinting_confidence) != original_confidence:
                fingerprinting_settings_changed = True
            self.config.set("fingerprinting", "confidence_threshold", float(fingerprinting_confidence))
        
        fingerprinting_max_threads = form.get('fingerprinting_max_threads')
        if fingerprinting_max_threads and fingerprinting_max_threads.isdigit() and 1 <= int(fingerprinting_max_threads) <= 20:
            original_max_threads = self.config.get("fingerprinting", "max_threads", default=10)
            if int(fingerprinting_max_threads) != original_max_threads:
                fingerprinting_settings_changed = True
            self.config.set("fingerprinting", "max_threads", int(fingerprinting_max_threads))
            
        fingerprinting_timeout = form.get('fingerprinting_timeout')
        if fingerprinting_timeout and fingerprinting_timeout.isdigit() and 1 <= int(fingerprinting_timeout) <= 10:
            original_timeout = self.config.get("fingerprinting", "timeout", default=2)
            if int(fingerprinting_timeout) != original_timeout:
                fingerprinting_settings_changed = True
            self.config.set("fingerprinting", "timeout", int(fingerprinting_timeout))
        
        # Telegram settings
        telegram_enabled = form.get('telegram_enabled') == 'on'
        self.config.set("telegram", "enabled", telegram_enabled)
        
        telegram_api_token = form.get('telegram_api_token')
        if telegram_api_token:
            self.config.set("telegram", "api_token", telegram_api_token)
        
        telegram_chat_id = form.get('telegram_chat_id')
        if telegram_chat_id:
            self.config.set("telegram", "chat_id", telegram_chat_id)
        
        # Internet health check settings
        internet_health_enabled = form.get('internet_health_enabled') == 'on'
        internet_health_interval = form.get('internet_health_interval')
        
        internet_health = self.config.get("monitoring", "internet_health", {})
        internet_health["enabled"] = internet_health_enabled
        
        if internet_health_interval and internet_health_interval.isdigit() and int(internet_health_interval) > 0:
            internet_health["interval"] = int(internet_health_interval)
        
        self.config.set("monitoring", "internet_health", internet_health)
        
        # Website monitoring settings
        websites_enabled = form.get('websites_enabled') == 'on'
        websites_interval = form.get('websites_interval')
        
        websites = self.config.get("monitoring", "websites", {})
        websites["enabled"] = websites_enabled
        
        if websites_interval and websites_interval.isdigit() and int(websites_interval) > 0:
            websites["interval"] = int(websites_interval)
        
        # Update website URLs
        website_urls = []
        for i in range(5):
            url = form.get(f'website_url_{i}')
            if url:
                website_urls.append(url)
        
        websites["urls"] = website_urls
        self.config.set("monitoring", "websites", websites)
        
        # Security scanning settings
        security_enabled = form.get('security_enabled') == 'on'
        security_interval = form.get('security_interval')
        
        security = self.config.get("monitoring", "security", {})
        security["enabled"] = security_enabled
        
        if security_interval and security_interval.isdigit() and int(security_interval) > 0:
            security["interval"] = int(security_interval)
        
        self.config.set("monitoring", "security", security)
        
        # Web interface settings
        web_host = form.get('web_host')
        if web_host:
            self.config.set("web_interface", "host", web_host)
        
        web_port = form.get('web_port')
        if web_port and web_port.isdigit() and 1024 <= int(web_port) <= 65535:
            self.config.set("web_interface", "port", int(web_port))
        
        # Authentication settings
        web_username = form.get('web_username')
        web_password = form.get('web_password')
        
        if web_username:
            self.config.set("web_interface", "username", web_username)
        
        if web_password:
            # Hash the password
            password_hash = hashlib.sha256(web_password.encode()).hexdigest()
            self.config.set("web_interface", "password_hash", password_hash)
            
        # Update monitoring threads if settings have changed and the main_app reference exists
        if self.main_app:
            current_settings = {
                "health_check": self.config.get("monitoring", "internet_health", {}).get("enabled", False),
                "website_monitoring": self.config.get("monitoring", "websites", {}).get("enabled", False),
                "security_scanning": self.config.get("monitoring", "security", {}).get("enabled", False)
            }
            
            # Check if any monitoring settings changed
            settings_changed = original_settings != current_settings
            
            # Also check if fingerprinting settings changed
            if 'fingerprinting_settings_changed' in locals() and fingerprinting_settings_changed:
                settings_changed = True
                
            if settings_changed:
                self.logger.info("Monitoring or fingerprinting settings changed, updating threads")
                self.main_app.update_monitoring_state()