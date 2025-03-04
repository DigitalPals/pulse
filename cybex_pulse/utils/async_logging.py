"""
Asynchronous logging module for Cybex Pulse.

This module provides thread-safe logging functionality using QueueHandler and QueueListener
to offload logging operations to a dedicated thread, preventing lock contention in
multi-threaded environments.
"""
import atexit
import logging
import logging.handlers
import queue
import threading
from typing import Dict, List, Optional, Any, Union

# Constants
DEFAULT_QUEUE_SIZE = 10000  # Maximum number of log records in queue
QUEUE_TIMEOUT = 0.1  # Timeout for queue operations in seconds


class AsyncLogManager:
    """
    Manages asynchronous logging using QueueHandler and QueueListener.
    
    This class provides a centralized way to set up and manage asynchronous logging,
    which helps prevent lock contention in multi-threaded applications.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        """Implement singleton pattern for AsyncLogManager."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AsyncLogManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        """Initialize the async log manager if not already initialized."""
        if self._initialized:
            return
            
        self._initialized = True
        self.log_queue = queue.Queue(maxsize=DEFAULT_QUEUE_SIZE)
        self.listener = None
        self.queue_handler = None
        self.werkzeug_queue_handler = None
        self.is_setup = False
        self.original_handlers = {}
        self.werkzeug_logger_patched = False
    
    def setup_async_logging(self, loggers: List[Union[str, logging.Logger]] = None) -> None:
        """
        Set up asynchronous logging for the specified loggers.
        
        Args:
            loggers: List of logger names or logger objects to set up async logging for.
                    If None, sets up async logging for the root logger.
        """
        # Use a lock to ensure thread safety during setup
        with self._lock:
            if self.is_setup:
                return
                
            try:
                # Create a QueueHandler that sends log records to the queue
                self.queue_handler = logging.handlers.QueueHandler(self.log_queue)
                
                # Get the loggers to set up
                logger_objects = []
                if loggers is None:
                    # Use root logger if no loggers specified
                    logger_objects = [logging.getLogger()]
                else:
                    for logger in loggers:
                        if isinstance(logger, str):
                            logger_objects.append(logging.getLogger(logger))
                        else:
                            logger_objects.append(logger)
                
                # Store original handlers and replace with queue handler
                for logger in logger_objects:
                    # Make a copy of the handlers to avoid modification during iteration
                    self.original_handlers[logger.name] = list(logger.handlers)
                    
                    # Remove all handlers and add the queue handler
                    for handler in list(logger.handlers):
                        logger.removeHandler(handler)
                        
                    logger.addHandler(self.queue_handler)
                
                # Create a listener that consumes log records from the queue
                # and dispatches them to the original handlers
                handlers = []
                for logger_handlers in self.original_handlers.values():
                    handlers.extend(logger_handlers)
                    
                # Remove duplicates while preserving order
                unique_handlers = []
                handler_ids = set()
                for handler in handlers:
                    handler_id = id(handler)
                    if handler_id not in handler_ids:
                        handler_ids.add(handler_id)
                        unique_handlers.append(handler)
                
                # Create and start the queue listener
                self.listener = logging.handlers.QueueListener(
                    self.log_queue,
                    *unique_handlers,
                    respect_handler_level=True
                )
                self.listener.start()
                
                # Register cleanup function to stop the listener on exit
                atexit.register(self.cleanup)
                
                self.is_setup = True
            except Exception as e:
                # If setup fails, log the error and continue with standard logging
                import sys
                print(f"Error setting up async logging: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                
                # Try to restore original handlers if possible
                try:
                    for logger_name, handlers in self.original_handlers.items():
                        logger = logging.getLogger(logger_name)
                        # Remove queue handler if it was added
                        if self.queue_handler in logger.handlers:
                            logger.removeHandler(self.queue_handler)
                        # Restore original handlers
                        for handler in handlers:
                            if handler not in logger.handlers:
                                logger.addHandler(handler)
                except Exception:
                    # Last resort - just make sure root logger has a handler
                    root = logging.getLogger()
                    if not root.handlers:
                        root.addHandler(logging.StreamHandler(sys.stderr))
    
    def patch_werkzeug_logger(self) -> None:
        """
        Patch the Werkzeug logger to use async logging.
        
        This is important because Werkzeug creates a lot of logging contention
        with many simultaneous web requests.
        """
        # Use a lock to ensure thread safety during patching
        with self._lock:
            if self.werkzeug_logger_patched:
                return
                
            try:
                # Create a separate queue handler for Werkzeug
                werkzeug_queue = queue.Queue(maxsize=DEFAULT_QUEUE_SIZE)
                self.werkzeug_queue_handler = logging.handlers.QueueHandler(werkzeug_queue)
                
                # Get the Werkzeug logger
                werkzeug_logger = logging.getLogger('werkzeug')
                
                # Store original handlers
                werkzeug_handlers = list(werkzeug_logger.handlers)
                
                # If no handlers, add a default one to ensure logs are captured
                if not werkzeug_handlers:
                    import sys
                    default_handler = logging.StreamHandler(sys.stdout)
                    default_handler.setFormatter(logging.Formatter(
                        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                    ))
                    werkzeug_handlers = [default_handler]
                
                # Remove all handlers and add the queue handler
                for handler in list(werkzeug_logger.handlers):
                    werkzeug_logger.removeHandler(handler)
                    
                werkzeug_logger.addHandler(self.werkzeug_queue_handler)
                
                # Create and start a separate queue listener for Werkzeug
                self.werkzeug_listener = logging.handlers.QueueListener(
                    werkzeug_queue,
                    *werkzeug_handlers,
                    respect_handler_level=True
                )
                self.werkzeug_listener.start()
                
                # Set the flag to indicate successful patching
                self.werkzeug_logger_patched = True
            except Exception as e:
                # If patching fails, log the error and continue with standard logging
                import sys
                print(f"Error patching Werkzeug logger: {e}", file=sys.stderr)
                import traceback
                traceback.print_exc(file=sys.stderr)
                
                # Make sure Werkzeug logger has at least one handler
                try:
                    werkzeug_logger = logging.getLogger('werkzeug')
                    if not werkzeug_logger.handlers:
                        werkzeug_logger.addHandler(logging.StreamHandler(sys.stdout))
                except Exception:
                    pass
    
    def cleanup(self) -> None:
        """Clean up resources and stop the queue listener."""
        with self._lock:
            # Stop the main listener
            if self.listener:
                try:
                    self.listener.stop()
                except Exception as e:
                    import sys
                    print(f"Error stopping log listener: {e}", file=sys.stderr)
                finally:
                    self.listener = None
                
            # Stop the Werkzeug listener if it exists
            if hasattr(self, 'werkzeug_listener') and self.werkzeug_listener:
                try:
                    self.werkzeug_listener.stop()
                except Exception as e:
                    import sys
                    print(f"Error stopping Werkzeug log listener: {e}", file=sys.stderr)
                finally:
                    self.werkzeug_listener = None
            
            # Restore original handlers if possible
            try:
                for logger_name, handlers in self.original_handlers.items():
                    logger = logging.getLogger(logger_name)
                    
                    # Remove queue handler if it was added
                    if self.queue_handler and self.queue_handler in logger.handlers:
                        logger.removeHandler(self.queue_handler)
                    
                    # Restore original handlers
                    for handler in handlers:
                        if handler not in logger.handlers:
                            logger.addHandler(handler)
            except Exception as e:
                import sys
                print(f"Error restoring original log handlers: {e}", file=sys.stderr)
            
            # Clear the queue to prevent memory leaks
            try:
                while not self.log_queue.empty():
                    self.log_queue.get_nowait()
                    self.log_queue.task_done()
            except Exception:
                # Ignore errors in queue cleanup
                pass
                
            # Reset state
            self.is_setup = False
            self.werkzeug_logger_patched = False
            self.queue_handler = None
            self.original_handlers = {}


class ThreadSafeConsoleStreamHandler(logging.Handler):
    """
    Thread-safe version of ConsoleStreamHandler that uses a queue internally.
    
    This handler is designed to be used with the console streaming functionality
    while avoiding lock contention.
    """
    
    def __init__(self, message_queue):
        """
        Initialize the handler with a queue.
        
        Args:
            message_queue: Queue to store log messages
        """
        super().__init__()
        self.message_queue = message_queue
        self._local_queue = queue.Queue()
        self._worker = threading.Thread(
            target=self._queue_worker,
            name="ConsoleStreamHandlerWorker",
            daemon=True
        )
        self._worker.start()
        
    def emit(self, record):
        """
        Put the log record into the local queue for processing by the worker thread.
        
        Args:
            record: Log record to process
        """
        try:
            # Put the record in the local queue for async processing
            self._local_queue.put(record)
        except Exception:
            self.handleError(record)
    
    def _queue_worker(self):
        """Worker thread that processes log records from the local queue."""
        import time
        import sys
        import traceback
        
        while True:
            try:
                # Get a record from the local queue
                record = self._local_queue.get(timeout=QUEUE_TIMEOUT)
                
                try:
                    # Format the record
                    msg = self.format(record)
                    
                    # Determine message type based on log level
                    msg_type = "error" if record.levelno >= logging.ERROR else \
                              "warning" if record.levelno >= logging.WARNING else "info"
                    
                    # Add to the message queue with type information
                    self.message_queue.put({
                        "message": msg,
                        "is_error": record.levelno >= logging.ERROR,
                        "type": msg_type,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                except Exception as e:
                    # Handle error but don't crash the worker thread
                    try:
                        self.handleError(record)
                    except Exception:
                        # Last resort error handling
                        print(f"Critical error in console stream handler: {e}", file=sys.stderr)
                        traceback.print_exc(file=sys.stderr)
                finally:
                    try:
                        self._local_queue.task_done()
                    except Exception:
                        # Ignore errors in task_done
                        pass
            except queue.Empty:
                # No records to process, continue waiting
                continue
            except Exception as e:
                # Log but don't crash the worker thread
                print(f"Error in console stream handler worker: {e}", file=sys.stderr)
                traceback.print_exc(file=sys.stderr)
                
                # Brief sleep to avoid tight loop in case of persistent errors
                try:
                    time.sleep(0.1)
                except Exception:
                    pass


# Create a singleton instance
async_log_manager = AsyncLogManager()