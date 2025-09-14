#!/usr/bin/env python
"""Validation matrix for root + all modules.

Default: safe checks (no writes):
- Audit config drift (dry-run)
- Verify venv python versions
- Run ruff check + mypy per module

With --full (may modify files via pre-commit fixers):
- Run pre-commit run -a in each module
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODULES = ["base", "browser", "compliance", "domains", "files", "node", "streams", "ux"]


def run(cmd: list[str], cwd: Path | None = None) -> int:
    print(f"$ {' '.join(cmd)} (cwd={cwd or ROOT})")
    res = subprocess.run(cmd, cwd=str(cwd or ROOT), text=True, check=False)
    return res.returncode


def audit_configs() -> None:
    run(["python3", "module_setup.py", "--audit-configs"], cwd=ROOT)


def venv_versions() -> None:
    if (ROOT / ".venv/bin/python").exists():
        run([str(ROOT / ".venv/bin/python"), "-V"])  # root
    for m in MODULES:
        vpy = ROOT / m / ".venv/bin/python"
        if vpy.exists():
            run([str(vpy), "-V"])  # module


def _mypy_targets(module: str, mpath: Path) -> tuple[list[str], list[str]]:
    pkgs: list[str] = []
    paths: list[str] = []

    # Prefer package-qualified invocation(s) to avoid duplicate module names
    if (mpath / "__init__.py").exists():
        pkgs += ["-p", module]

    # Known nested packages (data-driven to reduce branching)
    nested: dict[str, list[str]] = {
        "files": ["backend"],
        "compliance": ["compliance"],
        "domains": ["risk", "sda"],
    }
    for sub in nested.get(module, []):
        if (mpath / sub).exists():
            pkgs += ["-p", f"{module}.{sub}"]

    # Also type-check common top-level dirs if present
    if (mpath / "tests").exists() and not (mpath / "tests" / "__init__.py").exists():
        paths.append("tests")
    if (mpath / "scripts").exists():
        paths.append("scripts")

    # Fallback to module root when nothing else
    if not pkgs and not paths:
        paths.append(".")
    return pkgs, paths


def safe_checks() -> None:
    # Modules: run checks from the module root
    for m in MODULES:
        mpath = ROOT / m
        if not mpath.exists():
            continue
        run(["uv", "run", "ruff", "check", "."], cwd=mpath)
        pkgs, paths = _mypy_targets(m, mpath)
        if pkgs:
            run(["uv", "run", "mypy", "--config-file", "mypy.ini", *pkgs], cwd=mpath)
        if paths:
            run(["uv", "run", "mypy", "--config-file", "mypy.ini", *paths], cwd=mpath)


def full_hooks() -> None:
    # Run module hooks (may fix files)
    for m in MODULES:
        mpath = ROOT / m
        if not mpath.exists():
            continue
        run(["uv", "run", "pre-commit", "run", "-a"], cwd=mpath)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--full", action="store_true", help="Run full pre-commit hooks (may modify files)")
    args = ap.parse_args()

    audit_configs()
    venv_versions()
    safe_checks()
    if args.full:
        full_hooks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
