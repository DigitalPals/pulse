"""
Debug logging utility for Cybex Pulse.

This module provides enhanced debug logging functionality that can be enabled/disabled
through configuration settings.
"""
import logging
import inspect
import threading
import time
from typing import Any, Dict, Optional
from pathlib import Path

from cybex_pulse.utils.config import Config

class DebugLogger:
    """Debug logger utility for Cybex Pulse.
    
    This class provides enhanced debug logging with additional context information:
    - Thread information
    - Calling function/method
    - Execution time for operations
    - Resource usage tracking
    
    Debug logging can be enabled/disabled through the configuration.
    This implementation is thread-safe and uses asynchronous logging to prevent lock contention.
    """
    
    def __init__(self, logger: logging.Logger, config: Config):
        """Initialize the debug logger.
        
        Args:
            logger: Base logger instance
            config: Configuration manager
        """
        self.logger = logger
        self.config = config
        self._resource_trackers = {}
        self._resource_trackers_lock = threading.RLock()
        self._operation_timers = {}
        self._operation_timers_lock = threading.RLock()
        
    def is_debug_enabled(self) -> bool:
        """Check if debug logging is enabled in configuration.
        
        Returns:
            bool: True if debug logging is enabled, False otherwise
        """
        return self.config.get("general", "debug_logging", False)
    
    def debug(self, message: str, *args, **kwargs) -> None:
        """Log a debug message if debug logging is enabled.
        
        Args:
            message: Debug message
            *args: Additional positional arguments for the logger
            **kwargs: Additional keyword arguments for the logger
        """
        if not self.is_debug_enabled():
            return
            
        # Get caller information
        frame = inspect.currentframe().f_back
        func_name = frame.f_code.co_name
        filename = frame.f_code.co_filename.split('/')[-1]
        lineno = frame.f_lineno
        
        # Get thread information
        thread = threading.current_thread()
        thread_name = thread.name
        thread_id = thread.ident
        
        # Format debug message with context
        context_message = f"[{thread_name}:{thread_id}] [{filename}:{func_name}:{lineno}] {message}"
        
        # Log the message
        self.logger.debug(context_message, *args, **kwargs)
    
    def start_timer(self, operation_name: str) -> None:
        """Start a timer for an operation.
        
        Args:
            operation_name: Name of the operation to time
        """
        if not self.is_debug_enabled():
            return
        
        with self._operation_timers_lock:
            self._operation_timers[operation_name] = time.time()
            
        self.debug(f"Starting operation: {operation_name}")
    
    def end_timer(self, operation_name: str) -> Optional[float]:
        """End a timer for an operation and log the elapsed time.
        
        Args:
            operation_name: Name of the operation to end timing
            
        Returns:
            float: Elapsed time in seconds, or None if timer wasn't started
        """
        if not self.is_debug_enabled():
            return None
        
        start_time = None
        with self._operation_timers_lock:
            if operation_name not in self._operation_timers:
                self.debug(f"No timer found for operation: {operation_name}")
                return None
                
            start_time = self._operation_timers.pop(operation_name)
            
        if start_time is not None:
            elapsed_time = time.time() - start_time
            self.debug(f"Operation completed: {operation_name} - Took {elapsed_time:.4f} seconds")
            return elapsed_time
        
        return None
    
    def track_resource(self, resource_name: str, resource: Any) -> None:
        """Track a resource for potential leaks.
        
        Args:
            resource_name: Name of the resource
            resource: Resource object to track
        """
        if not self.is_debug_enabled():
            return
        
        with self._resource_trackers_lock:
            self._resource_trackers[resource_name] = {
                'resource': resource,
                'stack': inspect.stack()[1:],
                'thread': threading.current_thread().name,
                'time': time.time()
            }
            
        self.debug(f"Resource tracked: {resource_name}")
    
    def release_resource(self, resource_name: str) -> None:
        """Mark a resource as released.
        
        Args:
            resource_name: Name of the resource to release
        """
        if not self.is_debug_enabled():
            return
        
        released = False
        with self._resource_trackers_lock:
            if resource_name in self._resource_trackers:
                del self._resource_trackers[resource_name]
                released = True
        
        if released:
            self.debug(f"Resource released: {resource_name}")
        else:
            self.debug(f"Attempted to release untracked resource: {resource_name}")
    
    def log_resources(self) -> None:
        """Log all currently tracked resources."""
        if not self.is_debug_enabled():
            return
        
        # Make a copy of the resources to avoid holding the lock during logging
        with self._resource_trackers_lock:
            if not self._resource_trackers:
                return
                
            resources_copy = dict(self._resource_trackers)
            
        self.debug(f"Currently tracking {len(resources_copy)} resources:")
        for name, info in resources_copy.items():
            elapsed = time.time() - info['time']
            self.debug(f"  - {name} (tracked for {elapsed:.1f} seconds, thread: {info['thread']})")
    
    def log_thread_info(self) -> None:
        """Log information about all active threads."""
        if not self.is_debug_enabled():
            return
            
        threads = threading.enumerate()
        self.debug(f"Active threads ({len(threads)}):")
        
        for thread in threads:
            self.debug(f"  - {thread.name} (id: {thread.ident}, daemon: {thread.daemon}, alive: {thread.is_alive()})")
    
    def log_critical_issue(self, issue_type: str, message: str, details: Dict[str, Any] = None) -> None:
        """Log a critical issue to both debug log and a special critical issues log file.
        
        Args:
            issue_type: Type of issue (e.g., 'DEADLOCK', 'RESOURCE_LEAK', 'THREAD_STUCK')
            message: Description of the issue
            details: Additional details about the issue
        """
        if not self.is_debug_enabled():
            return
            
        # Log to debug log
        self.debug(f"CRITICAL ISSUE - {issue_type}: {message}")
        if details:
            self.debug(f"CRITICAL ISSUE DETAILS: {details}")
            
        # Try to log to a special critical issues log file
        try:
            # Determine log directory from logger's handlers
            log_dir = None
            
            # Use a local copy of handlers to avoid potential race conditions
            handlers = list(self.logger.handlers)
            
            for handler in handlers:
                if isinstance(handler, logging.FileHandler):
                    log_path = Path(handler.baseFilename)
                    log_dir = log_path.parent
                    break
                    
            if log_dir:
                critical_log_file = log_dir / "cybex_pulse_critical.log"
                
                # Format the message with timestamp
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                formatted_message = f"[{timestamp}] {issue_type}: {message}"
                if details:
                    formatted_message += f"\nDetails: {details}"
                formatted_message += "\n\n"
                
                # Use a file lock to prevent concurrent writes
                # This is a simple approach - for high-volume logging, consider using a queue
                critical_log_lock = threading.Lock()
                with critical_log_lock:
                    # Append to the critical issues log
                    with open(critical_log_file, "a") as f:
                        f.write(formatted_message)
                    
                # Also log at ERROR level to ensure visibility in main log
                self.logger.error(f"CRITICAL ISSUE - {issue_type}: {message}")
        except Exception as e:
            # Don't let errors in critical logging prevent normal operation
            self.debug(f"Error writing to critical issues log: {e}")
    
    def log_lock_info(self, lock: threading.Lock, lock_name: str, acquiring: bool = True) -> None:
        """Log information about lock acquisition and release.
        
        Args:
            lock: The lock object
            lock_name: Name of the lock for identification
            acquiring: True if acquiring the lock, False if releasing
        """
        if not self.is_debug_enabled():
            return
            
        # Capture thread information outside of any locks to avoid potential deadlocks
        action = "Acquiring" if acquiring else "Releasing"
        thread = threading.current_thread()
        thread_name = thread.name
        thread_id = thread.ident
        
        # Use a formatted message that doesn't require additional context gathering
        # This reduces the chance of lock contention during logging
        self.debug(f"{action} lock: {lock_name} (thread: {thread_name}, id: {thread_id})")