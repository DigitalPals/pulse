"""
Thread management module for Cybex Pulse.

This module provides centralized thread management functionality:
- Creating and managing daemon threads
- Graceful thread termination
- Thread lifecycle monitoring
- Thread status reporting
- Deadlock prevention and detection
- Resource tracking
"""
import logging
import threading
import time
import weakref
from typing import Any, Callable, Dict, List, Optional, Set

from cybex_pulse.utils.debug_logger import DebugLogger


class ThreadManager:
    """Centralized thread management for Cybex Pulse.
    
    This class provides a unified interface for:
    - Creating and starting threads
    - Stopping threads gracefully
    - Monitoring thread status
    - Managing thread lifecycle
    - Deadlock prevention and detection
    - Resource tracking
    """
    
    def __init__(self, logger: logging.Logger, config=None):
        """Initialize the thread manager.
        
        Args:
            logger: Logger instance
            config: Configuration manager (optional)
        """
        self.logger = logger
        self.config = config
        self.threads = []
        self.thread_stop_events = {}
        self.global_stop_event = threading.Event()
        
        # Thread pool management
        self.max_threads = 20  # Default maximum number of threads
        self.active_thread_count = 0
        self.thread_pool_lock = threading.Lock()
        
        # Deadlock prevention
        self.thread_locks = {}  # Track locks held by each thread
        self.lock_owners = {}   # Track which thread owns each lock
        self.lock_wait_graph = {}  # Track which threads are waiting for which locks
        self.deadlock_check_lock = threading.Lock()
        
        # Resource tracking
        self.resources = weakref.WeakValueDictionary()  # Track resources that should be closed
        
        # Debug logger
        self.debug = None
        if config:
            self.debug = DebugLogger(logger, config)
    
    def create_thread(self, name: str, target: Callable, args: tuple = ()) -> threading.Thread:
        """Create a new daemon thread.
        
        Args:
            name: Thread name
            target: Thread target function
            args: Arguments to pass to the target function
            
        Returns:
            threading.Thread: Created thread
        """
        # Wrap the target function to include debug logging and resource tracking
        def wrapped_target(*target_args):
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Thread started: {name}")
                self.debug.start_timer(f"thread_{name}")
                
                try:
                    with self.thread_pool_lock:
                        self.active_thread_count += 1
                        
                    if self.debug:
                        self.debug.debug(f"Active thread count: {self.active_thread_count}")
                        
                    # Call the original target function
                    return target(*target_args)
                finally:
                    with self.thread_pool_lock:
                        self.active_thread_count -= 1
                        
                    if self.debug:
                        self.debug.debug(f"Thread completed: {name}")
                        self.debug.debug(f"Active thread count: {self.active_thread_count}")
                        self.debug.end_timer(f"thread_{name}")
                        self.debug.log_resources()
            else:
                # If debug logging is disabled, just call the target function
                return target(*target_args)
                
        thread = threading.Thread(
            target=wrapped_target,
            name=name,
            args=args,
            daemon=True
        )
        return thread
    
    def start_thread(self, name: str, target: Callable, args: tuple = ()) -> threading.Thread:
        """Create and start a new thread.
        
        Args:
            name: Thread name
            target: Thread target function
            args: Arguments to pass to the target function
            
        Returns:
            threading.Thread: Started thread
        """
        # Check if we've reached the maximum number of threads
        with self.thread_pool_lock:
            if self.active_thread_count >= self.max_threads:
                self.logger.warning(f"Thread pool exhaustion: {self.active_thread_count}/{self.max_threads} threads active")
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.log_thread_info()
                    
        thread = self.create_thread(name, target, args)
        thread.start()
        self.threads.append(thread)
        self.logger.info(f"Started thread: {name}")
        
        if self.debug and self.debug.is_debug_enabled():
            self.debug.debug(f"Thread added to managed threads list: {name}")
            self.debug.log_thread_info()
            
        return thread
    
    def create_stop_event(self, name: str) -> threading.Event:
        """Create a stop event for a thread.
        
        Args:
            name: Thread name
            
        Returns:
            threading.Event: Stop event
        """
        stop_event = threading.Event()
        self.thread_stop_events[name] = stop_event
        return stop_event
    
    def stop_thread(self, name: str, thread: threading.Thread, timeout: float = 1.0) -> bool:
        """Stop a thread gracefully.
        
        Args:
            name: Thread name
            thread: Thread to stop
            timeout: Timeout in seconds to wait for thread to stop
            
        Returns:
            bool: True if thread was stopped gracefully, False otherwise
        """
        if self.debug and self.debug.is_debug_enabled():
            self.debug.debug(f"Attempting to stop thread: {name}")
            
        if not thread or not thread.is_alive():
            self.logger.info(f"No thread {name} running to stop")
            return True
            
        self.logger.info(f"Stopping thread: {name}")
        
        # Signal the thread to stop
        if name in self.thread_stop_events:
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Setting stop event for thread: {name}")
            self.thread_stop_events[name].set()
            
        # Wait for thread to terminate
        if thread.is_alive():
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Waiting for thread {name} to terminate (timeout: {timeout}s)")
                self.debug.start_timer(f"thread_stop_{name}")
                
            thread.join(timeout=timeout)
            
            if self.debug and self.debug.is_debug_enabled():
                self.debug.end_timer(f"thread_stop_{name}")
                
            if thread.is_alive():
                self.logger.warning(f"Thread {name} did not terminate gracefully within {timeout}s")
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.debug(f"Thread {name} is still alive after timeout")
                return False
                
        # Remove from active threads list
        if thread in self.threads:
            self.threads.remove(thread)
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Thread {name} removed from managed threads list")
                
        # Clean up any resources associated with this thread
        if name in self.thread_stop_events:
            del self.thread_stop_events[name]
            if self.debug and self.debug.is_debug_enabled():
                self.debug.debug(f"Stop event for thread {name} removed")
                
        return True
    
    def stop_all_threads(self, timeout: float = 5.0) -> None:
        """Stop all threads gracefully.
        
        Args:
            timeout: Timeout in seconds to wait for each thread to stop
        """
        self.logger.info("Stopping all threads")
        
        if self.debug and self.debug.is_debug_enabled():
            self.debug.debug(f"Stopping all threads (count: {len(self.threads)})")
            self.debug.log_thread_info()
            self.debug.start_timer("stop_all_threads")
        
        # Signal all threads to stop
        self.global_stop_event.set()
        for event in self.thread_stop_events.values():
            event.set()
        
        # Wait for threads to complete
        threads_stopped = 0
        threads_stuck = 0
        
        for thread in self.threads[:]:  # Create a copy of the list to avoid modification during iteration
            if thread.is_alive():
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.debug(f"Waiting for thread {thread.name} to terminate...")
                    
                self.logger.info(f"Waiting for thread {thread.name} to terminate...")
                thread.join(timeout=timeout)
                
                if thread.is_alive():
                    self.logger.warning(f"Thread {thread.name} did not terminate gracefully")
                    threads_stuck += 1
                    
                    if self.debug and self.debug.is_debug_enabled():
                        self.debug.debug(f"Thread {thread.name} is still alive after timeout")
                else:
                    self.threads.remove(thread)
                    threads_stopped += 1
                    
                    if self.debug and self.debug.is_debug_enabled():
                        self.debug.debug(f"Thread {thread.name} terminated successfully")
        
        # Clean up resources
        if threads_stuck == 0:
            # Only clear stop events if all threads terminated
            self.thread_stop_events.clear()
            
        # Reset global stop event only if we're not in the middle of a full shutdown
        # This allows restarting thread operations if needed
        if not self.threads:
            self.global_stop_event.clear()
            
        if self.debug and self.debug.is_debug_enabled():
            self.debug.end_timer("stop_all_threads")
            self.debug.debug(f"Thread shutdown summary: {threads_stopped} stopped, {threads_stuck} stuck")
            self.debug.log_resources()
    
    def sleep_with_check(self, seconds: int, stop_event: threading.Event) -> bool:
        """Sleep for specified seconds while periodically checking stop event.
        
        Args:
            seconds: Number of seconds to sleep
            stop_event: Event to check for termination signal
            
        Returns:
            bool: True if sleep completed, False if interrupted by stop event
        """
        if self.debug and self.debug.is_debug_enabled():
            thread_name = threading.current_thread().name
            self.debug.debug(f"Thread {thread_name} sleeping for {seconds} seconds with stop check")
        
        # Get the main app instance if available to access db_manager
        main_app = None
        current_thread = threading.current_thread()
        if hasattr(current_thread, '_target') and hasattr(current_thread._target, '__self__'):
            target_self = current_thread._target.__self__
            if hasattr(target_self, 'db_manager'):
                main_app = target_self
        
        for i in range(seconds):
            if stop_event.is_set() or self.global_stop_event.is_set():
                if self.debug and self.debug.is_debug_enabled():
                    thread_name = threading.current_thread().name
                    self.debug.debug(f"Thread {thread_name} sleep interrupted after {i} seconds")
                return False
                
            # Every 10 seconds, close and reopen database connections to prevent leaks
            if i > 0 and i % 10 == 0 and main_app and hasattr(main_app, 'db_manager'):
                if self.debug and self.debug.is_debug_enabled():
                    self.debug.debug(f"Thread {thread_name} releasing database connection during sleep")
                try:
                    main_app.db_manager.close()
                except Exception as e:
                    if self.debug and self.debug.is_debug_enabled():
                        self.debug.debug(f"Error closing database connection: {e}")
            
            time.sleep(1)
            
        if self.debug and self.debug.is_debug_enabled():
            thread_name = threading.current_thread().name
            self.debug.debug(f"Thread {thread_name} completed {seconds} seconds sleep")
            
        return True
        
    def track_lock_acquisition(self, lock: threading.Lock, lock_name: str) -> bool:
        """Track lock acquisition to detect potential deadlocks.
        
        Args:
            lock: The lock being acquired
            lock_name: Name of the lock for identification
            
        Returns:
            bool: True if lock acquisition is safe, False if potential deadlock detected
        """
        if not self.debug or not self.debug.is_debug_enabled():
            return True
            
        thread = threading.current_thread()
        thread_id = thread.ident
        
        with self.deadlock_check_lock:
            # Log lock acquisition attempt
            self.debug.log_lock_info(lock, lock_name, acquiring=True)
            
            # Check if this thread already holds locks
            if thread_id in self.thread_locks:
                # Add this lock to the thread's held locks
                self.thread_locks[thread_id].add(lock_name)
            else:
                # Initialize the set of locks held by this thread
                self.thread_locks[thread_id] = {lock_name}
                
            # Record that this lock is now owned by this thread
            self.lock_owners[lock_name] = thread_id
            
        return True
        
    def track_lock_release(self, lock: threading.Lock, lock_name: str) -> None:
        """Track lock release to update deadlock detection data.
        
        Args:
            lock: The lock being released
            lock_name: Name of the lock for identification
        """
        if not self.debug or not self.debug.is_debug_enabled():
            return
            
        thread = threading.current_thread()
        thread_id = thread.ident
        
        with self.deadlock_check_lock:
            # Log lock release
            self.debug.log_lock_info(lock, lock_name, acquiring=False)
            
            # Remove this lock from the thread's held locks
            if thread_id in self.thread_locks:
                self.thread_locks[thread_id].discard(lock_name)
                
                # If thread no longer holds any locks, remove it from tracking
                if not self.thread_locks[thread_id]:
                    del self.thread_locks[thread_id]
            
            # Remove this lock from the owners map
            if lock_name in self.lock_owners:
                del self.lock_owners[lock_name]
                
            # Remove any wait relationships involving this lock
            for waiting_thread in list(self.lock_wait_graph.keys()):
                if lock_name in self.lock_wait_graph.get(waiting_thread, set()):
                    self.lock_wait_graph[waiting_thread].remove(lock_name)
                    
                    # If thread is no longer waiting for any locks, remove it from tracking
                    if not self.lock_wait_graph[waiting_thread]:
                        del self.lock_wait_graph[waiting_thread]
    
    def check_for_deadlocks(self) -> bool:
        """Check for potential deadlocks in the current lock wait graph.
        
        Returns:
            bool: True if deadlock detected, False otherwise
        """
        if not self.debug or not self.debug.is_debug_enabled():
            return False
            
        with self.deadlock_check_lock:
            # Simple cycle detection in the wait graph
            visited = set()
            path = []
            
            def dfs(thread_id):
                if thread_id in path:
                    # Cycle detected - deadlock!
                    cycle_path = path[path.index(thread_id):] + [thread_id]
                    thread_names = [threading.get_ident() == tid and "current thread" or f"thread-{tid}" for tid in cycle_path]
                    locks_involved = [self.lock_owners.get(lock_name, "unknown") for lock_name in self.lock_wait_graph.get(thread_id, [])]
                    
                    # Use the critical issue logger for deadlock detection
                    deadlock_details = {
                        "thread_path": ' -> '.join(thread_names),
                        "locks_involved": locks_involved,
                        "thread_ids": cycle_path
                    }
                    
                    if self.debug:
                        self.debug.log_critical_issue(
                            "DEADLOCK",
                            f"Deadlock detected between threads: {' -> '.join(thread_names)}",
                            deadlock_details
                        )
                    return True
                    
                if thread_id in visited:
                    return False
                    
                visited.add(thread_id)
                path.append(thread_id)
                
                # Check all locks this thread is waiting for
                for lock_name in self.lock_wait_graph.get(thread_id, []):
                    # Find the thread that owns this lock
                    owner_thread = self.lock_owners.get(lock_name)
                    if owner_thread and dfs(owner_thread):
                        return True
                        
                path.pop()
                return False
                
            # Start DFS from each thread in the wait graph
            for thread_id in self.lock_wait_graph:
                if dfs(thread_id):
                    return True
                    
            return False
            
    def track_resource(self, resource_name: str, resource: Any) -> None:
        """Track a resource that should be properly closed/released.
        
        Args:
            resource_name: Name of the resource
            resource: The resource object to track
        """
        if not self.debug or not self.debug.is_debug_enabled():
            return
            
        self.resources[resource_name] = resource
        self.debug.track_resource(resource_name, resource)
        
    def check_for_resource_leaks(self, timeout_seconds: int = 300) -> None:
        """Check for potential resource leaks by identifying resources that have been tracked for too long.
        
        Args:
            timeout_seconds: Number of seconds after which a resource is considered potentially leaked
        """
        if not self.debug or not self.debug.is_debug_enabled():
            return
            
        current_time = time.time()
        leaked_resources = []
        
        # Use the debug logger's resource trackers
        for resource_name, info in self.debug._resource_trackers.items():
            elapsed = current_time - info['time']
            if elapsed > timeout_seconds:
                leaked_resources.append({
                    'name': resource_name,
                    'elapsed_time': elapsed,
                    'thread': info['thread']
                })
                
        if leaked_resources:
            # Log each leaked resource as a critical issue
            for resource in leaked_resources:
                if self.debug:
                    self.debug.log_critical_issue(
                        "RESOURCE_LEAK",
                        f"Resource {resource['name']} has not been released for {resource['elapsed_time']:.1f} seconds",
                        {
                            'resource': resource['name'],
                            'elapsed_time': resource['elapsed_time'],
                            'thread': resource['thread']
                        }
                    )
    
    def release_resource(self, resource_name: str) -> None:
        """Mark a resource as released/closed.
        
        Args:
            resource_name: Name of the resource to release
        """
        if not self.debug or not self.debug.is_debug_enabled():
            return
            
        if resource_name in self.resources:
            del self.resources[resource_name]
            self.debug.release_resource(resource_name)