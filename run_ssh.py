#!/usr/bin/env python
"""Run SSH MCP server."""
import subprocess
import sys
from pathlib import Path

result = subprocess.run([sys.executable, str(Path(__file__).parent / "run_mcp.py"), "ssh"] + sys.argv[1:], check=False)
sys.exit(result.returncode)
