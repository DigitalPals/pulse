"""
API routes for internet speed data.
"""


def register_speed_routes(app, server):
    """Register speed test API routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Get recent speed tests
    @app.route('/api/speed-tests')
    @server.login_required
    def api_speed_tests():
        # Return empty array if internet health checks are not enabled
        if not server.config.config.get("monitoring", {}).get("internet_health", {}).get("enabled", False):
            return server.jsonify([])
            
        limit = int(server.request.args.get('limit', 10))
        tests = server.db_manager.get_recent_speed_tests(limit)
        return server.jsonify(tests)