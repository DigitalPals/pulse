"""
Update routes for the web interface.
"""

def register_update_routes(app, server):
    """Register update routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    
    @app.route('/check-update')
    @server.login_required
    def check_update():
        """Check for updates manually."""
        if not server.main_app:
            return server.jsonify({"error": "Main application not available"}), 500
            
        # Force check for updates
        update_available, error = server.main_app.update_checker.check_for_updates()
        
        if error:
            return server.jsonify({"error": error}), 500
            
        return server.jsonify({
            "update_available": update_available,
            "current_commit": server.main_app.update_checker.current_commit_hash,
            "latest_commit": server.main_app.update_checker.latest_commit_hash
        })
    
    @app.route('/perform-update')
    @server.login_required
    def perform_update():
        """Perform application update."""
        if not server.main_app:
            return server.jsonify({"error": "Main application not available"}), 500
            
        # Perform update
        success, message = server.main_app.update_application()
        
        if not success:
            return server.jsonify({"error": message}), 500
            
        return server.jsonify({"success": True, "message": message})