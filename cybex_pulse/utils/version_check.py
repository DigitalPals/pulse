"""
Version check module for Cybex Pulse.

This module provides functionality to check for updates by comparing the
local Git commit hash with the latest commit on the main branch.
"""
import json
import logging
import os
import platform
import subprocess
import threading
import time
from typing import Dict, Optional, Tuple, Union

import requests

logger = logging.getLogger(__name__)

class UpdateChecker:
    """Check for updates to the Cybex Pulse application."""
    
    def __init__(self, check_interval: int = 3600, logger=None):
        """Initialize the update checker.
        
        Args:
            check_interval: Interval in seconds between update checks (default: 3600)
            logger: Logger instance
        """
        self.check_interval = check_interval
        self.logger = logger or logging.getLogger(__name__)
        self.thread = None
        self.stop_event = threading.Event()
        self.update_available = False
        self.latest_commit_hash = None
        self.current_commit_hash = None
        self.update_error = None
        self.last_checked = None
    
    def get_current_commit_hash(self) -> Optional[str]:
        """Get the current Git commit hash.
        
        Returns:
            str: Current commit hash or None if an error occurred
        """
        try:
            # First check if we're in a git repository
            repo_check = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # If not a git repository, return a fallback identifier
            if repo_check.returncode != 0:
                self.logger.warning("Not running from a git repository. Using fallback version identifier.")
                # Use the modification time of the main script as a fallback version
                script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../pulse"))
                if os.path.exists(script_path):
                    return f"install-{int(os.path.getmtime(script_path))}"
                return "unknown"
                
            # Run git rev-parse to get current commit hash
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout.strip()
        except subprocess.SubprocessError as e:
            self.logger.error(f"Failed to get current commit hash: {e}")
            # Use fallback version identifier
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../pulse"))
            if os.path.exists(script_path):
                return f"install-{int(os.path.getmtime(script_path))}"
            return "unknown"
    
    def get_latest_commit_hash(self) -> Optional[str]:
        """Get the latest commit hash from GitHub.
        
        Returns:
            str: Latest commit hash from GitHub or None if an error occurred
        """
        try:
            # Use GitHub API to get latest commit hash
            response = requests.get(
                'https://api.github.com/repos/DigitalPals/pulse/commits/main',
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('sha')
        except (requests.RequestException, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to get latest commit hash from GitHub: {e}")
            return None
    
    def check_for_updates(self) -> Tuple[bool, Optional[str]]:
        """Check if updates are available.
        
        Returns:
            tuple: (update_available, error_message)
        """
        self.update_error = None
        self.last_checked = time.time()
        
        # Get current commit hash
        self.current_commit_hash = self.get_current_commit_hash()
        if not self.current_commit_hash:
            self.update_error = "Failed to get current commit hash"
            return False, self.update_error
            
        # Check if we're using a fallback version (not a git repository)
        if self.current_commit_hash.startswith("install-") or self.current_commit_hash == "unknown":
            self.logger.info("Using non-git installation. Update checks disabled.")
            self.update_available = False
            return False, None
        
        # Get latest commit hash
        self.latest_commit_hash = self.get_latest_commit_hash()
        if not self.latest_commit_hash:
            self.update_error = "Failed to get latest commit hash from GitHub"
            return False, self.update_error
        
        # Compare hashes
        self.update_available = self.current_commit_hash != self.latest_commit_hash
        return self.update_available, None
    
    def update_application(self) -> Tuple[bool, Optional[str]]:
        """Update the application using git pull.
        
        Returns:
            tuple: (success, error_message)
        """
        # Check if we're using a fallback version (not a git repository)
        if hasattr(self, 'current_commit_hash') and self.current_commit_hash:
            if self.current_commit_hash.startswith("install-") or self.current_commit_hash == "unknown":
                error_msg = "Cannot update: not a git repository installation."
                self.logger.warning(error_msg)
                return False, error_msg

        try:
            # First check if we're in a git repository
            repo_check = subprocess.run(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # If not a git repository, return error
            if repo_check.returncode != 0:
                error_msg = "Cannot update: not a git repository installation."
                self.logger.warning(error_msg)
                return False, error_msg
            
            # Run git pull to update
            result = subprocess.run(
                ['git', 'pull'],
                check=True,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check for merge conflicts
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                return False, "Merge conflict detected during update"
            
            # Check for authentication failure
            if "Authentication failed" in result.stdout or "Authentication failed" in result.stderr:
                return False, "Git authentication failed"
            
            return True, None
        except subprocess.SubprocessError as e:
            error_msg = f"Failed to update application: {e}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def restart_application(self) -> None:
        """Restart the application.
        
        This function uses different methods based on the platform.
        """
        try:
            # Get the path to the current script
            current_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../pulse"))
            
            # Determine platform and restart accordingly
            system = platform.system().lower()
            
            if system == "linux" or system == "darwin":
                # Use execv on Unix-like systems
                self.logger.info(f"Restarting application with: {current_script}")
                os.execv(current_script, [current_script])
            elif system == "windows":
                # Use subprocess on Windows
                self.logger.info(f"Restarting application with: {current_script}")
                subprocess.Popen([current_script], close_fds=True)
                os._exit(0)
            else:
                self.logger.error(f"Unsupported platform for restart: {system}")
        except Exception as e:
            self.logger.error(f"Failed to restart application: {e}")
    
    def start_checker_thread(self) -> None:
        """Start the update checker thread."""
        if self.thread and self.thread.is_alive():
            self.logger.info("Update checker thread already running")
            return
        
        self.logger.info("Starting update checker thread")
        self.stop_event.clear()
        self.thread = threading.Thread(
            target=self._run_update_checker,
            name="UpdateChecker",
            daemon=True
        )
        self.thread.start()
    
    def stop_checker_thread(self) -> None:
        """Stop the update checker thread."""
        if not self.thread or not self.thread.is_alive():
            return
        
        self.logger.info("Stopping update checker thread")
        self.stop_event.set()
        self.thread.join(timeout=1.0)
        self.thread = None
    
    def _run_update_checker(self) -> None:
        """Run the update checker in a loop."""
        self.logger.info("Update checker thread started")
        
        # Initial check
        self.check_for_updates()
        
        while not self.stop_event.is_set():
            try:
                # Sleep for interval
                self._sleep_with_check(self.check_interval)
                
                # Skip if thread should stop
                if self.stop_event.is_set():
                    break
                
                # Check for updates
                self.check_for_updates()
            except Exception as e:
                self.logger.error(f"Error in update checker: {e}")
                self._sleep_with_check(60)
    
    def _sleep_with_check(self, seconds: int) -> None:
        """Sleep for specified seconds while periodically checking stop event.
        
        Args:
            seconds: Number of seconds to sleep
        """
        for _ in range(seconds):
            if self.stop_event.is_set():
                break
            time.sleep(1)