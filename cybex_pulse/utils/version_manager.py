"""
Version manager for Cybex Pulse.

This module provides functionality to automatically determine and update the version
of the application at runtime based on file changes.
"""
import logging
import os
import hashlib
import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class VersionManager:
    """Manages version information for Cybex Pulse.
    
    This class automatically tracks file changes and increments the version
    number when changes are detected.
    """
    
    def __init__(self):
        """Initialize the version manager."""
        self.version = None
        self.last_modified = None
        self.file_hashes = {}
        self.version_file = self._get_version_file_path()
        
    def get_version(self) -> str:
        """Get the current version of the application.
        
        If files have changed since the last version update, the version
        will be automatically incremented.
        
        Returns:
            str: The current version
        """
        if self.version is not None:
            return self.version
            
        # Load the current version from the version file
        self._load_version_info()
        
        # Check if files have changed
        if self._have_files_changed():
            # Increment the version and save it
            self._increment_version()
            self._save_version_info()
            logger.info(f"Version updated to {self.version} due to file changes")
        
        return self.version
    
    def _get_version_file_path(self) -> Path:
        """Get the path to the version file.
        
        Returns:
            Path: Path to the version file
        """
        # Try to use /var/lib/cybex_pulse if running as a service
        if os.access('/var/lib', os.W_OK):
            data_dir = Path('/var/lib/cybex_pulse')
        else:
            # Otherwise use the home directory
            data_dir = Path.home() / ".cybex_pulse"
        
        # Create the directory if it doesn't exist
        try:
            data_dir.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # Fallback to the current directory
            data_dir = Path(os.path.dirname(os.path.abspath(__file__))) / ".."
        
        return data_dir / "version.json"
    
    def _load_version_info(self) -> None:
        """Load version information from the version file."""
        if not self.version_file.exists():
            # If the file doesn't exist, create it with default values
            self.version = "0.1.0"
            self.last_modified = time.time()
            self.file_hashes = self._compute_file_hashes()
            self._save_version_info()
            return
        
        try:
            with open(self.version_file, 'r') as f:
                data = json.load(f)
                self.version = data.get('version', "0.1.0")
                self.last_modified = data.get('last_modified', time.time())
                self.file_hashes = data.get('file_hashes', {})
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading version file: {e}")
            # Use default values
            self.version = "0.1.0"
            self.last_modified = time.time()
            self.file_hashes = self._compute_file_hashes()
            self._save_version_info()
    
    def _save_version_info(self) -> None:
        """Save version information to the version file."""
        data = {
            'version': self.version,
            'last_modified': self.last_modified,
            'file_hashes': self.file_hashes
        }
        
        try:
            with open(self.version_file, 'w') as f:
                json.dump(data, f, indent=2)
        except IOError as e:
            logger.error(f"Error saving version file: {e}")
    
    def _have_files_changed(self) -> bool:
        """Check if any files have changed since the last version update.
        
        Returns:
            bool: True if files have changed, False otherwise
        """
        current_hashes = self._compute_file_hashes()
        
        # If we have no previous hashes, assume files have changed
        if not self.file_hashes:
            self.file_hashes = current_hashes
            return True
        
        # Check if any files have been added, removed, or modified
        if set(current_hashes.keys()) != set(self.file_hashes.keys()):
            self.file_hashes = current_hashes
            return True
        
        # Check if any file contents have changed
        for file_path, file_hash in current_hashes.items():
            if file_path not in self.file_hashes or self.file_hashes[file_path] != file_hash:
                self.file_hashes = current_hashes
                return True
        
        return False
    
    def _compute_file_hashes(self) -> Dict[str, str]:
        """Compute hashes of all Python files in the project.
        
        Returns:
            Dict[str, str]: Dictionary mapping file paths to their hashes
        """
        hashes = {}
        
        # Get the root directory of the project
        root_dir = self._get_project_root()
        if not root_dir:
            return hashes
        
        # Find all Python files
        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                if filename.endswith('.py'):
                    file_path = os.path.join(dirpath, filename)
                    try:
                        with open(file_path, 'rb') as f:
                            file_hash = hashlib.md5(f.read()).hexdigest()
                            # Store the path relative to the root directory
                            rel_path = os.path.relpath(file_path, root_dir)
                            hashes[rel_path] = file_hash
                    except IOError:
                        # Skip files that can't be read
                        pass
        
        return hashes
    
    def _get_project_root(self) -> Optional[str]:
        """Get the root directory of the project.
        
        Returns:
            Optional[str]: Path to the project root or None if not found
        """
        # Try standard installation location
        if os.path.exists('/opt/pulse'):
            return '/opt/pulse'
        
        # Try to find the project root relative to this file
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Go up two levels: utils -> cybex_pulse
            return os.path.abspath(os.path.join(current_dir, ".."))
        except Exception:
            logger.debug("Could not determine project root")
            return None
    
    def _increment_version(self) -> None:
        """Increment the version number.
        
        This follows a simple versioning scheme:
        - For development versions (x.y.z-dev), increment the patch number
        - For release versions (x.y.z), append -dev and increment the patch number
        """
        # Parse the current version
        version_parts = self.version.split('.')
        
        # Ensure we have at least three parts (major.minor.patch)
        while len(version_parts) < 3:
            version_parts.append('0')
        
        # Check if this is a development version
        if '-dev' in version_parts[-1]:
            # Extract the patch number
            patch_parts = version_parts[-1].split('-')
            try:
                patch = int(patch_parts[0])
                # Increment the patch number
                patch += 1
                # Update the version
                version_parts[-1] = f"{patch}-dev"
            except ValueError:
                # If we can't parse the patch number, just use 1
                version_parts[-1] = "1-dev"
        else:
            # This is a release version, convert to development
            try:
                patch = int(version_parts[-1])
                # Increment the patch number
                patch += 1
                # Update the version
                version_parts[-1] = f"{patch}-dev"
            except ValueError:
                # If we can't parse the patch number, just use 1
                version_parts[-1] = "1-dev"
        
        # Update the version and last modified time
        self.version = '.'.join(version_parts)
        self.last_modified = time.time()
    
    def is_development_version(self) -> bool:
        """Check if this is a development version.
        
        Returns:
            bool: True if this is a development version
        """
        # Ensure version is determined
        if self.version is None:
            self.get_version()
        
        return '-dev' in self.version
    
    def get_last_modified(self) -> float:
        """Get the timestamp of the last version update.
        
        Returns:
            float: Timestamp of the last version update
        """
        # Ensure version is determined
        if self.last_modified is None:
            self.get_version()
        
        return self.last_modified
        
    def get_commit_hash(self) -> Optional[str]:
        """Get the current commit hash (compatibility method).
        
        This method is provided for compatibility with code that expects
        the old VersionManager interface. It always returns None since
        we no longer track commit hashes.
        
        Returns:
            Optional[str]: Always returns None
        """
        return None

# Create a singleton instance
version_manager = VersionManager()