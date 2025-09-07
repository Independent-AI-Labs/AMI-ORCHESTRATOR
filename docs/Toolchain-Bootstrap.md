# Toolchain Bootstrap (Trusted)

Objective: Provide a robust, cross-platform, trusted path to obtain `uv` and a Python 3.12 toolchain. Modules then manage their own virtual environments via `uv`.

Trust model
- Prefer OS package managers with signed catalogs (Homebrew, winget, apt where applicable).
- Otherwise, use Astral’s official installers over HTTPS for `uv`.
- Provision Python runtimes via `uv python install 3.12` (python-build-standalone).

One-time bootstrap
```bash
python scripts/bootstrap_uv_python.py --auto
```

Manual alternatives
- macOS: `brew install uv`
- Windows: `winget install -e --id Astral-Software.UV` or `choco install uv`
- Linux/macOS fallback: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Windows fallback (PowerShell): `irm https://astral.sh/uv/install.ps1 | iex`

Why no root venv?
- Each module is independently runnable and self-contained; orchestrator only ensures the toolchain is present and calls `uv run --python 3.12 module_setup.py` inside each module.

Offline/air-gapped notes
- Mirror `uv` and python-build-standalone artifacts into an internal registry.
- Configure `UV_INDEX_URL`/`PIP_INDEX_URL` to point to internal package repositories.
- Vendor minimal wheels where needed for bootstrap-only steps.
