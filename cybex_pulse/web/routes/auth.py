"""
Authentication routes for the web interface.
"""


def register_auth_routes(app, server):
    """Register authentication routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Login route
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        # If not configured, redirect to setup wizard
        if not server.config.is_configured():
            return server.redirect(server.url_for('setup_wizard'))
            
        if server.request.method == 'POST':
            username = server.request.form.get('username')
            password = server.request.form.get('password')
            
            if server._check_credentials(username, password):
                server.session['logged_in'] = True
                return server.redirect(server.url_for('dashboard'))
            else:
                server.flash('Invalid credentials')
        
        return server.render_template('login.html')
    
    # Logout route
    @app.route('/logout')
    def logout():
        server.session.pop('logged_in', None)
        return server.redirect(server.url_for('login'))