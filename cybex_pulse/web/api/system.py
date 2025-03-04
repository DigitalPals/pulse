"""
System information API endpoints.
"""
import logging
import time
from cybex_pulse.utils.system_info import get_all_system_info, get_cpu_info, get_memory_info, get_disk_info

logger = logging.getLogger("cybex_pulse.api.system")

# Cache system information to reduce load
_system_info_cache = {}
_last_update_time = 0
_CACHE_TTL = 2  # Cache TTL in seconds

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
        global _system_info_cache, _last_update_time
        
        try:
            current_time = time.time()
            
            # Check if we have a recent cache
            if current_time - _last_update_time <= _CACHE_TTL and _system_info_cache:
                return server.jsonify(_system_info_cache)
            
            # Get system information
            system_info = get_all_system_info()
            
            # Update cache
            _system_info_cache = system_info
            _last_update_time = current_time
            
            # Return as JSON
            return server.jsonify(system_info)
        except Exception as e:
            logger.error(f"Error getting system information: {str(e)}")
            return server.jsonify({
                "error": str(e)
            }), 500
    
    @app.route('/api/system-info/cpu')
    @server.login_required
    def api_cpu_info():
        """Get CPU information only.
        
        Returns:
            JSON response with CPU information
        """
        try:
            # Get CPU information only
            cpu_info = get_cpu_info()
            
            # Return as JSON
            return server.jsonify(cpu_info)
        except Exception as e:
            logger.error(f"Error getting CPU information: {str(e)}")
            return server.jsonify({
                "error": str(e)
            }), 500
    
    @app.route('/api/system-info/memory')
    @server.login_required
    def api_memory_info():
        """Get memory information only.
        
        Returns:
            JSON response with memory information
        """
        try:
            # Get memory information only
            memory_info = get_memory_info()
            
            # Return as JSON
            return server.jsonify(memory_info)
        except Exception as e:
            logger.error(f"Error getting memory information: {str(e)}")
            return server.jsonify({
                "error": str(e)
            }), 500
    
    @app.route('/api/system-info/disk')
    @server.login_required
    def api_disk_info():
        """Get disk information only.
        
        Returns:
            JSON response with disk information
        """
        try:
            # Get disk information only
            disk_info = get_disk_info()
            
            # Return as JSON
            return server.jsonify(disk_info)
        except Exception as e:
            logger.error(f"Error getting disk information: {str(e)}")
            return server.jsonify({
                "error": str(e)
            }), 500