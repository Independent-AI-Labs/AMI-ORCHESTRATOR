#!/usr/bin/env python
"""Test runner for orchestrator root (delegates to base).

Keeps sys.path handling isolated to runner level.
"""

import sys
from pathlib import Path

ORCHESTRATOR_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ORCHESTRATOR_ROOT))

from base.scripts.run_tests import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(project_root=ORCHESTRATOR_ROOT, project_name="Orchestrator"))
