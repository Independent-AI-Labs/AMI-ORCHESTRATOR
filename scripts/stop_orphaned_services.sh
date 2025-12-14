#!/usr/bin/env bash
"""Stop all orphaned services and containers that may be running."""

set -euo pipefail

echo "=== Stopping All Orphaned Services and Containers ==="

# 1. Stop all running podman containers
echo ">>> Stopping all running podman containers..."
CONTAINERS=$(podman ps -q 2>/dev/null)
if [ -n "$CONTAINERS" ]; then
    echo "Found running containers: $CONTAINERS"
    podman stop $CONTAINERS || true
else
    echo "No running containers found"
fi

# 2. Stop all podman-compose projects
echo ">>> Stopping all podman-compose services..."
for compose_file in docker-compose*.yml docker-compose*.yaml; do
    if [ -f "$compose_file" ]; then
        echo "Stopping services in $compose_file"
        podman-compose -f "$compose_file" down || true
    fi
done

# 3. Kill all Python processes (be careful with this - only if they're related to this project)
echo ">>> Stopping Python processes that may be related to services..."
# Kill Python processes running scripts from this project
pkill -f ".*AMI-ORCHESTRATOR.*\\.py" || true

# 4. Kill all Node.js processes 
echo ">>> Stopping Node.js processes..."
pkill -f "node.*AMI-ORCHESTRATOR" || true

# 5. Kill any uvicorn/FastAPI servers
echo ">>> Stopping uvicorn/FastAPI processes..."
pkill -f "uvicorn.*AMI-ORCHESTRATOR" || true

# 6. Kill any other potential service processes
echo ">>> Stopping other potential service processes..."
pkill -f "launcher" || true
pkill -f "monitoring_server" || true
pkill -f "run_launcher_mcp" || true

# 7. Clean up any remaining containers that might have been created
echo ">>> Removing stopped containers..."
podman container prune -f || true

# 8. List what's still running to verify
echo ">>> Checking for any remaining containers..."
podman ps

echo "=== Cleanup Complete ==="
echo "All known services and containers have been stopped."