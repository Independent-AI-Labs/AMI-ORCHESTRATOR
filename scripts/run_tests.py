#!/usr/bin/env python
"""Test runner for orchestrator root."""

import sys
from pathlib import Path

# Get orchestrator root and ensure it's on sys.path before importing base
ORCHESTRATOR_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from base.scripts.run_tests import main  # noqa: E402

if __name__ == "__main__":
    # Run tests using base test runner with orchestrator root
    sys.exit(main(project_root=ORCHESTRATOR_ROOT, project_name="Orchestrator"))
