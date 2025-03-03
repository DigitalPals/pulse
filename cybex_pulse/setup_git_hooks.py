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
python -m setuptools_scm
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
python -m setuptools_scm
"""
    
    # Write the pre-push hook
    with open(pre_push_path, 'w') as f:
        f.write(pre_push_content)
    
    # Make the hook executable
    os.chmod(pre_push_path, os.stat(pre_push_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    
    print(f"Created pre-push hook at {pre_push_path}")

def main():
    """Main function to set up Git hooks."""
    print("Setting up Git hooks for automatic versioning...")
    create_post_commit_hook()
    create_pre_push_hook()
    print("Git hooks setup complete.")
    
    # Install setuptools_scm if not already installed
    try:
        import setuptools_scm
        print("setuptools_scm is already installed.")
    except ImportError:
        print("Installing setuptools_scm...")
        subprocess.run(['pip', 'install', 'setuptools_scm'], check=True)
        print("setuptools_scm installed successfully.")
    
    # Generate initial version
    print("Generating initial version...")
    subprocess.run(['python', '-m', 'setuptools_scm'], check=True)
    print("Initial version generated.")

if __name__ == "__main__":
    main()