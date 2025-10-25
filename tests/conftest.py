"""Root conftest.py for automation tests.

Prevents pytest from collecting submodule tests that have missing dependencies.
"""

import sys
from pathlib import Path

# Standard /base imports pattern
root_path = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_path))

# Collect only from tests/unit/
collect_ignore_glob = [
    "*/base/tests/*",
    "*/browser/tests/*",
    "*/compliance/tests/*",
    "*/domains/tests/*",
    "*/files/tests/*",
    "*/nodes/tests/*",
    "*/streams/tests/*",
    "*/ux/tests/*",
]
