#!/usr/bin/env python
"""Browser module setup script using the generic base setup."""

import sys
from pathlib import Path

# Get project root
PROJECT_ROOT = Path(__file__).parent.resolve()

# Add parent directory to path to find base module
PARENT_DIR = PROJECT_ROOT.parent
sys.path.insert(0, str(PARENT_DIR))

# Try to import the generic setup from base
try:
    from base.setup import GenericSetup
    from base.setup import main as setup_main
except ImportError:
    print("ERROR: base.setup module not found!")
    print(f"Expected at: {PARENT_DIR / 'base' / 'setup.py'}")
    print("\nPlease ensure the base module is available as a sibling to browser/")
    sys.exit(1)

# Package information specific to browser module
# Note: packages will be auto-discovered by find_packages() in base setup
PACKAGE_INFO = {
    "name": "ami-manager",
    "version": "0.1.0",
    "python_requires": ">=3.12",
    "install_requires": [
        # Core dependencies are listed in requirements.txt
        # This is just for editable install support
    ],
    "author": "AMI",
    # packages will be auto-discovered
}

# Create a browser-specific setup instance
_browser_setup = GenericSetup(PROJECT_ROOT, "AMI Manager")


# Expose the functions that MCP scripts expect
def ensure_base_module():
    """Ensure base module is available - exposed for MCP scripts."""
    return _browser_setup.ensure_base_module()


def run_environment_setup():
    """Run environment setup - exposed for MCP scripts."""
    return _browser_setup.run_environment_setup()


def main():
    """Run setup for browser module."""
    return setup_main(project_root=PROJECT_ROOT, project_name="AMI Browser", package_info=PACKAGE_INFO)


if __name__ == "__main__":
    sys.exit(main())
