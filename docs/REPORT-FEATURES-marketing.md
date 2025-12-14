# Marketing Domain Features Report (domains/marketing)

## MCP Servers

### Research MCP Server
- **File**: `domains/marketing/backend/mcp/research/server.py`
- **Class**: `ResearchMCPServer`
- **Purpose**: Provides simplified research functionality through MCP protocol for marketing domain
- **Functionality**:
  - Create research workspaces with requirements
  - List all research workspaces
  - Describe workspace contents and metadata
  - Define and update research schemas for validation
  - Capture and validate research records with provenance tracking
  - Append notes to research audit trails
  - List recent audit trail entries
- **Transport**: Supports stdio, sse, streamable-http
- **CLI Access**: Available through `ami-run domains/marketing/scripts/run_research_mcp.py`

## Tools and Scripts

### Core Scripts
1. **run_research_mcp.py** - Marketing research MCP server runner
   - **Location**: `domains/marketing/scripts/run_research_mcp.py`
   - **Functionality**: Runs the Research MCP server with configurable research root and transport
   - **CLI Access**: `ami-run domains/marketing/scripts/run_research_mcp.py [--research-root PATH] [--transport stdio|sse|streamable-http]`

2. **research-claude.sh** - Claude research automation script
   - **Location**: `domains/marketing/scripts/research-claude.sh`
   - **Functionality**: Shell script for automated research workflows with Claude
   - **CLI Access**: `ami-run domains/marketing/scripts/research-claude.sh`

### Core Components
- **Location**: `domains/marketing/backend/core/`
- **Functionality**:
  - `workspace.py`: Workspace creation and management functionality
  - `schema.py`: Schema definition and validation capabilities
  - `record.py`: Research record capture with validation and provenance
  - `audit.py`: Audit trail management and logging
  - `common.py`: Common utilities and structured logging

### MCP Tools (Core Functionality)
- **Location**: `domains/marketing/backend/mcp/research/server.py` (implemented as methods)
- **Functionality**:
  - `create_research_workspace`: Create new research workspace with directory structure
  - `list_research_workspaces`: List all available workspaces
  - `describe_research_workspace`: Get detailed workspace information
  - `define_research_schema`: Define or update research schemas for data validation
  - `capture_research_record`: Capture and validate research records with source verification
  - `append_research_audit`: Append notes to research audit trail
  - `list_research_audit`: List recent audit trail entries

### Research Settings
- **Location**: `domains/marketing/backend/mcp/research/settings.py`
- **Functionality**: Configuration management for research server including root directory settings

### Research Framework
- **Location**: `domains/marketing/backend/mcp/research/`
- **Files**:
  - `response.py`: Response handling for MCP tools
  - `SPEC-RESEARCH.md`: Specification for research MCP server

## CLI Features and Aliases

### Available Aliases
1. `ami-marketing-test` - Run marketing domain tests (aliased as `amt` from setup-shell.sh)
2. `ami-marketing-campaign` - Marketing campaign management (aliased as `amc` from setup-shell.sh)

### Required Exposures
1. Research MCP server access for marketing automation
2. Research workspace management tools
3. Schema definition and validation capabilities
4. Research record capture with provenance tracking
5. Audit trail management system
6. Marketing domain testing capabilities

## Exposed Functionality for Other Modules

### Research Framework
- Complete MCP-based research system for data collection
- Schema validation system for structured data
- Provenance tracking and audit capabilities
- Workspace management system
- Source verification and attachment handling
- Structured logging and audit trails

### Marketing-Specific Tools
- Automated research workflows with Claude integration
- Marketing-specific workspace templates
- Requirements management for marketing research
- Data categorization and organization by category
- Research progress tracking and audit