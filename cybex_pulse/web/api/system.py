"""
System information API endpoints.
"""
import logging
from cybex_pulse.utils.system_info import get_all_system_info

logger = logging.getLogger("cybex_pulse.api.system")

def register_system_api(app, server):
    """Register system API endpoints with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    
    @app.route('/api/system-info')
    @server.login_required
    def api_system_info():
        """Get system information.
        
        Returns:
            JSON response with system information
        """
        try:
            # Get system information
            system_info = get_all_system_info()
            
            # Return as JSON
            return server.jsonify(system_info)
        except Exception as e:
            logger.error(f"Error getting system information: {str(e)}")
            return server.jsonify({
                "error": str(e)
            }), 500