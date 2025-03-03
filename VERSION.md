# Version Management

This file explains how the version management system works in Cybex Pulse.

## VERSION File

The version of Cybex Pulse is stored in the `VERSION` file in the repository root. This file contains a single line with the version string (e.g., `0.1.3-dev`).

## Updating the Version

To update the version:

1. Edit the `VERSION` file in the repository root
2. Commit the change to the repository
3. Push the change to the remote repository

This ensures that all users who pull from the repository will have the same version information.

## Version Format

The version follows the [Semantic Versioning](https://semver.org/) format:

- `MAJOR.MINOR.PATCH` (e.g., `0.1.0`)
- For development versions, add `-dev` suffix (e.g., `0.1.3-dev`)

## Examples

- `0.1.0`: Initial release
- `0.1.1`: Patch release with bug fixes
- `0.2.0`: Minor release with new features
- `1.0.0`: Major release
- `0.1.3-dev`: Development version