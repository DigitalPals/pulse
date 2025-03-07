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

from cybex_pulse.utils.version_manager import version_manager

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
        self.current_commit_hash = self.get_current_commit_hash()  # Use our own method instead
        self.current_version = version_manager.get_version()
        self.latest_version = None
        self.update_error = None
        self.last_checked = None
    
    def get_current_commit_hash(self) -> Optional[str]:
        """Get the current Git commit hash.
        
        Returns:
            str: Current commit hash or None if an error occurred
        """
        try:
            # Get expected git repository location (always at /opt/pulse)
            repo_dir = '/opt/pulse'
            if not os.path.exists(repo_dir):
                # Fall back to try relative path resolution if not at standard location
                repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            
            # Check if we're in a git repository - specify the repo directory explicitly
            repo_check = subprocess.run(
                ['git', '-C', repo_dir, 'rev-parse', '--is-inside-work-tree'],
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
                
            # Run git rev-parse to get current commit hash - specify the repo directory explicitly
            result = subprocess.run(
                ['git', '-C', repo_dir, 'rev-parse', 'HEAD'],
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
    
    def get_latest_commit_hash(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the latest commit hash and version from GitHub.
        
        Returns:
            tuple: (latest_commit_hash, latest_version) or (None, None) if an error occurred
        """
        try:
            # Use GitHub API to get latest commit hash
            commit_response = requests.get(
                'https://api.github.com/repos/DigitalPals/pulse/commits/main',
                timeout=10
            )
            commit_response.raise_for_status()
            commit_data = commit_response.json()
            latest_hash = commit_data.get('sha')
            
            # Try to get latest version from tags
            try:
                tags_response = requests.get(
                    'https://api.github.com/repos/DigitalPals/pulse/tags',
                    timeout=10
                )
                tags_response.raise_for_status()
                tags_data = tags_response.json()
                
                if tags_data and len(tags_data) > 0:
                    # Get the most recent tag
                    latest_tag = tags_data[0].get('name', '')
                    # Remove 'v' prefix if present
                    latest_version = latest_tag[1:] if latest_tag.startswith('v') else latest_tag
                else:
                    # If no tags, use commit hash as version
                    latest_version = latest_hash[:7]
            except (requests.RequestException, json.JSONDecodeError) as e:
                self.logger.warning(f"Failed to get latest tag from GitHub: {e}")
                latest_version = latest_hash[:7] if latest_hash else None
                
            return latest_hash, latest_version
        except (requests.RequestException, json.JSONDecodeError) as e:
            self.logger.error(f"Failed to get latest commit hash from GitHub: {e}")
            return None, None
    
    def check_for_updates(self) -> Tuple[bool, Optional[str]]:
        """Check if updates are available.
        
        Returns:
            tuple: (update_available, error_message)
        """
        self.update_error = None
        self.last_checked = time.time()
        
        # Get current commit hash for comparison
        self.current_commit_hash = self.get_current_commit_hash()
        if not self.current_commit_hash:
            self.update_error = "Failed to get current commit hash"
            return False, self.update_error
            
        # Check if we're using a fallback version (not a git repository)
        if self.current_commit_hash.startswith("install-") or self.current_commit_hash == "unknown":
            self.logger.info("Using non-git installation. Update checks disabled.")
            self.update_available = False
            return False, None
        
        # Get latest commit hash and version
        result = self.get_latest_commit_hash()
        if not result[0]:  # First element is commit hash
            self.update_error = "Failed to get latest commit hash from GitHub"
            return False, self.update_error
            
        self.latest_commit_hash, self.latest_version = result
        
        # Compare hashes
        self.update_available = self.current_commit_hash != self.latest_commit_hash
        
        # Log version information
        self.logger.info(f"Current version: {self.current_version}")
        if self.latest_version:
            self.logger.info(f"Latest version available: {self.latest_version}")
        self.logger.info(f"Update available: {self.update_available}")
        
        return self.update_available, None
    
    def update_application(self, progress_callback=None) -> Tuple[bool, Optional[str]]:
        """Update the application using git pull.
        
        Args:
            progress_callback: Optional callback function to receive real-time progress updates
            
        Returns:
            tuple: (success, error_message)
        """
        # Check if we're using a fallback version (not a git repository)
        if hasattr(self, 'current_commit_hash') and self.current_commit_hash:
            if self.current_commit_hash.startswith("install-") or self.current_commit_hash == "unknown":
                error_msg = "Cannot update: not a git repository installation."
                self.logger.warning(error_msg)
                if progress_callback:
                    progress_callback(error_msg, is_error=True)
                return False, error_msg

        try:
            # Get expected git repository location (always at /opt/pulse)
            repo_dir = '/opt/pulse'
            if not os.path.exists(repo_dir):
                # Fall back to try relative path resolution if not at standard location
                repo_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
            
            # First check if we're in a git repository
            if progress_callback:
                progress_callback("Checking repository status...")
                
            repo_check = subprocess.run(
                ['git', '-C', repo_dir, 'rev-parse', '--is-inside-work-tree'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            # If not a git repository, return error
            if repo_check.returncode != 0:
                error_msg = "Cannot update: not a git repository installation."
                self.logger.warning(error_msg)
                if progress_callback:
                    progress_callback(error_msg, is_error=True)
                return False, error_msg
            
            # Run git status to show current state
            if progress_callback:
                progress_callback("Checking for local changes...")
                
            status_result = subprocess.run(
                ['git', '-C', repo_dir, 'status', '--short'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if status_result.stdout.strip():
                if progress_callback:
                    progress_callback("Local changes detected:\n" + status_result.stdout)
            else:
                if progress_callback:
                    progress_callback("Working directory clean")
            
            # Run git fetch to get latest changes
            if progress_callback:
                progress_callback("Fetching latest changes from remote repository...")
                
            fetch_result = subprocess.run(
                ['git', '-C', repo_dir, 'fetch'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if fetch_result.stdout:
                if progress_callback:
                    progress_callback(fetch_result.stdout)
            
            # Force update by resetting any local changes
            if progress_callback:
                progress_callback("Resetting local changes to ensure clean update...")
                
            reset_result = subprocess.run(
                ['git', '-C', repo_dir, 'reset', '--hard', 'origin/main'],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if reset_result.stdout:
                if progress_callback:
                    progress_callback(reset_result.stdout)
            if reset_result.stderr:
                if progress_callback:
                    progress_callback(reset_result.stderr, is_error=True)
            
            # Run git pull to update
            if progress_callback:
                progress_callback("Pulling latest changes...")
                
            result = subprocess.run(
                ['git', '-C', repo_dir, 'pull', '--force'],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Send output to callback
            if progress_callback:
                if result.stdout:
                    progress_callback(result.stdout)
                if result.stderr:
                    progress_callback(result.stderr, is_error=True)
            
            # Check for merge conflicts
            if "CONFLICT" in result.stdout or "CONFLICT" in result.stderr:
                error_msg = "Merge conflict detected during update"
                if progress_callback:
                    progress_callback(error_msg, is_error=True)
                return False, error_msg
            
            # Check for authentication failure
            if "Authentication failed" in result.stdout or "Authentication failed" in result.stderr:
                error_msg = "Git authentication failed"
                if progress_callback:
                    progress_callback(error_msg, is_error=True)
                return False, error_msg
            
            # Check if any changes were pulled
            if "Already up to date" in result.stdout:
                if progress_callback:
                    progress_callback("No changes to pull - already up to date")
            else:
                if progress_callback:
                    progress_callback("Update successful")
            
            return True, None
        except subprocess.SubprocessError as e:
            error_msg = f"Failed to update application: {e}"
            self.logger.error(error_msg)
            if progress_callback:
                progress_callback(error_msg, is_error=True)
            return False, error_msg
    
    def restart_application(self) -> None:
        """Restart the application.
        
        This function uses different methods based on the platform.
        """
        try:
            # Enable more verbose logging
            self.logger.setLevel(logging.DEBUG)
            self.logger.debug("Starting restart process with detailed logging")
            
            # Try multiple paths to find the executable
            possible_paths = [
                # Standard installation path
                "/usr/local/bin/cybex-pulse",
                # Legacy path in installation directory
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../cybex-pulse")),
                # Compatibility path
                "/opt/cybex-pulse",
                # Older versions used pulse filename
                os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../pulse"))
            ]
            
            # Log all possible paths
            self.logger.debug(f"Checking possible executable paths: {possible_paths}")
            
            # Find the first existing executable
            current_script = None
            for path in possible_paths:
                self.logger.debug(f"Checking path: {path}")
                if os.path.exists(path):
                    self.logger.debug(f"Path exists: {path}")
                    # Check if it's a file (not a directory) and is executable
                    if os.path.isfile(path) and os.access(path, os.X_OK):
                        self.logger.debug(f"Path is a file and is executable: {path}")
                        current_script = path
                        break
                    elif os.path.isdir(path):
                        self.logger.debug(f"Path is a directory, not a file: {path}")
                    elif not os.access(path, os.X_OK):
                        self.logger.debug(f"Path exists but is not executable: {path}")
                else:
                    self.logger.debug(f"Path does not exist: {path}")
            
            # If no executable found in standard paths, check for the pulse script in the root directory
            if not current_script:
                self.logger.debug("No executable found in standard paths, checking for pulse script")
                pulse_script = "/opt/pulse/pulse"
                self.logger.debug(f"Checking pulse script at: {pulse_script}")
                
                if os.path.exists(pulse_script):
                    self.logger.debug(f"Pulse script exists at: {pulse_script}")
                    # Check if it's a file and is executable
                    if os.path.isfile(pulse_script) and os.access(pulse_script, os.X_OK):
                        self.logger.debug(f"Pulse script is a file and is executable")
                        current_script = pulse_script
                        self.logger.info(f"Found pulse script at: {current_script}")
                    elif os.path.isdir(pulse_script):
                        self.logger.debug(f"Pulse script path is a directory, not a file")
                    elif not os.access(pulse_script, os.X_OK):
                        self.logger.debug(f"Pulse script exists but is not executable")
                else:
                    self.logger.debug(f"Pulse script does not exist at: {pulse_script}")
                
                # Try to find run_app.py as a fallback
                if not current_script:
                    run_app_script = "/opt/pulse/run_app.py"
                    self.logger.debug(f"Checking run_app.py at: {run_app_script}")
                    
                    if os.path.exists(run_app_script):
                        self.logger.debug(f"run_app.py exists at: {run_app_script}")
                        # Check if it's a file and is executable
                        if os.path.isfile(run_app_script) and os.access(run_app_script, os.X_OK):
                            self.logger.debug(f"run_app.py is a file and is executable")
                            current_script = run_app_script
                            self.logger.info(f"Found run_app.py script at: {current_script}")
                        elif os.path.isdir(run_app_script):
                            self.logger.debug(f"run_app.py path is a directory, not a file")
                        elif not os.access(run_app_script, os.X_OK):
                            self.logger.debug(f"run_app.py exists but is not executable")
                    else:
                        self.logger.debug(f"run_app.py does not exist at: {run_app_script}")
                
                if not current_script:
                    self.logger.error("Could not find application executable for restart")
                    return
                
            # Determine platform and restart accordingly
            system = platform.system().lower()
            
            if system == "linux" or system == "darwin":
                # Use subprocess instead of execv to avoid permission issues
                self.logger.info(f"Restarting application with: {current_script}")
                try:
                    # Determine the correct execution method based on the script type
                    script_basename = os.path.basename(current_script)
                    self.logger.debug(f"Script basename: {script_basename}")
                    
                    # Use a direct approach with the full path to the script
                    if script_basename == 'pulse':
                        # For the pulse bash script
                        self.logger.info("Executing pulse bash script directly")
                        cmd = ["/bin/bash", current_script]
                        self.logger.debug(f"Executing command: {cmd} in directory: /opt/pulse")
                        try:
                            # Use Popen to start the process without waiting
                            self.logger.debug("Starting process with Popen")
                            subprocess.Popen(cmd, cwd="/opt/pulse", close_fds=True)
                            
                            # Log success and exit this process
                            self.logger.info("Successfully started new process, exiting current process")
                            os._exit(0)
                        except Exception as e:
                            self.logger.error(f"Error executing pulse script: {e}")
                    elif script_basename == 'run_app.py':
                        # For the Python script
                        self.logger.info("Executing Python script directly")
                        cmd = ["/usr/bin/python3", current_script]
                        self.logger.debug(f"Executing command: {cmd} in directory: /opt/pulse")
                        try:
                            # Use Popen to start the process without waiting
                            self.logger.debug("Starting process with Popen")
                            subprocess.Popen(cmd, cwd="/opt/pulse", close_fds=True)
                            
                            # Log success and exit this process
                            self.logger.info("Successfully started new process, exiting current process")
                            os._exit(0)
                        except Exception as e:
                            self.logger.error(f"Error executing Python script: {e}")
                    else:
                        # For other executables
                        self.logger.info("Executing application binary directly")
                        cmd = [current_script]
                        self.logger.debug(f"Executing command: {cmd}")
                        try:
                            # Use Popen to start the process without waiting
                            self.logger.debug("Starting process with Popen")
                            subprocess.Popen(cmd, close_fds=True)
                            
                            # Log success and exit this process
                            self.logger.info("Successfully started new process, exiting current process")
                            os._exit(0)
                        except Exception as e:
                            self.logger.error(f"Error executing binary: {e}")
                    
                    # Exit the current process
                    self.logger.info("Exiting current process to complete restart")
                    os._exit(0)
                except subprocess.SubprocessError as e:
                    self.logger.error(f"Failed to restart using subprocess: {e}")
                    # Fall back to execv as a last resort
                    self.logger.info("Falling back to execv for restart")
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
            # Log more detailed error information
            import traceback
            self.logger.error(f"Restart error details: {traceback.format_exc()}")
    
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