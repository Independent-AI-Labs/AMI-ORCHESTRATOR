# Domains Module Features Report

## MCP Servers

### Marketing Research MCP Server
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
- **Shell Exposure**:
  - `ami-marketing-mcp` - Function in marketing setup-shell.sh (requires implementation)
  - `ami-run domains/marketing/scripts/run_research_mcp.py --transport stdio` - Direct access
  - `ami-run domains/marketing/scripts/run_research_mcp.py --research-root /path/to/research` - With custom root
  - Alias: `amm` (requires additional alias in setup-shell.sh)

## Tools and Scripts

### Core Scripts
1. **run_research_mcp.py** - Marketing research MCP server runner
   - **Location**: `domains/marketing/scripts/run_research_mcp.py`
   - **Functionality**: Runs the Research MCP server with configurable research root and transport
   - **Shell Exposure**:
     - `ami-marketing-mcp` - Primary access through marketing setup-shell.sh function (needs implementation)
     - Direct access: `ami-run domains/marketing/scripts/run_research_mcp.py [options]`
     - Options: `--research-root PATH`, `--transport [stdio|sse|streamable-http]`
     - Default research root: `domains/marketing/research`

2. **research-claude.sh** - Claude research automation script
   - **Location**: `domains/marketing/scripts/research-claude.sh`
   - **Functionality**: Shell script for automated research workflows with Claude
   - **Shell Exposure**:
     - `ami-research-claude` - Function in setup-shell.sh (requires implementation)
     - Direct access: `ami-run domains/marketing/scripts/research-claude.sh [options]`
     - Alias: `arc` (requires additional alias in setup-shell.sh)

### Marketing Core Components
- **Location**: `domains/marketing/backend/core/`
- **Functionality**:
  - `workspace.py`: Workspace creation and management functionality
  - `schema.py`: Schema definition and validation capabilities
  - `record.py`: Research record capture with validation and provenance
  - `audit.py`: Audit trail management and logging
  - `common.py`: Common utilities and structured logging
- **Shell Exposure**:
  - Through MCP server and related functions (require implementation)
  - `ami-research-workspace` - Workspace management (requires implementation)
  - `ami-research-schema` - Schema management (requires implementation)
  - `ami-research-record` - Record capture and validation (requires implementation)
  - `ami-research-audit` - Audit trail management (requires implementation)

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
- **Shell Exposure**: Through MCP server, accessed via MCP client tools

### Research Settings
- **Location**: `domains/marketing/backend/mcp/research/settings.py`
- **Functionality**: Configuration management for research server including root directory settings
- **Shell Exposure**:
  - `ami-research-config` - Function to manage research configuration (requires implementation)
  - Configuration via `--research-root` option in MCP server

### Research MCP Framework
- **Location**: `domains/marketing/backend/mcp/research/`
- **Files**:
  - `response.py`: Response handling for MCP tools
  - `SPEC-RESEARCH.md`: Specification for research MCP server
- **Shell Exposure**: Through MCP server operations

## CLI Features and Aliases

### Available Aliases
1. `ami-marketing-test` - Run marketing domain tests (aliased as `amt`)
2. `ami-marketing-campaign` - Marketing campaign management (aliased as `amc`)
3. `ami-domains-list` - List domain submodules (aliased as `adl`)
4. `ami-domains-test` - Run domains module tests (aliased as `adt`)

### Shell Exposures to Implement
1. **Marketing MCP server access**:
   - `ami-marketing-mcp` function with transport and root options
   - Research workspace management commands
   - Schema definition and validation tools

2. **Research automation**:
   - `ami-research-claude` function for Claude workflows
   - Research record capture tools
   - Audit trail management utilities

3. **Domain submodule management**:
   - Enhanced domain listing capabilities
   - Cross-domain resource management
   - Domain-specific configuration tools

4. **Research workflow tools**:
   - Workspace creation and management
   - Data validation and schema tools
   - Provenance tracking utilities

