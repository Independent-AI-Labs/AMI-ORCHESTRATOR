"""Root conftest.py for automation tests.

Prevents pytest from collecting submodule tests that have missing dependencies.
"""

import sys
from pathlib import Path

# Standard /base imports pattern - using proper traversal
current = Path(__file__).resolve().parent
while current != current.parent:
    if (current / ".git").exists():
        sys.path.insert(0, str(current))
        break
    current = current.parent

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
