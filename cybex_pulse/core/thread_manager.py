"""
Thread management module for Cybex Pulse.

This module provides centralized thread management functionality:
- Creating and managing daemon threads
- Graceful thread termination
- Thread lifecycle monitoring
- Thread status reporting
"""
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional


class ThreadManager:
    """Centralized thread management for Cybex Pulse.
    
    This class provides a unified interface for:
    - Creating and starting threads
    - Stopping threads gracefully
    - Monitoring thread status
    - Managing thread lifecycle
    """
    
    def __init__(self, logger: logging.Logger):
        """Initialize the thread manager.
        
        Args:
            logger: Logger instance
        """
        self.logger = logger
        self.threads = []
        self.thread_stop_events = {}
        self.global_stop_event = threading.Event()
    
    def create_thread(self, name: str, target: Callable, args: tuple = ()) -> threading.Thread:
        """Create a new daemon thread.
        
        Args:
            name: Thread name
            target: Thread target function
            args: Arguments to pass to the target function
            
        Returns:
            threading.Thread: Created thread
        """
        thread = threading.Thread(
            target=target,
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
        thread = self.create_thread(name, target, args)
        thread.start()
        self.threads.append(thread)
        self.logger.info(f"Started thread: {name}")
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
        if not thread or not thread.is_alive():
            self.logger.info(f"No thread {name} running to stop")
            return True
            
        self.logger.info(f"Stopping thread: {name}")
        
        # Signal the thread to stop
        if name in self.thread_stop_events:
            self.thread_stop_events[name].set()
            
        # Wait for thread to terminate
        if thread.is_alive():
            thread.join(timeout=timeout)
            if thread.is_alive():
                self.logger.warning(f"Thread {name} did not terminate gracefully")
                return False
                
        # Remove from active threads list
        if thread in self.threads:
            self.threads.remove(thread)
            
        return True
    
    def stop_all_threads(self, timeout: float = 5.0) -> None:
        """Stop all threads gracefully.
        
        Args:
            timeout: Timeout in seconds to wait for each thread to stop
        """
        self.logger.info("Stopping all threads")
        
        # Signal all threads to stop
        self.global_stop_event.set()
        for event in self.thread_stop_events.values():
            event.set()
        
        # Wait for threads to complete
        for thread in self.threads[:]:  # Create a copy of the list to avoid modification during iteration
            if thread.is_alive():
                self.logger.info(f"Waiting for thread {thread.name} to terminate...")
                thread.join(timeout=timeout)
                if thread.is_alive():
                    self.logger.warning(f"Thread {thread.name} did not terminate gracefully")
                else:
                    self.threads.remove(thread)
    
    def sleep_with_check(self, seconds: int, stop_event: threading.Event) -> bool:
        """Sleep for specified seconds while periodically checking stop event.
        
        Args:
            seconds: Number of seconds to sleep
            stop_event: Event to check for termination signal
            
        Returns:
            bool: True if sleep completed, False if interrupted by stop event
        """
        for _ in range(seconds):
            if stop_event.is_set() or self.global_stop_event.is_set():
                return False
            time.sleep(1)
        return True