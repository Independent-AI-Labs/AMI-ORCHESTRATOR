# Files Module Features Report

## MCP Servers

### Filesys MCP Server
- **File**: `files/backend/mcp/filesys/filesys_server.py`
- **Class**: `FilesysFastMCPServer`
- **Purpose**: Provides comprehensive filesystem operations through MCP protocol
- **Functionality**:
  - Filesystem operations (list, create, find, read, write, delete, modify, replace)
  - Git operations (status, stage, unstage, commit, diff, history, restore, fetch, pull, push, merge_abort)
  - Python execution (run, run_background, task_status, task_cancel, list_tasks)
  - Document processing (index, read, read_image) with multimodal LLM support
  - Metadata management (list, read, write, delete, git)
  - LLM validation for Python file write operations
  - Session-based validation with fail-open behavior
- **Transport**: Supports stdio, sse, streamable-http
- **Shell Exposure**:
  - `ami-files-mcp` - Primary access through setup-shell.sh function
  - `ami-files-mcp --transport stdio` - Launch with specific transport
  - `ami-files-mcp --root-dir /path/to/root` - Launch with specific root directory
  - `ami-files-mcp --response-format json` - Launch with specific response format
  - Direct access: `ami-run files/scripts/run_filesys.py [options]`
  - Alias: `afm` (requires additional alias in setup-shell.sh)

## Tools and Scripts

### Core Scripts
1. **run_filesys.py** - Filesys MCP server runner
   - **Location**: `files/scripts/run_filesys.py`
   - **Functionality**: Runs the Filesys MCP server with configurable root directory and transport
   - **Shell Exposure**:
     - `ami-files-mcp` - Primary access through setup-shell.sh function
     - Direct access: `ami-run files/scripts/run_filesys.py [options]`
     - Options: `--root-dir PATH`, `--transport [stdio|sse|streamable-http]`, `--response-format [json|yaml]`
     - Default root directory: `.` (current directory)

2. **run_filesys_fastmcp.py** - Alternative Filesys MCP server runner
   - **Location**: `files/scripts/run_filesys_fastmcp.py`
   - **Functionality**: Alternative runner for Filesys MCP server (exact content varies)
   - **Shell Exposure**:
     - Alternative access: `ami-run files/scripts/run_filesys_fastmcp.py [options]`
     - Options similar to main runner

3. **convert_extensions.py** - File extension conversion utility
   - **Location**: `files/scripts/convert_extensions.py`
   - **Functionality**: Utility for converting file extensions (purpose based on name)
   - **Shell Exposure**:
     - `ami-convert-extensions` - Function in setup-shell.sh (requires implementation)
     - Direct access: `ami-run files/scripts/convert_extensions.py [options]`
     - Alias: `ace` (requires additional alias in setup-shell.sh)

### MCP Tools (Core Functionality)
- **Location**: `files/backend/mcp/filesys/tools/facade/`
- **Functionality**:
  - `filesystem.py`: Filesystem operations with LLM validation for Python files
  - `git.py`: Git operations with auto-commit and test-on-push functionality
  - `python.py`: Python execution with background task support and task management
  - `document.py`: Document processing with structured data extraction and multimodal image analysis
  - `metadata.py`: Metadata management with git versioning support
- **Shell Exposure**: Through MCP server, accessed via MCP client tools

### Core Tools Implementation
- **Location**: `files/backend/mcp/filesys/tools/`
- **Files**:
  - `filesystem_tools.py`: Implementation of filesystem operations
  - `git_tools.py`: Implementation of git operations
  - `python_tools.py`: Implementation of Python execution tools
  - `document_tools.py`: Implementation of document processing tools
  - `metadata_tools.py`: Implementation of metadata management tools
- **Shell Exposure**: Through MCP server operations

### Filesystem Services
- **Location**: `files/backend/services/` (if exists)
- **Functionality**: Backend services for file operations
- **Shell Exposure**: Through MCP server operations

### File Extractors and Generators
- **Location**: `files/backend/extractors/` and `files/backend/generators/`
- **Functionality**: Tools for extracting and generating content from various file formats
- **Shell Exposure**: Through document processing tools

### Model Definitions
- **Location**: `files/backend/models/`
- **Functionality**: Data models for file operations
- **Shell Exposure**: Internal implementation, not directly exposed

## CLI Features and Aliases

