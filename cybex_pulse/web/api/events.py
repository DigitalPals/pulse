"""
API routes for event data.
"""


def register_event_routes(app, server):
    """Register event API routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Get recent events
    @app.route('/api/events')
    @server.login_required
    def api_events():
        limit = int(server.request.args.get('limit', 100))
        event_type = server.request.args.get('type')
        severity = server.request.args.get('severity')
        
        events = server.db_manager.get_recent_events(limit, event_type, severity)
        return server.jsonify(events)