# Nodes Module Features Report

## MCP Servers

### Launcher MCP Server
- **File**: `nodes/backend/mcp/launcher/launcher_server.py`
- **Class**: `LauncherFastMCPServer`
- **Purpose**: Exposes launcher supervision API through MCP protocol
- **Functionality**:
  - List launcher profiles from service manifest
  - Retrieve launcher status for services
  - Start services with profile awareness
  - Stop services with optional force option
- **Transport**: Supports stdio, sse, streamable-http
- **CLI Access**: `ami-run nodes/scripts/run_launcher_mcp.py [--manifest PATH] [--transport stdio|sse|streamable-http]`

### Node Setup MCP Server
- **File**: `nodes/backend/mcp/setup/setup_server.py`
- **Class**: `NodeSetupFastMCPServer`
- **Purpose**: Exposes node setup automation through MCP protocol
- **Functionality**:
  - Run configured pre-install scripts and commands
  - Run module setup and verification with optional testing
  - Run setup for individual modules with configuration propagation
  - List managed processes with their status
  - Check status of individual managed processes
  - Start and stop managed processes (with optional force)
- **Transport**: Supports stdio, sse, streamable-http

## Tools and Scripts

### Core Scripts
1. **run_launcher_mcp.py** - Launcher MCP server runner
   - **Location**: `nodes/scripts/run_launcher_mcp.py`
   - **Functionality**: Runs the Launcher MCP server with configurable manifest and transport
   - **CLI Access**: `ami-run nodes/scripts/run_launcher_mcp.py [--manifest PATH] [--transport stdio|sse|streamable-http]`

2. **setup_service.py** - Node setup service automation
   - **Location**: `nodes/scripts/setup_service.py`
   - **Functionality**: Implements node setup automation functionality
   - **CLI Access**: `ami-run nodes/scripts/setup_service.py`

3. **launch_services.py** - Service launcher
   - **Location**: `nodes/scripts/launch_services.py`
   - **Functionality**: Launches services based on manifest configuration
   - **CLI Access**: `ami-run nodes/scripts/launch_services.py`

4. **preinstall.sh** - Pre-installation script
   - **Location**: `nodes/scripts/preinstall.sh`
   - **Functionality**: Shell script for pre-installation steps
   - **CLI Access**: `ami-run nodes/scripts/preinstall.sh`

### Core Components
- **Launcher System** (`nodes/backend/launcher/`):
  - `supervisor.py`: Service supervision and management
  - `loader.py`: Service manifest loading and parsing
  - `models.py`: Service and process models
  - `state_manager.py`: Process state management
  - `validator.py`: Service configuration validation
  - `health.py`: Health checking capabilities
  - `adapters/`: Service adapters (local, mcp)

- **Setup System** (`nodes/backend/setup/`):
  - `service.py`: Node setup service implementation
  - `config.py`: Configuration management (if exists)

### MCP Tools (Core Functionality)
- **Launcher Tools** (`nodes/backend/mcp/launcher/tools.py`):
  - `list_profiles`: List launcher profiles from manifest
  - `service_status`: Retrieve launcher status for services
  - `start_services`: Start services with profile awareness
  - `stop_services`: Stop services with optional force option

- **Setup Tools** (`nodes/backend/mcp/setup/setup_server.py`):
  - `setup_preinstall`: Run pre-install scripts and commands
  - `setup_verify`: Run module setup and verification (with optional testing)
  - `setup_module`: Run setup for individual modules
  - `setup_process_list`: List managed processes with status
  - `setup_process_status`: Get status of individual managed processes
  - `setup_process_start`: Start managed processes
  - `setup_process_stop`: Stop managed processes (with optional force)

### Production Components
- **Location**: `nodes/production/`
- **Functionality**:
  - `python_strategy.py`: Python deployment strategy
  - `npm_strategy.py`: NPM deployment strategy
  - `generic_strategy.py`: Generic deployment strategy
  - `production_monitor.py`: Production monitoring capabilities

## CLI Features and Aliases

### Available Aliases
1. `ami-nodes-mcp` - Launch nodes-specific MCP server (from setup-shell.sh)
2. `ami-nodes-test` - Run nodes module tests (aliased as `ant`)
3. `ami-nodes-status` - Check node status (aliased as `ans`)