### Available Aliases
1. `ami-files-mcp` - Launch files-specific MCP server (FilesysFastMCPServer)
2. `ami-files-test` - Run files module tests (aliased as `aft`)
3. `ami-files-doc` - Document processing tool with multiple subcommands:
   - `adocr` - Read document (`ami-files-doc read`)
   - `adoci` - Index document (`ami-files-doc index`)
   - `adocimg` - Read image (`ami-files-doc read-image`)

### Shell Exposures to Implement
1. **Enhanced MCP server access**:
   - Add transport selection options to `ami-files-mcp`
   - Add root directory and response format configuration
   - Add server status and management functions
   - Add server configuration tools

2. **File operations**:
   - Direct file operation commands (ls, find, read, write, etc.)
   - File search and content extraction tools
   - File extension conversion utilities

3. **Git operations**:
   - Direct git command equivalents through MCP
   - Git workflow automation tools
   - Status and history management

4. **Python execution tools**:
   - Direct Python script execution commands
   - Background task management
   - Task status and cancellation tools

5. **Document processing**:
   - Enhanced `ami-files-doc` with more options
   - Format conversion and extraction tools
   - Batch document processing

### Required Exposures
1. Filesys MCP server for comprehensive filesystem operations through `ami-files-mcp`
2. Document processing with multimodal capabilities through `ami-files-doc`
3. Git workflow automation through MCP server operations
4. Python execution with background task support through MCP server
5. Metadata management with versioning through MCP server
6. File operations with LLM validation for safety through MCP server
7. File search and content extraction tools through MCP server and utilities
8. Direct file operation utilities (needs implementation)
9. Enhanced document processing tools through `ami-files-doc`

## Exposed Functionality for Other Modules

### Filesystem Operations Framework
- Complete MCP-based filesystem operations
- LLM-validated Python file modification
- File search and content extraction
- Directory traversal and listing
- File read/write with encoding support
- Range-based content extraction (lines, offsets)

### Version Control Integration
- Git operations through MCP protocol
- Automated commit workflow with auto-staging
- Pre-push testing enforcement
- Git history and status management
- Branch and remote operations

### Document Processing System
- Document indexing for search
- Structured data extraction with templates
- Table and image extraction
- Multimodal image analysis with OCR
- Chart data extraction
- Instruction-based document processing

### Python Execution Environment
- Safe Python script execution
- Background task execution with monitoring
- Task cancellation and status checking
- Process isolation and timeout management
- Working directory specification

### Metadata Management
- Progress and feedback logging
- .meta directory management
- Git-based metadata versioning
- Module-specific artifact tracking
- Content-based metadata operations

### Configuration Management
- Root directory configuration for operations
- Session-based validation system
- Response format options (JSON/YAML)
- Transport protocol selection

## Shell Integration Requirements

### Functions to Add to setup-shell.sh
1. **ami-files-mcp** - Enhanced function with transport, root-dir, and response-format options
2. **ami-convert-extensions** - Function to convert file extensions
3. **ami-files-find** - Function to find files with search criteria
4. **ami-files-git** - Function to run git operations through MCP
5. **ami-files-python** - Function to run Python scripts through MCP
6. **ami-files-task** - Function to manage background tasks
7. **ami-files-meta** - Function to manage metadata
8. **ami-files-status** - Function to check server status
9. **ami-files-logs** - Function to view server logs
10. **ami-files-config** - Function to manage server configuration

### Aliases to Add
1. `afm` - Alias for `ami-files-mcp`
2. `ace` - Alias for `ami-convert-extensions`
3. `aff` - Alias for `ami-files-find`
4. `afg` - Alias for `ami-files-git`
5. `afp` - Alias for `ami-files-python`
6. `aftk` - Alias for `ami-files-task`
7. `afmt` - Alias for `ami-files-meta`
8. `afst` - Alias for `ami-files-status`
9. `afl` - Alias for `ami-files-logs`
10. `afc` - Alias for `ami-files-config`

### Enhanced Functionality
1. Add server management capabilities to `ami-files-mcp` (start, stop, status, logs)
2. Add file operation utilities (ls, find, read, write, etc.)
3. Add direct git command equivalents
4. Add Python execution utilities with task management
5. Add document processing with advanced options (tables, images, OCR)
6. Add file search and content extraction capabilities
7. Add background task management tools
8. Add metadata management utilities
9. Add configuration validation and management tools