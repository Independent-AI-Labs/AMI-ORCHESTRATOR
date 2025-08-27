#!/usr/bin/env python
"""Test runner for orchestrator root."""

import sys
from pathlib import Path

# Get orchestrator root
ORCHESTRATOR_ROOT = Path(__file__).resolve().parent.parent

# Add orchestrator root to path (for base imports)
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

# Import from base using proper base. prefix
from base.scripts.run_tests import main  # noqa: E402

if __name__ == "__main__":
    # Run tests using base test runner with orchestrator root
    sys.exit(main(project_root=ORCHESTRATOR_ROOT, project_name="Orchestrator"))
