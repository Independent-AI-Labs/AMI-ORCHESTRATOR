# Base Module Features Report

## MCP Servers

### DataOps MCP Server
- **File**: `base/backend/mcp/dataops/dataops_server.py`
- **Class**: `DataOpsFastMCPServer`
- **Purpose**: Provides DataOps functionality through MCP protocol
- **Functionality**:
  - Create, read, update, delete StorageModel instances
  - Query operations with structured queries
  - Raw query execution on storage backends
  - Storage validation and listing
  - Model-to-storage mapping inspection
- **Transport**: Supports stdio, sse, streamable-http
- **Shell Exposure**:
  - `ami-base-mcp dataops` - Launch DataOps MCP server
  - `ami-base-mcp dataops --transport stdio` - Launch with specific transport
  - Alias: `abm dataops` (requires additional alias in setup-shell.sh)

### SSH MCP Server
- **File**: `base/backend/mcp/ssh/ssh_server.py`
- **Class**: `SSHFastMCPServer`
- **Purpose**: Provides SSH operations through MCP protocol
- **Functionality**:
  - Execute SSH commands on remote servers
  - Upload files via SSH
  - Download files via SSH
  - SSH server information and capabilities
- **Transport**: Supports stdio, sse, streamable-http
- **Shell Exposure**:
  - `ami-base-mcp ssh` - Launch SSH MCP server
  - `ami-base-mcp ssh --transport stdio` - Launch with specific transport
  - Alias: `abm ssh` (requires additional alias in setup-shell.sh)

### Base MCP Server Framework
- **File**: `base/backend/mcp/fastmcp_server_base.py`
- **Class**: `FastMCPServerBase`
- **Purpose**: Abstract base class for building MCP servers
- **Functionality**:
  - Provides base infrastructure for MCP server implementations
  - Tool registration framework
  - Resource registration framework
- **Shell Exposure**: Used by other MCP server implementations, not directly exposed

## Tools and Scripts

### Core Scripts
1. **run_mcp.py** - Unified MCP runner dispatcher
   - **Location**: `base/scripts/run_mcp.py`
   - **Functionality**: Dispatches to specific MCP runners (dataops, ssh, chrome, filesys)
   - **Shell Exposure**:
     - `ami-base-mcp [server] [args...]` - Unified entry point for all MCP servers
     - Supported servers: dataops, ssh, chrome, filesys
     - Usage: `ami-base-mcp dataops`, `ami-base-mcp ssh`, etc.

2. **run_dataops_fastmcp.py** - DataOps MCP server runner
   - **Location**: `base/scripts/run_dataops_fastmcp.py`
   - **Functionality**: Runs the DataOps MCP server with configurable transport
   - **Shell Exposure**:
     - `ami-base-mcp dataops [args]` - Primary access through unified dispatcher
     - Direct access: `ami-run base/scripts/run_dataops_fastmcp.py [args]`
     - Options: `--transport [stdio|sse|streamable-http]`

3. **run_ssh_fastmcp.py** - SSH MCP server runner
   - **Location**: `base/scripts/run_ssh_fastmcp.py`
   - **Functionality**: Runs the SSH MCP server
   - **Shell Exposure**:
     - `ami-base-mcp ssh [args]` - Primary access through unified dispatcher
     - Direct access: `ami-run base/scripts/run_ssh_fastmcp.py [args]`

4. **run_secrets_broker.py** - Secrets broker service
   - **Location**: `base/scripts/run_secrets_broker.py`
   - **Functionality**: Launch the secrets broker service using uvicorn
   - **Shell Exposure**:
     - `ami-base-secrets-broker` - Function in setup-shell.sh (requires implementation)
     - Options: `--host HOST --port PORT`
     - Alias: `absb` (requires additional alias in setup-shell.sh)

5. **run_tests.py** - Smart test runner
   - **Location**: `base/scripts/run_tests.py`
   - **Functionality**: Auto-discovers modules and runs tests with parallel execution support
   - **Shell Exposure**:
     - `ami-base-test [module] [pytest-args]` - Run tests for base and other modules
     - Alias: `abt [module] [pytest-args]`
     - Example: `ami-base-test base`, `ami-base-test -- --verbose`

6. **check_storage.py** - Storage validation tool
   - **Location**: `base/scripts/check_storage.py`
   - **Functionality**: Validates DataOps storage backends defined in storage-config.yaml
   - **Shell Exposure**:
     - `ami-base-storage-check [options]` - Validate storage backends
     - Alias: `abs` [options]
     - Example: `ami-base-storage-check --verbose`

