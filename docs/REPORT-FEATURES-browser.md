# Browser Module Features Report

## MCP Servers

### Chrome MCP Server
- **File**: `browser/backend/mcp/chrome/chrome_server.py`
- **Class**: `ChromeFastMCPServer`
- **Purpose**: Provides Chrome browser automation through MCP protocol
- **Functionality**:
  - Browser instance lifecycle management (launch, terminate, list, get_active)
  - Session persistence (save, restore, list_sessions, delete_session, rename_session)
  - Navigation and tab management (goto, back, forward, refresh, open_tab, close_tab, switch_tab)
  - Element interaction (click, type, select, hover, scroll, press, wait)
  - DOM inspection (get_html, exists, get_attribute)
  - Content extraction (get_text, get_cookies) with chunking support
  - Screenshot capture (screenshot, element_screenshot)
  - JavaScript execution with security validation
  - Web search functionality
  - Download and screenshot management
  - React component interaction
  - Browser profile management (create, delete, list, copy)
- **Transport**: Supports stdio, sse, streamable-http
- **Shell Exposure**:
  - `ami-browser-mcp` - Launch Chrome MCP server via setup-shell.sh function
  - `ami-browser-mcp --transport stdio` - Launch with specific transport
  - `ami-browser-mcp --data-root /path/to/data` - Launch with specific data root
  - Alias: `abm` (requires additional alias in setup-shell.sh)

## Tools and Scripts

### Core Scripts
1. **run_chrome.py** - Chrome MCP server runner
   - **Location**: `browser/scripts/run_chrome.py`
   - **Functionality**: Runs the Chrome MCP server with configurable data root and options
   - **Shell Exposure**:
     - `ami-browser-mcp` - Primary access through setup-shell.sh function
     - Direct access: `ami-run browser/scripts/run_chrome.py [options]`
     - Options: `--transport [stdio|sse|streamable-http]`, `--data-root PATH`
     - Default data root: `browser/data`

2. **setup_chrome.py** - Chrome setup script
   - **Location**: `browser/scripts/setup_chrome.py`
   - **Functionality**: Sets up Chrome dependencies and configurations
   - **Shell Exposure**:
     - `ami-browser-setup` - Function in setup-shell.sh (requires implementation)
     - Direct access: `ami-run browser/scripts/setup_chrome.py`
     - Alias: `abs` (requires additional alias in setup-shell.sh)

3. **install_chrome_deps.sh** - Chrome dependencies installer
   - **Location**: `browser/scripts/install_chrome_deps.sh`
   - **Functionality**: Shell script to install Chrome and related dependencies
   - **Shell Exposure**:
     - `ami-browser-install-deps` - Function in setup-shell.sh (requires implementation)
     - Direct access: `ami-run browser/scripts/install_chrome_deps.sh`
     - Alias: `abid` (requires additional alias in setup-shell.sh)

### MCP Tools (Core Functionality)
- **Location**: `browser/backend/mcp/chrome/tools/`
- **Functionality**:
  - `session_tool`: Manage browser sessions and lifecycle
  - `navigate_tool`: Handle navigation and tab management
  - `interact_tool`: Interact with page elements (click, type, etc.)
  - `inspect_tool`: Inspect DOM structure and element properties
  - `extract_tool`: Extract content with optional chunking
  - `capture_tool`: Take screenshots
  - `execute_tool`: Execute JavaScript with security validation
  - `storage_tool`: Manage downloads and screenshots
  - `react_tool`: React-specific component interactions
  - `profile_tool`: Browser profile management
  - `search_tools`: Web search functionality
- **Shell Exposure**: Exposed through Chrome MCP server, accessed via MCP client

### Facade Tools
- **Location**: `browser/backend/mcp/chrome/tools/facade/`
- **Functionality**:
  - Organized by feature: capture, execution, extraction, inspection, interaction, navigation, profile, react, session, storage
  - Provides clean interface between MCP server and ChromeManager
