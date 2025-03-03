#!/usr/bin/env python3
"""
Set up Git hooks for automatic versioning.

This script installs Git hooks that automatically update the version
when commits are made.
"""
import os
import stat
import shutil
import subprocess
import re
from pathlib import Path

def get_git_root():
    """Get the root directory of the Git repository."""
    try:
        result = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.SubprocessError:
        # Fallback to current directory if not in a git repo
        return os.path.abspath(os.path.dirname(__file__))

def increment_version(version_str):
    """Increment the patch version number.
    
    For development versions (x.y.z-dev), increment the patch number.
    For release versions (x.y.z), append -dev and increment the patch number.
    
    Args:
        version_str: Current version string
        
    Returns:
        str: Updated version string
    """
    # Parse the current version
    version_parts = version_str.split('.')
    
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
    
    # Return the updated version
    return '.'.join(version_parts)

def update_version_file():
    """Update the VERSION file with an incremented version number."""
    git_root = get_git_root()
    version_file = os.path.join(git_root, "VERSION")
    
    # Read current version
    try:
        with open(version_file, 'r') as f:
            current_version = f.read().strip()
    except (IOError, FileNotFoundError):
        # If file doesn't exist or can't be read, use default
        current_version = "0.1.0-dev"
    
    # Increment version
    new_version = increment_version(current_version)
    
    # Write updated version
    try:
        with open(version_file, 'w') as f:
            f.write(new_version)
        print(f"Updated version from {current_version} to {new_version}")
        return True
    except IOError:
        print(f"Error: Could not write to VERSION file at {version_file}")
        return False

def create_post_commit_hook():
    """Create a post-commit hook that updates the version."""
    git_root = get_git_root()
    hooks_dir = os.path.join(git_root, '.git', 'hooks')
    
    # Create hooks directory if it doesn't exist
    os.makedirs(hooks_dir, exist_ok=True)
    
    # Path to the post-commit hook
    post_commit_path = os.path.join(hooks_dir, 'post-commit')
    
    # Content of the post-commit hook
    post_commit_content = """#!/bin/sh
# Post-commit hook to update version
echo "Updating version after commit..."
# Get the root directory of the Git repository
REPO_ROOT=$(git rev-parse --show-toplevel)
# Run the version update script
python $REPO_ROOT/cybex_pulse/setup_git_hooks.py --update-version
"""
    
    # Write the post-commit hook
    with open(post_commit_path, 'w') as f:
        f.write(post_commit_content)
    
    # Make the hook executable
    os.chmod(post_commit_path, os.stat(post_commit_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    print(f"Created post-commit hook at {post_commit_path}")

def create_pre_push_hook():
    """Create a pre-push hook that ensures the version is up to date."""
    git_root = get_git_root()
    hooks_dir = os.path.join(git_root, '.git', 'hooks')
    
    # Create hooks directory if it doesn't exist
    os.makedirs(hooks_dir, exist_ok=True)
    
    # Path to the pre-push hook
    pre_push_path = os.path.join(hooks_dir, 'pre-push')
    
    # Content of the pre-push hook
    pre_push_content = """#!/bin/sh
# Pre-push hook to ensure version is up to date
echo "Ensuring version is up to date before push..."
# Get the root directory of the Git repository
REPO_ROOT=$(git rev-parse --show-toplevel)
# Check if there are uncommitted changes to the VERSION file
if git diff --name-only | grep -q "VERSION"; then
    echo "Error: There are uncommitted changes to the VERSION file."
    echo "Please commit these changes before pushing."
    exit 1
fi
"""
    
    # Write the pre-push hook
    with open(pre_push_path, 'w') as f:
        f.write(pre_push_content)
    
    # Make the hook executable
    os.chmod(pre_push_path, os.stat(pre_push_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    print(f"Created pre-push hook at {pre_push_path}")

def main():
    """Main function to set up Git hooks."""
    # Check if we're just updating the version
    if len(os.sys.argv) > 1 and os.sys.argv[1] == "--update-version":
        update_version_file()
        return
    
    print("Setting up Git hooks for automatic versioning...")
    create_post_commit_hook()
    create_pre_push_hook()
    print("Git hooks setup complete.")
    
    # Generate initial version if needed
    git_root = get_git_root()
    version_file = os.path.join(git_root, "VERSION")
    if not os.path.exists(version_file):
        print("VERSION file not found. Creating with default version...")
        with open(version_file, 'w') as f:
            f.write("0.1.0-dev")
        print("Initial version file created.")

if __name__ == "__main__":
    main()