#!/usr/bin/env python
"""Run Filesys MCP server."""
import subprocess
import sys
from pathlib import Path

result = subprocess.run([sys.executable, str(Path(__file__).parent / "run_mcp.py"), "filesys"] + sys.argv[1:], check=False)
sys.exit(result.returncode)