### Required Exposures
1. Research MCP server for marketing domain through `ami-marketing-mcp` (needs implementation)
2. Research workspace management tools through `ami-research-workspace` (needs implementation)
3. Schema definition and validation capabilities through `ami-research-schema` (needs implementation)
4. Research record capture with provenance through `ami-research-record` (needs implementation)
5. Audit trail management through `ami-research-audit` (needs implementation)
6. Research testing framework via `ami-marketing-test`
7. Claude research automation through `ami-research-claude` (needs implementation)
8. Domain submodule management through `ami-domains-list`

## Domain Submodules

### Marketing Domain (domains/marketing)
- **Status**: Active implementation with backend and MCP server
- **Purpose**: Research and marketing automation capabilities
- **Key Features**:
  - Research workspace management
  - Schema-based data validation
  - Provenance tracking for research records
  - Audit trail functionality
  - Automated research workflows
- **Shell Exposure**:
  - MCP server: `ami-marketing-mcp` (needs implementation)
  - Research tools: `ami-research-*` functions (need implementation)
  - Campaign management: `ami-marketing-campaign` (placeholder)

### Risk Domain (domains/risk)
- **Status**: Documentation only
- **Files**: `SPEC-RISK.md`
- **Purpose**: Risk assessment and management (planned)
- **Shell Exposure**:
  - `ami-risk-mcp` - Planned MCP server function (needs implementation)
  - `ami-risk-assess` - Planned risk assessment tools (needs implementation)
  - Alias: `arm` (requires additional alias in setup-shell.sh)

### SDA Domain (domains/sda)
- **Status**: Basic structure
- **Files**: Basic directory structure with sda module
- **Purpose**: System design automation (planned)
- **Shell Exposure**:
  - `ami-sda-mcp` - Planned MCP server function (needs implementation)
  - `ami-sda-design` - Planned system design tools (needs implementation)
  - Alias: `asm` (requires additional alias in setup-shell.sh)

## Exposed Functionality for Other Modules

### Research Framework
- Complete MCP-based research system for data collection
- Schema validation system for structured data
- Provenance tracking and audit capabilities
- Workspace management system
- Source verification and attachment handling
- Structured logging and audit trails

### Domain Management
- Multi-domain architecture support
- Module-specific backends and MCP servers
- Research workspace templates
- Data validation frameworks
- Cross-domain resource management

## Shell Integration Requirements

### Functions to Add to setup-shell.sh
1. **ami-marketing-mcp** - Function to run marketing research MCP server
2. **ami-research-claude** - Function to run Claude research automation
3. **ami-research-workspace** - Function to manage research workspaces
4. **ami-research-schema** - Function to manage research schemas
5. **ami-research-record** - Function to manage research records
6. **ami-research-audit** - Function to manage research audit trails
7. **ami-research-config** - Function to manage research configuration
8. **ami-risk-mcp** - Function to run risk assessment MCP server (planned)
9. **ami-sda-mcp** - Function to run SDA MCP server (planned)
10. **ami-domains-status** - Function to check status of domain services

### Aliases to Add
1. `amm` - Alias for `ami-marketing-mcp`
2. `arc` - Alias for `ami-research-claude`
3. `arw` - Alias for `ami-research-workspace`
4. `ars` - Alias for `ami-research-schema`
5. `arr` - Alias for `ami-research-record`
6. `ara` - Alias for `ami-research-audit`
7. `arcfg` - Alias for `ami-research-config`
8. `arm` - Alias for `ami-risk-mcp`
9. `asm` - Alias for `ami-sda-mcp`
10. `ads` - Alias for `ami-domains-status`

### Enhanced Functionality
1. Add server management capabilities to `ami-marketing-mcp` (start, stop, status, logs)
2. Add research workflow management commands (create, update, delete workspaces)
3. Add schema validation and management tools
4. Add provenance tracking and source verification utilities
5. Add audit trail querying and reporting capabilities
6. Add cross-domain resource management tools
7. Add research data export and import capabilities
8. Add automated research workflow scheduling