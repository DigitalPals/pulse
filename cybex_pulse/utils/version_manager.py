"""
Version manager for Cybex Pulse.

This module provides functionality to read the version of the application
from a VERSION file in the repository root.
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
    
    This class reads the version from a VERSION file in the repository root.
    The version should be manually updated in this file to ensure all users
    have the same version information.
    """
    
    def __init__(self):
        """Initialize the version manager."""
        self.version = None
        self.last_modified = None
        self.version_file = self._get_version_file_path()
        
    def get_version(self) -> str:
        """Get the current version of the application.
        
        Returns:
            str: The current version from the VERSION file
        """
        if self.version is not None:
            return self.version
            
        # Load the current version from the version file
        self._load_version_info()
        
        return self.version
    
    def _get_version_file_path(self) -> Path:
        """Get the path to the version file.
        
        Returns:
            Path: Path to the version file
        """
        # Always use a version file in the repository root
        # This ensures all users have the same version information
        root_dir = self._get_project_root()
        if not root_dir:
            # Fallback to the current directory if we can't find the project root
            root_dir = os.path.dirname(os.path.abspath(__file__))
            root_dir = os.path.abspath(os.path.join(root_dir, ".."))
            
        return Path(root_dir) / "VERSION"
    
    def _load_version_info(self) -> None:
        """Load version information from the version file."""
        if not self.version_file.exists():
            # If the file doesn't exist, create it with default values
            self.version = "0.1.0"
            self.last_modified = time.time()
            self._save_version_info()
            return
        
        try:
            with open(self.version_file, 'r') as f:
                # The VERSION file contains just the version string
                self.version = f.read().strip()
                self.last_modified = self.version_file.stat().st_mtime
        except IOError as e:
            logger.error(f"Error loading version file: {e}")
            # Use default values
            self.version = "0.1.0"
            self.last_modified = time.time()
            self._save_version_info()
    
    def _save_version_info(self) -> None:
        """Save version information to the version file."""
        try:
            with open(self.version_file, 'w') as f:
                # Just write the version string to the file
                f.write(self.version)
            self.last_modified = time.time()
        except IOError as e:
            logger.error(f"Error saving version file: {e}")
    
    def _have_files_changed(self) -> bool:
        """Check if files have changed.
        
        Since we're now using a repository-based version file,
        we no longer track file changes automatically. The version
        should be manually updated in the VERSION file.
        
        Returns:
            bool: Always returns False since we don't auto-increment anymore
        """
        return False
    
    # _compute_file_hashes method removed as it's no longer needed
    
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