### Required Exposures
1. Service launcher and supervisor functionality
2. Node setup automation tools
3. Process management (start, stop, status)
4. Service manifest management
5. Pre-installation automation
6. Module verification and testing

## Exposed Functionality for Other Modules

### Service Management Framework
- Complete service launcher with profile awareness
- Process supervision and health management
- Service manifest configuration and parsing
- Process state management and monitoring
- Graceful start/stop with optional force operations

### Node Setup Automation
- Pre-installation script execution
- Module setup and verification
- Configuration propagation across modules
- Test execution during setup
- Process lifecycle management
- Status monitoring for managed processes

### Deployment Strategies
- Python application deployment
- NPM package deployment
- Generic deployment mechanisms
- Production monitoring capabilities
- Universal deployer framework

## Shell Integration Requirements

### Current Shell Exposure
1. **ami-nodes-mcp** - Placeholder for nodes-specific MCP server (not implemented)
2. **ami-nodes-test** - Run nodes module tests (aliased as `ant`)
3. **ami-nodes-status** - Check node status (aliased as `ans`)
4. **ami-nodes-list** - Function to list nodes (needs implementation)

### Functions to Add to setup-shell.sh
1. **ami-launcher-mcp** - Function to run launcher MCP server with manifest support
   - `ami-launcher-mcp --manifest PATH` - Launch with specific manifest
   - `ami-launcher-mcp --transport stdio` - Launch with specific transport
   - Default: Uses default manifest location

2. **ami-setup-mcp** - Function to run setup MCP server
   - `ami-setup-mcp --transport stdio` - Launch with specific transport
   - For node setup automation

3. **ami-launch-services** - Function to launch services directly
   - `ami-run nodes/scripts/launch_services.py [options]` - Direct access
   - Launch services based on manifest configuration

4. **ami-setup-service** - Function to run service setup automation
   - `ami-run nodes/scripts/setup_service.py [options]` - Direct access
   - Execute node setup automation

5. **ami-preinstall** - Function to run pre-installation steps
   - `ami-run nodes/scripts/preinstall.sh [options]` - Direct access
   - Execute pre-installation automation

6. **ami-node-status** - Enhanced function to check node status
   - `ami-node-status [node_name]` - Check specific node status
   - Replacement for current placeholder

7. **ami-deploy-python** - Function for Python deployment
   - Uses `python_strategy.py` for deployment

8. **ami-deploy-npm** - Function for NPM deployment
   - Uses `npm_strategy.py` for deployment

9. **ami-deploy-generic** - Function for generic deployment
   - Uses `generic_strategy.py` for deployment

10. **ami-production-monitor** - Function for production monitoring
    - Uses `production_monitor.py` for monitoring

### Aliases to Add
1. `alm` - Alias for `ami-launcher-mcp`
2. `asm` - Alias for `ami-setup-mcp`
3. `als` - Alias for `ami-launch-services`
4. `ass` - Alias for `ami-setup-service`
5. `api` - Alias for `ami-preinstall`
6. `ans` - Already exists for `ami-nodes-status`
7. `adpy` - Alias for `ami-deploy-python`
8. `adnpm` - Alias for `ami-deploy-npm`
9. `adgen` - Alias for `ami-deploy-generic`
10. `apm` - Alias for `ami-production-monitor`

### Required Shell Exposures for MCP Servers
1. **Launcher MCP Server Access**:
   - `ami-launcher-mcp` with manifest and transport options
   - Service management through MCP tools (list, start, stop, status)

2. **Setup MCP Server Access**:
   - `ami-setup-mcp` with transport options
   - Setup automation through MCP tools (preinstall, verify, module setup)

3. **Process Management**:
   - Process lifecycle management (start, stop, status, list)
   - Process configuration and monitoring
   - Service manifest management

### Enhanced Functionality
1. Add server management capabilities to launcher and setup MCP servers
2. Add service manifest management tools
3. Add process lifecycle management commands
4. Add pre-installation automation utilities
5. Add deployment strategy selection tools
6. Add node health monitoring and alerting
7. Add service configuration validation tools
8. Add module-based setup and verification commands
9. Add production monitoring and logging capabilities
10. Add graceful service startup/shutdown with dependency handling