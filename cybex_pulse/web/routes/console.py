"""
Console routes for the web interface.

This module provides routes for the system console, which displays real-time
system information and log output. It includes functionality for streaming
logs and system output via Server-Sent Events (SSE).
"""
import queue
import logging
import sys
import io
import time
import threading
from flask import Response, stream_with_context
from cybex_pulse.utils.system_info import get_all_system_info

# Constants for console configuration
MAX_QUEUE_SIZE = 1000  # Maximum number of messages in queue
LOG_LEVEL = logging.INFO
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
HEARTBEAT_INTERVAL = 1.0  # Seconds between heartbeats
CONSOLE_STREAM_TIMEOUT = 60 * 60  # 1 hour max stream time

# Create a thread-local storage for stream resources
thread_local = threading.local()

class RedirectStdStreams:
    """Context manager for redirecting stdout/stderr streams."""
    
    def __init__(self, stdout=None, stderr=None):
        """Initialize with output streams.
        
        Args:
            stdout: Stream to redirect stdout to
            stderr: Stream to redirect stderr to
        """
        self._stdout = stdout or sys.stdout
        self._stderr = stderr or sys.stderr

    def __enter__(self):
        """Redirect streams when entering context."""
        self.old_stdout, self.old_stderr = sys.stdout, sys.stderr
        self.old_stdout.flush(); self.old_stderr.flush()
        sys.stdout, sys.stderr = self._stdout, self._stderr
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Restore original streams when exiting context."""
        self._stdout.flush(); self._stderr.flush()
        sys.stdout = self.old_stdout
        sys.stderr = self.old_stderr


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
            
            # Determine message type based on log level
            msg_type = "error" if record.levelno >= logging.ERROR else \
                      "warning" if record.levelno >= logging.WARNING else "info"
            
            # Add to queue with type information
            self.message_queue.put({
                "message": msg,
                "is_error": record.levelno >= logging.ERROR,
                "type": msg_type,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
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
        if not text:
            return 0
            
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
                    msg_type = "error" if self.is_error else "info"
                    self.message_queue.put({
                        "message": line,
                        "is_error": self.is_error,
                        "type": msg_type,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
        return len(text)
        
    def flush(self):
        """Flush the buffer."""
        if self.buffer:
            msg_type = "error" if self.is_error else "info"
            self.message_queue.put({
                "message": self.buffer,
                "is_error": self.is_error,
                "type": msg_type,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            })
            self.buffer = ""


def setup_console_resources():
    """Set up and return console streaming resources.
    
    Returns:
        tuple: (message_queue, console_handler, stdout_redirector, stderr_redirector)
    """
    # Create a queue for console messages
    message_queue = queue.Queue(maxsize=MAX_QUEUE_SIZE)
    
    # Set up logging handler
    console_handler = ConsoleStreamHandler(message_queue)
    console_handler.setLevel(LOG_LEVEL)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(console_handler)
    
    # Create stream redirectors
    stdout_redirector = StreamToQueue(message_queue, is_error=False)
    stderr_redirector = StreamToQueue(message_queue, is_error=True)
    
    return message_queue, console_handler, stdout_redirector, stderr_redirector


def cleanup_console_resources(console_handler):
    """Clean up console resources.
    
    Args:
        console_handler: The logging handler to remove
    """
    # Remove the logger handler
    root_logger = logging.getLogger()
    if console_handler in root_logger.handlers:
        root_logger.removeHandler(console_handler)


def format_sse_event(event_type, data):
    """Format a server-sent event.
    
    Args:
        event_type: Type of event
        data: Data to send
        
    Returns:
        str: Formatted SSE event
    """
    return f"event: {event_type}\ndata: {data}\n\n"


def register_console_routes(app, server):
    """Register console routes with the Flask application.
    
    Args:
        app: Flask application instance
        server: WebServer instance
    """
    # Set up shared resources
    message_queue, console_handler, stdout_redirector, stderr_redirector = setup_console_resources()
    
    @app.route('/console-test')
    def console_test_page():
        """Display the console test page."""
        return app.send_static_file('console-test.html')
    
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
        server.logger.info("Console stream requested")
        
        # Store start time to enforce maximum stream duration
        start_time = time.time()
        
        def generate():
            """Generate SSE events."""
            try:
                server.logger.info("Starting console stream generation")
                
                # Send initial message
                initial_message = {
                    "message": "Connected to Cybex Pulse console stream. Showing real-time output.",
                    "type": "info",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                server.logger.info("Sending initial message")
                yield format_sse_event("message", server.json.dumps(initial_message))
                
                # Temporarily redirect stdout/stderr only for this stream
                with RedirectStdStreams(stdout=stdout_redirector, stderr=stderr_redirector):
                    # Send messages from queue
                    while True:
                        # Check if we've exceeded the maximum stream time
                        if time.time() - start_time > CONSOLE_STREAM_TIMEOUT:
                            timeout_message = {
                                "message": "Console stream timeout reached. Please refresh to reconnect.",
                                "is_error": True,
                                "type": "warning",
                                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                            }
                            yield format_sse_event("message", server.json.dumps(timeout_message))
                            break
                            
                        try:
                            # Try to get a message with timeout
                            message = message_queue.get(timeout=HEARTBEAT_INTERVAL)
                            server.logger.debug(f"Got message from queue: {message}")
                            
                            # Format as SSE event
                            formatted_event = format_sse_event("message", server.json.dumps(message))
                            server.logger.debug(f"Sending SSE event: {formatted_event}")
                            yield formatted_event
                            
                        except queue.Empty:
                            # Send heartbeat to keep connection alive
                            server.logger.debug("Queue empty, sending heartbeat")
                            yield ": heartbeat\n\n"
            except Exception as e:
                # Log the error
                server.logger.error(f"Error in console stream: {str(e)}", exc_info=True)
                # Send error to client
                error_message = {
                    "message": f"Server error: {str(e)}",
                    "is_error": True,
                    "type": "error",
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                }
                server.logger.info(f"Sending error message to client: {error_message}")
                yield format_sse_event("message", server.json.dumps(error_message))
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',  # Disable buffering for Nginx
                'Access-Control-Allow-Origin': '*',  # Allow cross-origin requests
                'Access-Control-Allow-Headers': 'Content-Type',
                'Access-Control-Allow-Methods': 'GET'
            }
        )
    
    # Add a cleanup function to remove the logger handler
    def cleanup():
        """Clean up console resources."""
        cleanup_console_resources(console_handler)
        
        # Clear the message queue to prevent memory leaks
        try:
            while not message_queue.empty():
                message_queue.get_nowait()
        except Exception:
            pass
    
    # Register cleanup with server
    if hasattr(server, 'cleanup_functions'):
        server.cleanup_functions.append(cleanup)
    else:
        server.cleanup_functions = [cleanup]