- **Shell Exposure**: Internal organization layer, not directly exposed to shell

### Chrome Manager System
- **Location**: `browser/backend/core/management/manager.py`
- **Class**: `ChromeManager`
- **Functionality**:
  - Manages browser instances (both standalone and pool-based)
  - Handles profile management
  - Session persistence capabilities
  - Worker pool management for browser instances
  - Instance lifecycle management
  - Security configuration and anti-detection features
  - Download and screenshot handling
- **Shell Exposure**:
  - Profile management through `ami-browser-profile` function
  - Session management accessible via Chrome MCP server

## CLI Features and Aliases

### Available Aliases
1. `ami-browser-mcp` - Launch browser-specific MCP server via setup-shell.sh function
2. `ami-browser-test` - Run browser module tests (aliased as `abr`)
3. `ami-browser-profile` - Browser profile management (aliased as `abp`)
4. `ami-browser-setup` - Chrome setup (needs implementation)
5. `ami-browser-install-deps` - Chrome dependencies installation (needs implementation)

### Shell Exposures to Implement
1. **Enhanced MCP server access**:
   - Add transport selection options to `ami-browser-mcp`
   - Add data root configuration
   - Add server status and management functions
   - Add server configuration tools

2. **Chrome setup and management**:
   - `ami-browser-setup` function for Chrome configuration
   - `ami-browser-install-deps` function for dependencies
   - Configuration validation tools

3. **Browser instance management**:
   - Instance start/stop/status commands
   - Session management utilities
   - Profile management enhancement

4. **MCP server management**:
   - Server monitoring and health checks
   - Log viewing and debugging tools
   - Configuration validation

### Required Exposures
1. Chrome MCP server access through `ami-browser-mcp` function
2. Browser instance management commands
3. Profile creation and management tools via `ami-browser-profile`
4. Chrome dependency installation script (needs implementation)
5. Browser testing capabilities via `ami-browser-test`
6. Chrome setup and configuration tools (needs implementation)
7. Session management utilities (needs implementation)

## Exposed Functionality for Other Modules

### Browser Automation Framework
- Complete browser automation through MCP protocol
- Multi-instance support with worker pool
- Session persistence and restoration
- Security and anti-detection features
- Profile management system
- React component interaction capabilities

### Core Services
- Chrome instance lifecycle management
- Download and screenshot handling
- JavaScript execution with validation
- DOM inspection and content extraction
- Navigation and tab management
- Web search integration
- Element interaction tools
- Content extraction with chunking support

## Shell Integration Requirements

### Functions to Add to setup-shell.sh
1. **ami-browser-setup** - Function to setup Chrome dependencies and configurations
2. **ami-browser-install-deps** - Function to install Chrome dependencies
3. **ami-browser-status** - Function to check Chrome server status
4. **ami-browser-logs** - Function to view Chrome server logs
5. **ami-browser-config** - Function to manage Chrome configuration
6. **ami-browser-sessions** - Function to manage browser sessions
7. **ami-browser-profiles** - Function to list and manage browser profiles
8. **ami-browser-instance** - Function to manage Chrome instances

### Aliases to Add
1. `abs` - Alias for `ami-browser-setup`
2. `abid` - Alias for `ami-browser-install-deps`
3. `abst` - Alias for `ami-browser-status`
4. `abl` - Alias for `ami-browser-logs`
5. `abc` - Alias for `ami-browser-config`
6. `absn` - Alias for `ami-browser-sessions`
7. `abpr` - Alias for `ami-browser-profiles`
8. `abi` - Alias for `ami-browser-instance`

### Enhanced Functionality
1. Add server management capabilities to `ami-browser-mcp` (start, stop, status, logs)
2. Add configuration validation and management tools
3. Add session management commands (list, save, restore, delete)
4. Add profile management commands (list, create, delete, copy)
5. Add instance monitoring and health check capabilities
6. Add debugging and development utilities
7. Add data root management and cleanup utilities