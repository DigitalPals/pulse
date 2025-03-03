"""
Setup and settings routes for the web interface.
"""
import hashlib
from typing import Dict


def register_setup_routes(app, server):
    """Register setup and settings routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Setup wizard route
    @app.route('/setup', methods=['GET', 'POST'])
    def setup_wizard():
        # If already configured, redirect to dashboard
        if server.config.is_configured() and not server.request.args.get('force'):
            return server.redirect(server.url_for('dashboard'))
        
        # Get current step (default to 1)
        step = int(server.session.get('setup_step', 1))
        
        # Handle form submission
        if server.request.method == 'POST':
            # Handle step navigation
            if 'prev_step' in server.request.form:
                step = int(server.request.form['prev_step'])
                server.session['setup_step'] = step
                return server.redirect(server.url_for('setup_wizard'))
            
            if 'next_step' in server.request.form:
                # Process current step data
                process_setup_step(server, step)
                
                # Move to next step
                step = int(server.request.form['next_step'])
                server.session['setup_step'] = step
                return server.redirect(server.url_for('setup_wizard'))
            
            if 'complete_setup' in server.request.form:
                # Process final step data
                process_setup_step(server, step)
                
                # Mark as configured
                server.config.mark_as_configured()
                
                # Clear session
                server.session.pop('setup_step', None)
                
                # Redirect to dashboard
                server.flash('Setup completed successfully!')
                return server.redirect(server.url_for('dashboard'))
        
        # For GET requests or after processing POST
        # Detect subnet for network configuration step
        detected_subnet = None
        if step == 1:
            from cybex_pulse.core.setup_wizard import SetupWizard
            wizard = SetupWizard(server.config, server.db_manager)
            detected_subnet = wizard._detect_subnet()
        
        # Initialize fingerprinting config if needed
        if "fingerprinting" not in server.config.config and step >= 4:
            server.config.config["fingerprinting"] = {
                "enabled": False,
                "confidence_threshold": 0.5,
                "max_threads": 10,
                "timeout": 2
            }
        
        return server.render_template('setup_wizard.html',
                                   step=step,
                                   config=server.config,
                                   detected_subnet=detected_subnet)

    # Settings route
    @app.route('/settings', methods=['GET', 'POST'])
    @server.login_required
    def settings():
        # Handle advanced actions
        action = server.request.args.get('action')
        if server.request.method == 'POST' and action:
            if action == 'clear_database':
                # Clear the database
                count = server.db_manager.clear_all_devices()
                
                # Reset in-memory caches if main_app is available
                if server.main_app:
                    # Reset network scanner caches
                    if hasattr(server.main_app.network_scanner, 'current_scan_devices'):
                        server.main_app.network_scanner.current_scan_devices = set()
                    if hasattr(server.main_app.network_scanner, 'previous_scan_devices'):
                        server.main_app.network_scanner.previous_scan_devices = set()
                    
                    # Reset fingerprinter cache if it exists
                    if (server.main_app.network_scanner.fingerprinter and
                        hasattr(server.main_app.network_scanner.fingerprinter, 'fingerprinted_mac_addresses')):
                        server.main_app.network_scanner.fingerprinter.fingerprinted_mac_addresses = set()
                        server.logger.info("Reset fingerprinter in-memory cache")
                
                server.flash(f'Database cleared successfully. {count} devices and all related data removed.')
                server.logger.warning(f"User initiated database clear. {count} devices and all related data removed.")
                return server.redirect(server.url_for('settings'))
            elif action == 'remove_database':
                # Completely remove the database file
                success = server.db_manager.remove_database()
                
                # Reset in-memory caches if main_app is available
                if server.main_app:
                    # Reset network scanner caches
                    if hasattr(server.main_app.network_scanner, 'current_scan_devices'):
                        server.main_app.network_scanner.current_scan_devices = set()
                    if hasattr(server.main_app.network_scanner, 'previous_scan_devices'):
                        server.main_app.network_scanner.previous_scan_devices = set()
                    
                    # Reset fingerprinter cache if it exists
                    if (server.main_app.network_scanner.fingerprinter and
                        hasattr(server.main_app.network_scanner.fingerprinter, 'fingerprinted_mac_addresses')):
                        server.main_app.network_scanner.fingerprinter.fingerprinted_mac_addresses = set()
                        server.logger.info("Reset fingerprinter in-memory cache")
                
                if success:
                    server.flash('Database file completely removed from the system.')
                    server.logger.warning("User initiated complete database removal.")
                else:
                    server.flash('Failed to remove database file. Check logs for details.', 'error')
                    server.logger.error("Failed to remove database file.")
                
                return server.redirect(server.url_for('settings'))
            elif action == 'clear_config':
                # Reset configuration to defaults
                # Preserve web interface settings
                web_interface_settings = server.config.get("web_interface")
                
                # Reset to defaults
                server.config.config = server.config.DEFAULT_CONFIG.copy()
                
                # Restore web interface settings
                server.config.set("web_interface", None, web_interface_settings)
                
                # Save the configuration
                server.config.save()
                
                server.flash('Configuration reset to default values successfully.')
                server.logger.warning("User initiated configuration reset.")
                return server.redirect(server.url_for('settings'))
        
        if server.request.method == 'POST':
            # Update settings
            update_settings_from_form(server, server.request.form)
            server.flash('Settings updated successfully')
            return server.redirect(server.url_for('settings'))
        
        # Get missing tools and their installation instructions
        missing_tools = {}
        for tool, installed in server.tool_status.items():
            if not installed:
                missing_tools[tool] = server.get_installation_instructions(tool)
        
        # Ensure fingerprinting config section exists
        if 'fingerprinting' not in server.config.config:
            server.config.config['fingerprinting'] = {
                'enabled': False,
                'confidence_threshold': 0.5,
                'max_threads': 10,
                'timeout': 2
            }
            
        return server.render_template('settings.html',
                                   config=server.config.config,
                                   missing_tools=missing_tools,
                                   tool_status=server.tool_status)


def process_setup_step(server, step: int) -> None:
    """Process setup wizard step data.
    
    Args:
        server: WebServer instance
        step: Current setup step
    """
    form = server.request.form
    
    # Step 1: Network Configuration
    if step == 1:
        # Handle subnet
        use_detected = form.get('use_detected_subnet') == 'on'
        if use_detected:
            from cybex_pulse.core.setup_wizard import SetupWizard
            wizard = SetupWizard(server.config, server.db_manager)
            subnet = wizard._detect_subnet()
            if subnet:
                server.config.set("network", "subnet", subnet)
        else:
            subnet = form.get('subnet')
            if subnet:
                server.config.set("network", "subnet", subnet)
        
        # Handle scan interval
        scan_interval = form.get('scan_interval')
        if scan_interval and scan_interval.isdigit() and int(scan_interval) > 0:
            server.config.set("general", "scan_interval", int(scan_interval))
    
    # Step 2: Alert Configuration
    elif step == 2:
        # Telegram configuration
        enable_telegram = form.get('enable_telegram') == 'on'
        server.config.set("telegram", "enabled", enable_telegram)
        
        if enable_telegram:
            api_token = form.get('telegram_api_token')
            if api_token:
                server.config.set("telegram", "api_token", api_token)
            
            chat_id = form.get('telegram_chat_id')
            if chat_id:
                server.config.set("telegram", "chat_id", chat_id)
        
        # Alert settings
        new_device_alert = form.get('new_device_alert') == 'on'
        server.config.set("alerts", "new_device", new_device_alert)
        
        device_offline_alert = form.get('device_offline_alert') == 'on'
        server.config.set("alerts", "device_offline", device_offline_alert)
        
        important_device_alert = form.get('important_device_alert') == 'on'
        server.config.set("alerts", "important_device_offline", important_device_alert)
    
    # Step 3: Web Interface Configuration
    elif step == 3:
        # Web interface is always enabled in this implementation
        server.config.set("web_interface", "enabled", True)
        
        # Host configuration
        host = form.get('web_host')
        if host:
            server.config.set("web_interface", "host", host)
        
        # Port configuration
        port = form.get('web_port')
        if port and port.isdigit() and 1024 <= int(port) <= 65535:
            server.config.set("web_interface", "port", int(port))
        
        # Authentication
        setup_auth = form.get('setup_auth') == 'on'
        if setup_auth:
            import hashlib
            
            username = form.get('web_username')
            if username:
                server.config.set("web_interface", "username", username)
            
            password = form.get('web_password')
            if password:
                # Hash the password
                password_hash = hashlib.sha256(password.encode()).hexdigest()
                server.config.set("web_interface", "password_hash", password_hash)
    
    # Step 4: Fingerprinting Configuration
    elif step == 4:
        # Setup fingerprinting options
        enable_fingerprinting = form.get('enable_fingerprinting') == 'on'
        
        # Initialize fingerprinting config if it doesn't exist
        if "fingerprinting" not in server.config.config:
            server.config.config["fingerprinting"] = {
                "enabled": False,
                "confidence_threshold": 0.5,
                "max_threads": 10,
                "timeout": 2
            }
        
        # Set fingerprinting enabled state
        server.config.set("fingerprinting", "enabled", enable_fingerprinting)
        
        if enable_fingerprinting:
            # Confidence threshold
            fingerprinting_confidence = form.get('fingerprinting_confidence')
            if fingerprinting_confidence and 0.1 <= float(fingerprinting_confidence) <= 1.0:
                server.config.set("fingerprinting", "confidence_threshold", float(fingerprinting_confidence))
            
            # Max threads
            fingerprinting_max_threads = form.get('fingerprinting_max_threads')
            if fingerprinting_max_threads and fingerprinting_max_threads.isdigit() and 1 <= int(fingerprinting_max_threads) <= 20:
                server.config.set("fingerprinting", "max_threads", int(fingerprinting_max_threads))
            
            # Timeout
            fingerprinting_timeout = form.get('fingerprinting_timeout')
            if fingerprinting_timeout and fingerprinting_timeout.isdigit() and 1 <= int(fingerprinting_timeout) <= 10:
                server.config.set("fingerprinting", "timeout", int(fingerprinting_timeout))
    
    # Step 5: Additional Features Configuration
    elif step == 5:
        # Internet health check
        enable_health = form.get('enable_health') == 'on'
        internet_health = server.config.get("monitoring", "internet_health", {})
        internet_health["enabled"] = enable_health
        server.config.set("monitoring", "internet_health", internet_health)
        
        # Website monitoring
        enable_websites = form.get('enable_websites') == 'on'
        websites = server.config.get("monitoring", "websites", {})
        websites["enabled"] = enable_websites
        
        if enable_websites:
            website_urls = []
            for i in range(5):
                url = form.get(f'website_url_{i}')
                if url:
                    website_urls.append(url)
            
            websites["urls"] = website_urls
        
        server.config.set("monitoring", "websites", websites)
        
        # Security scanning
        enable_security = form.get('enable_security') == 'on'
        security = server.config.get("monitoring", "security", {})
        security["enabled"] = enable_security
        server.config.set("monitoring", "security", security)


def update_settings_from_form(server, form: Dict[str, str]) -> None:
    """Update settings from form data.
    
    Args:
        server: WebServer instance
        form: Form data
    """
    # Track changes in monitoring settings to update threads later
    original_settings = {
        "health_check": server.config.get("monitoring", "internet_health", {}).get("enabled", False),
        "website_monitoring": server.config.get("monitoring", "websites", {}).get("enabled", False),
        "security_scanning": server.config.get("monitoring", "security", {}).get("enabled", False)
    }
    
    # Network settings
    subnet = form.get('subnet')
    if subnet:
        server.config.set("network", "subnet", subnet)
    
    scan_interval = form.get('scan_interval')
    if scan_interval and scan_interval.isdigit() and int(scan_interval) > 0:
        server.config.set("general", "scan_interval", int(scan_interval))
    
    # Alert settings
    alerts_enabled = form.get('alerts_enabled') == 'on'
    server.config.set("alerts", "enabled", alerts_enabled)
    
    new_device_alert = form.get('new_device_alert') == 'on'
    server.config.set("alerts", "new_device", new_device_alert)
    
    device_offline_alert = form.get('device_offline_alert') == 'on'
    server.config.set("alerts", "device_offline", device_offline_alert)
    
    important_device_offline_alert = form.get('important_device_offline_alert') == 'on'
    server.config.set("alerts", "important_device_offline", important_device_offline_alert)
    
    latency_threshold = form.get('latency_threshold')
    if latency_threshold and latency_threshold.isdigit() and int(latency_threshold) > 0:
        server.config.set("alerts", "latency_threshold", int(latency_threshold))
    
    website_error_alert = form.get('website_error_alert') == 'on'
    server.config.set("alerts", "website_error", website_error_alert)
    
    # Fingerprinting settings
    original_fingerprinting_enabled = server.config.get("fingerprinting", "enabled", default=False)
    fingerprinting_enabled = form.get('fingerprinting_enabled') == 'on'
    server.config.set("fingerprinting", "enabled", fingerprinting_enabled)
    
    fingerprinting_settings_changed = original_fingerprinting_enabled != fingerprinting_enabled
    
    fingerprinting_confidence = form.get('fingerprinting_confidence')
    if fingerprinting_confidence and float(fingerprinting_confidence) >= 0.1 and float(fingerprinting_confidence) <= 1.0:
        original_confidence = server.config.get("fingerprinting", "confidence_threshold", default=0.5)
        if float(fingerprinting_confidence) != original_confidence:
            fingerprinting_settings_changed = True
        server.config.set("fingerprinting", "confidence_threshold", float(fingerprinting_confidence))
    
    fingerprinting_max_threads = form.get('fingerprinting_max_threads')
    if fingerprinting_max_threads and fingerprinting_max_threads.isdigit() and 1 <= int(fingerprinting_max_threads) <= 20:
        original_max_threads = server.config.get("fingerprinting", "max_threads", default=10)
        if int(fingerprinting_max_threads) != original_max_threads:
            fingerprinting_settings_changed = True
        server.config.set("fingerprinting", "max_threads", int(fingerprinting_max_threads))
        
    fingerprinting_timeout = form.get('fingerprinting_timeout')
    if fingerprinting_timeout and fingerprinting_timeout.isdigit() and 1 <= int(fingerprinting_timeout) <= 10:
        original_timeout = server.config.get("fingerprinting", "timeout", default=2)
        if int(fingerprinting_timeout) != original_timeout:
            fingerprinting_settings_changed = True
        server.config.set("fingerprinting", "timeout", int(fingerprinting_timeout))
    
    # Telegram settings
    telegram_enabled = form.get('telegram_enabled') == 'on'
    server.config.set("telegram", "enabled", telegram_enabled)
    
    telegram_api_token = form.get('telegram_api_token')
    if telegram_api_token:
        server.config.set("telegram", "api_token", telegram_api_token)
    
    telegram_chat_id = form.get('telegram_chat_id')
    if telegram_chat_id:
        server.config.set("telegram", "chat_id", telegram_chat_id)
    
    # Internet health check settings
    internet_health_enabled = form.get('internet_health_enabled') == 'on'
    internet_health_interval = form.get('internet_health_interval')
    
    internet_health = server.config.get("monitoring", "internet_health", {})
    internet_health["enabled"] = internet_health_enabled
    
    if internet_health_interval and internet_health_interval.isdigit() and int(internet_health_interval) > 0:
        internet_health["interval"] = int(internet_health_interval)
    
    server.config.set("monitoring", "internet_health", internet_health)
    
    # Website monitoring settings
    websites_enabled = form.get('websites_enabled') == 'on'
    websites_interval = form.get('websites_interval')
    
    websites = server.config.get("monitoring", "websites", {})
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
    server.config.set("monitoring", "websites", websites)
    
    # Security scanning settings
    security_enabled = form.get('security_enabled') == 'on'
    security_interval = form.get('security_interval')
    
    security = server.config.get("monitoring", "security", {})
    security["enabled"] = security_enabled
    
    if security_interval and security_interval.isdigit() and int(security_interval) > 0:
        security["interval"] = int(security_interval)
    
    server.config.set("monitoring", "security", security)
    
    # Web interface settings
    web_host = form.get('web_host')
    if web_host:
        server.config.set("web_interface", "host", web_host)
    
    web_port = form.get('web_port')
    if web_port and web_port.isdigit() and 1024 <= int(web_port) <= 65535:
        server.config.set("web_interface", "port", int(web_port))
    
    # Authentication settings
    web_username = form.get('web_username')
    web_password = form.get('web_password')
    
    if web_username:
        server.config.set("web_interface", "username", web_username)
    
    if web_password:
        # Hash the password
        password_hash = hashlib.sha256(web_password.encode()).hexdigest()
        server.config.set("web_interface", "password_hash", password_hash)
        
    # Update monitoring threads if settings have changed and the main_app reference exists
    if server.main_app:
        current_settings = {
            "health_check": server.config.get("monitoring", "internet_health", {}).get("enabled", False),
            "website_monitoring": server.config.get("monitoring", "websites", {}).get("enabled", False),
            "security_scanning": server.config.get("monitoring", "security", {}).get("enabled", False)
        }
        
        # Check if any monitoring settings changed
        settings_changed = original_settings != current_settings
        
        # Also check if fingerprinting settings changed
        if fingerprinting_settings_changed:
            settings_changed = True
            
        if settings_changed:
            server.logger.info("Monitoring or fingerprinting settings changed, updating threads")
            server.main_app.update_monitoring_state()