"""
Console routes for the web interface.
"""
import queue
import threading
import time
import logging
import sys
import io
from functools import wraps
from cybex_pulse.utils.system_info import get_all_system_info, get_cpu_info, get_memory_info

class ConsoleStreamHandler(logging.Handler):
    """Custom logging handler that puts logs into a queue for streaming."""
    
    def __init__(self, message_queue):
        """Initialize the handler with a queue.
        
        Args:
            message_queue: Queue to store log messages
        """
        super().__init__()
        self.message_queue = message_queue
        
    def emit(self, record):
        """Put the log record into the queue.
        
        Args:
            record: Log record to process
        """
        try:
            # Format the record
            msg = self.format(record)
            
            # Add to queue with error flag based on level
            self.message_queue.put({
                "message": msg,
                "is_error": record.levelno >= logging.ERROR
            })
        except Exception:
            self.handleError(record)

class StreamToQueue(io.TextIOBase):
    """Redirect stdout/stderr to a queue."""
    
    def __init__(self, message_queue, is_error=False):
        """Initialize with a queue.
        
        Args:
            message_queue: Queue to store output
            is_error: Whether this stream represents stderr
        """
        self.message_queue = message_queue
        self.is_error = is_error
        self.buffer = ""
        
    def write(self, text):
        """Write text to the queue.
        
        Args:
            text: Text to write
        """
        if text:
            # Buffer until we get a newline
            self.buffer += text
            
            # Process complete lines
            if '\n' in self.buffer:
                lines = self.buffer.split('\n')
                # Keep the last part if it doesn't end with newline
                self.buffer = lines.pop() if self.buffer[-1] != '\n' else ""
                
                # Add complete lines to queue
                for line in lines:
                    if line:  # Skip empty lines
                        self.message_queue.put({
                            "message": line,
                            "is_error": self.is_error
                        })
        return len(text)
        
    def flush(self):
        """Flush the buffer."""
        if self.buffer:
            self.message_queue.put({
                "message": self.buffer,
                "is_error": self.is_error
            })
            self.buffer = ""

def register_console_routes(app, server):
    """Register console routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    
    # Create a queue for console messages
    console_messages = queue.Queue(maxsize=1000)  # Limit queue size to prevent memory issues
    
    # Set up logging handler
    console_handler = ConsoleStreamHandler(console_messages)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    
    # Store original stdout and stderr but don't redirect globally
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    
    # Create stream redirectors but don't apply them globally
    stdout_redirector = StreamToQueue(console_messages, is_error=False)
    stderr_redirector = StreamToQueue(console_messages, is_error=True)
    
    # We'll use these in a context manager when needed, not globally
    
    @app.route('/console')
    @server.login_required
    def console_page():
        """Display the console page."""
        # Use placeholder values for initial page load
        # All real data will be loaded asynchronously via AJAX to prevent page load delays
        system_info = {
            "cpu": {"percent": 0, "count": 1, "model": "Loading..."},
            "memory": {"percent": 0, "used": 0, "total": 100},
            "disk": {"percent": 0, "used": 0, "total": 100}
        }
        
        return server.render_template('console.html', system_info=system_info)
    
    @app.route('/console-stream')
    @server.login_required
    def console_stream():
        """Stream console output as server-sent events."""
        if not hasattr(server, 'Response') or not hasattr(server, 'stream_with_context'):
            # Import Flask's streaming response if not already available
            from flask import Response, stream_with_context
            server.Response = Response
            server.stream_with_context = stream_with_context
        
        # Create a context manager for stdout/stderr redirection
        class RedirectStdStreams:
            def __init__(self, stdout=None, stderr=None):
                self._stdout = stdout or sys.stdout
                self._stderr = stderr or sys.stderr

            def __enter__(self):
                self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
                self.old_stdout.flush(); self.old_stderr.flush()
                sys.stdout, sys.stderr = self._stdout, self._stderr
                return self

            def __exit__(self, exc_type, exc_value, traceback):
                self._stdout.flush(); self._stderr.flush()
                sys.stdout = self.old_stdout
                sys.stderr = self.old_stderr
        
        def generate():
            """Generate SSE events."""
            try:
                # Send initial message
                yield "event: message\ndata: {\"message\": \"Connected to Cybex Pulse console stream. Showing real-time output.\"}\n\n"
                
                # Temporarily redirect stdout/stderr only for this stream
                with RedirectStdStreams(stdout=stdout_redirector, stderr=stderr_redirector):
                    # Send messages from queue
                    while True:
                        try:
                            # Try to get a message with timeout
                            message = console_messages.get(timeout=1.0)
                            
                            # Format as SSE event
                            if message.get("is_error", False):
                                yield f"event: message\ndata: {server.json.dumps(message)}\n\n"
                            else:
                                yield f"event: message\ndata: {server.json.dumps(message)}\n\n"
                            
                        except queue.Empty:
                            # Send heartbeat to keep connection alive
                            yield ": heartbeat\n\n"
            except Exception as e:
                # Log the error
                server.logger.error(f"Error in console stream: {str(e)}")
                # Send error to client
                yield f"event: message\ndata: {{\"message\": \"Server error: {str(e)}\", \"is_error\": true}}\n\n"
        
        return server.Response(
            server.stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'  # Disable buffering for Nginx
            }
        )
    
    # Add a cleanup function to remove the logger handler
    def cleanup():
        """Clean up console resources."""
        # We don't need to restore stdout/stderr since we're using a context manager
        # Just remove the logger handler
        root_logger.removeHandler(console_handler)
        
        # Clear the message queue to prevent memory leaks
        try:
            while not console_messages.empty():
                console_messages.get_nowait()
        except Exception:
            pass
    
    # Register cleanup with server
    if hasattr(server, 'cleanup_functions'):
        server.cleanup_functions.append(cleanup)
    else:
        server.cleanup_functions = [cleanup]