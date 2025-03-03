"""
Update routes for the web interface.
"""
import queue
import threading
from functools import wraps

def register_update_routes(app, server):
    """Register update routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    
    # Create a queue for update messages
    update_messages = queue.Queue()
    update_in_progress = threading.Event()
    
    def add_update_message(message, is_error=False):
        """Add a message to the update queue.
        
        Args:
            message: Message to add
            is_error: Whether the message is an error
        """
        update_messages.put({
            "message": message,
            "is_error": is_error
        })
    
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
            
        # Clear any existing messages and set update in progress
        while not update_messages.empty():
            update_messages.get()
        update_in_progress.set()
        
        # Start update in a separate thread to not block the response
        def run_update():
            try:
                # Perform update with progress callback
                success, message = server.main_app.update_application(add_update_message)
                
                if not success:
                    add_update_message(f"Update failed: {message}", is_error=True)
                
                # Clear update in progress flag when done
                update_in_progress.clear()
            except Exception as e:
                add_update_message(f"Error during update: {str(e)}", is_error=True)
                update_in_progress.clear()
        
        # Start update thread
        update_thread = threading.Thread(target=run_update)
        update_thread.daemon = True
        update_thread.start()
        
        return server.jsonify({"success": True, "message": "Update started"})
    
    @app.route('/update-stream')
    @server.login_required
    def update_stream():
        """Stream update progress as server-sent events."""
        if not hasattr(server, 'Response') or not hasattr(server, 'stream_with_context'):
            # Import Flask's streaming response if not already available
            from flask import Response, stream_with_context
            server.Response = Response
            server.stream_with_context = stream_with_context
        
        def generate():
            """Generate SSE events."""
            # Send initial message
            yield "event: message\ndata: {\"message\": \"Connecting to update stream...\"}\n\n"
            
            # Check if update is in progress
            if not update_in_progress.is_set():
                yield "event: message\ndata: {\"message\": \"No update in progress\", \"is_error\": true}\n\n"
                return
            
            # Send messages from queue
            while update_in_progress.is_set() or not update_messages.empty():
                try:
                    # Try to get a message with timeout
                    message = update_messages.get(timeout=1.0)
                    
                    # Format as SSE event
                    if message.get("is_error", False):
                        yield f"event: error\ndata: {server.json.dumps(message)}\n\n"
                    else:
                        yield f"event: message\ndata: {server.json.dumps(message)}\n\n"
                    
                except queue.Empty:
                    # Send heartbeat to keep connection alive
                    yield ": heartbeat\n\n"
            
            # Send completion message
            yield "event: complete\ndata: {\"message\": \"Update process completed\"}\n\n"
        
        return server.Response(
            server.stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # Disable buffering for Nginx
            }
        )
    
    @app.route('/update-status')
    @server.login_required
    def update_status():
        """Get the current update status."""
        return server.jsonify({
            "in_progress": update_in_progress.is_set()
        })
    
    @app.route('/update-page')
    @server.login_required
    def update_page():
        """Display the update streaming page."""
        return server.render_template(
            'update_stream.html',
            update_available=server.main_app and server.main_app.update_checker.update_available,
            update_disabled=server.main_app and hasattr(server.main_app.update_checker, 'current_commit_hash') and
                            server.main_app.update_checker.current_commit_hash and
                            (server.main_app.update_checker.current_commit_hash.startswith("install-") or
                             server.main_app.update_checker.current_commit_hash == "unknown")
        )