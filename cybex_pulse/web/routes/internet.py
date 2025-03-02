"""
Internet monitoring routes for the web interface.
"""
import time


def register_internet_routes(app, server):
    """Register internet monitoring routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Speed tests route
    @app.route('/speed-tests')
    @server.login_required
    def speed_tests():
        # Redirect to dashboard if internet health checks are not enabled
        if not server.config.config.get("monitoring", {}).get("internet_health", {}).get("enabled", False):
            server.flash('Internet health monitoring is not enabled')
            return server.redirect(server.url_for('dashboard'))
            
        tests = server.db_manager.get_recent_speed_tests()
        
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
        
        return server.render_template('speed_tests.html', tests=tests,
                                   avg_download=avg_download,
                                   avg_upload=avg_upload,
                                   avg_ping=avg_ping,
                                   max_download=max_download,
                                   max_upload=max_upload,
                                   min_ping=min_ping,
                                   now=now)
    
    # Website checks route
    @app.route('/websites')
    @server.login_required
    def websites():
        # Redirect to dashboard if website monitoring is not enabled
        if not server.config.config.get("monitoring", {}).get("websites", {}).get("enabled", False):
            server.flash('Website monitoring is not enabled')
            return server.redirect(server.url_for('dashboard'))
            
        checks = server.db_manager.get_website_checks()
        
        # Get configured website URLs from config
        configured_urls = server.config.config.get("monitoring", {}).get("websites", {}).get("urls", [])
        
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
        
        return server.render_template('websites.html', websites=websites, checks=checks, now=now)
        
    # Website history route
    @app.route('/websites/history/<path:url>')
    @server.login_required
    def website_history(url):
        # Redirect to dashboard if website monitoring is not enabled
        if not server.config.config.get("monitoring", {}).get("websites", {}).get("enabled", False):
            server.flash('Website monitoring is not enabled')
            return server.redirect(server.url_for('dashboard'))
            
        # Get checks for the specific URL
        checks = server.db_manager.get_website_checks(url=url, limit=100)
        
        if not checks:
            server.flash(f'No history found for {url}')
            return server.redirect(server.url_for('websites'))
        
        # Prepare data for response time chart
        timestamps = []
        response_times = []
        
        for check in checks:
            if check['timestamp'] and check['response_time']:
                timestamps.append(server.app.jinja_env.filters['timestamp_to_time'](check['timestamp']))
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
        
        return server.render_template('websites.html',
                                   checks=checks,
                                   now=now,
                                   response_times=response_times_data,
                                   website_url=url)