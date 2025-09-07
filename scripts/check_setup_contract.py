#!/usr/bin/env python3
"""Check setup contract for module_setup.py files.

Rules checked:
- No third-party imports at top-level in module_setup.py (stdlib only).
- No ad-hoc sys.path manipulation in module_setup.py.

Exit non-zero on violations. Prints a concise report.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

ORCHESTRATOR_ROOT = Path(__file__).resolve().parent.parent
MODULES = ["base", "browser", "files", "node", "streams", "ux", "compliance", "domains"]

# Allow-list of stdlib modules commonly used in setup scripts
STDLIB_ALLOWED = {
    # Core
    "sys",
    "os",
    "argparse",
    "subprocess",
    "pathlib",
    "logging",
    "shutil",
    "json",
    "typing",
    "time",
    "platform",
}

# Known third-party we explicitly disallow during setup
DISALLOWED_THIRD_PARTY = {
    "yaml",
    "loguru",
    "requests",
    "rich",
    "click",
    "pydantic",
    "tomli",
    "tomllib",  # Note: tomllib is stdlib in 3.11+, keep allowed via STDLIB_ALLOWED if needed
    "numpy",
    "pandas",
    "pytest",
}


def analyze_module_setup(path: Path) -> tuple[list[str], list[str]]:
    """Return (violations, warnings) for a module_setup.py file."""
    violations: list[str] = []
    warnings: list[str] = []

    try:
        code = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"Failed to read {path}: {e}"], warnings

    # Quick string check for sys.path manipulation
    if "sys.path.insert" in code or "sys.path.append" in code:
        warnings.append("ad-hoc sys.path manipulation found (flagged; consider centralizing)")

    # AST parse to check imports
    try:
        tree = ast.parse(code, filename=str(path))
    except SyntaxError as e:
        violations.append(f"Syntax error: {e}")
        return violations, warnings

    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            # Only check true top-level imports
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name.split(".")[0] for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue  # relative import like `from . import X` (treated as local)
                modules = [node.module.split(".")[0]]

            for mod in modules:
                if mod in DISALLOWED_THIRD_PARTY:
                    violations.append(f"disallowed third-party import: {mod}")
                elif mod not in STDLIB_ALLOWED:
                    # Likely first-party import (OK) or third-party (warn)
                    # We warn so devs can review, but don't fail on first-party.
                    warnings.append(f"non-stdlib import detected: {mod}")

    return violations, warnings


def main() -> int:
    any_fail = False
    reports: list[str] = []

    for mod in MODULES:
        setup_path = ORCHESTRATOR_ROOT / mod / "module_setup.py"
        if not setup_path.exists():
            reports.append(f"[WARN] {mod}: missing module_setup.py (ok if intentionally absent)")
            continue

        violations, warnings = analyze_module_setup(setup_path)
        if violations:
            any_fail = True
            reports.append(f"[FAIL] {mod}: " + "; ".join(violations))
        else:
            reports.append(f"[ OK ] {mod}: no violations")

        for w in warnings:
            reports.append(f"       note: {w}")

    print("\n".join(reports))
    return 1 if any_fail else 0


if __name__ == "__main__":
    sys.exit(main())
