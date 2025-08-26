#!/usr/bin/env python
"""Run any MCP server from the orchestrator root."""

import subprocess
import sys
from pathlib import Path

# Run the generic MCP runner from base
base_runner = Path(__file__).parent / "base" / "scripts" / "run_mcp.py"

if not base_runner.exists():
    print(f"Error: Base MCP runner not found at {base_runner}")
    sys.exit(1)

# Pass through all arguments
result = subprocess.run([sys.executable, str(base_runner)] + sys.argv[1:], check=False)
sys.exit(result.returncode)
