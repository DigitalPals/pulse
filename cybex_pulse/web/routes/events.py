"""
Event routes for the web interface.
"""
import time


def register_events_routes(app, server):
    """Register event routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Events route
    @app.route('/events')
    @server.login_required
    def events():
        limit = int(server.request.args.get('limit', 100))
        event_type = server.request.args.get('type')
        severity = server.request.args.get('severity')
        
        events = server.db_manager.get_recent_events(limit, event_type, severity)
        
        # Add current timestamp for template
        now = int(time.time())
        
        return server.render_template('events.html', events=events, now=now)