### DataOps Tools (MCP Tools)
- **Location**: `base/backend/mcp/dataops/tools/`
- **Functionality**:
  - `dataops_create_tool`: Create StorageModel instances
  - `dataops_read_tool`: Read StorageModel instances by UID
  - `dataops_update_tool`: Update StorageModel instances
  - `dataops_delete_tool`: Delete StorageModel instances by UID
  - `dataops_query_tool`: Query StorageModel instances with structured queries
  - `dataops_raw_query_tool`: Execute raw queries on storage backends
  - `dataops_info_tool`: Get information about StorageModel and operations
  - `storage_list_tool`: List configured storage backends
  - `storage_validate_tool`: Validate storage backend connectivity
  - `storage_models_tool`: Show model-to-storage mappings
- **Shell Exposure**: Exposed through DataOps MCP server, accessed via MCP client

### SSH Tools (MCP Tools)
- **Location**: `base/backend/mcp/ssh/tools/`
- **Functionality**:
  - `ssh_execute_tool`: Execute SSH commands on remote servers
  - `ssh_upload_tool`: Upload files via SSH
  - `ssh_download_tool`: Download files via SSH
  - `ssh_info_tool`: Get SSH server information
- **Shell Exposure**: Exposed through SSH MCP server, accessed via MCP client

### Data Operations Core
- **Location**: `base/backend/dataops/`
- **Functionality**:
  - Data acquisition, storage implementations
  - Model definitions and security
  - Storage registry and validation
  - Services and utilities for data operations
- **Shell Exposure**:
  - Configuration via `storage-config.yaml`
  - Validation through `ami-base-storage-check`

### Utilities
- **Location**: `base/backend/utils/`
- **Functionality**:
  - Runner bootstrapping (`runner_bootstrap.py`)
  - Environment setup and path management
  - Path resolution utilities
  - Import setup utilities
- **Shell Exposure**: Internal utilities, not directly exposed to shell

## CLI Features and Aliases

### Available Aliases
1. `ami-base-mcp` - Launch base-specific MCP server with server type selection (dataops, ssh, chrome, filesys)
2. `ami-base-test` - Run base module tests (aliased as `abt`)
3. `ami-base-storage-check` - Check base module storage backends (aliased as `abs`)
4. `ami-base-secrets-broker` - Launch secrets broker service (needs implementation)
5. `ami-base-run` - Generic runner for base scripts (needs implementation)

### Shell Exposures to Implement
1. **Enhanced MCP dispatcher**:
   - Add support for server-specific arguments
   - Add server status and management functions
   - Add server configuration tools

2. **Secrets broker management**:
   - `ami-base-secrets-broker` function
   - Start/stop/status commands
   - Configuration management

3. **Storage management**:
   - Enhanced storage validation tools
   - Storage configuration utilities
   - Storage backend management

4. **MCP server management**:
   - Server monitoring and health checks
   - Log viewing and debugging tools
   - Configuration validation

### Required Exposures
1. Unified MCP server access through `ami-base-mcp` dispatcher
2. Test running capabilities with module auto-discovery via `ami-base-test`
3. Storage validation and configuration tools via `ami-base-storage-check`
4. Secrets broker service management (needs implementation)
5. DataOps operations through MCP protocol
6. SSH operations through MCP protocol
7. Server status and monitoring tools (needs implementation)

## Exposed Functionality for Other Modules

### Framework Components
- MCP server base class for other modules to extend
- Storage registry and validation framework
- Test runner infrastructure with auto-discovery
- Environment and path setup utilities
- Secrets management and broker services

### Shared Services
- DataOps infrastructure for all modules
- SSH operations for remote management
- Storage validation and configuration
- Secrets broker for secure credential handling

## Shell Integration Requirements

### Functions to Add to setup-shell.sh
1. **ami-base-secrets-broker** - Function to start/stop secrets broker
2. **ami-base-run** - Generic function to run base scripts with proper environment
3. **ami-base-status** - Function to check status of base services
4. **ami-base-logs** - Function to view base module logs
5. **ami-base-config** - Function to manage base module configuration

### Aliases to Add
1. `absb` - Alias for `ami-base-secrets-broker`
2. `abr` - Alias for `ami-base-run`
3. `abs` - Already exists for storage check
4. `abst` - Alias for `ami-base-status`
5. `abl` - Alias for `ami-base-logs`
6. `abc` - Alias for `ami-base-config`

### Enhanced Functionality
1. Add server management capabilities to `ami-base-mcp` (start, stop, status, logs)
2. Add configuration validation and management tools
3. Add service monitoring and health check capabilities
4. Add debugging and development utilities