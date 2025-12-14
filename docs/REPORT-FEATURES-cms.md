# CMS Module Features Report

## MCP Servers

### Current Status
- **No MCP servers currently implemented** in the CMS module
- Module focuses on content management and user interface components
- CMS serves as a frontend for interacting with other MCP services (planned)

### Planned MCP Servers (Future)
Based on the architectural vision, potential future MCP integration may include:
- API Drawer for MCP endpoint management
- Automation orchestration server
- Content publishing MCP server
- Translation pipeline MCP server
- Agent integration server

## Tools and Scripts

### Core Scripts

1. **setup-shell.sh** - CMS module shell environment setup
   - **Location**: `ux/cms/scripts/setup-shell.sh`
   - **Functionality**: Defines CMS-specific aliases and functions
   - **CLI Access**: `ami-cms-server`, `ami-cms-test`

2. **px-to-rem.py** - CSS dimension conversion tool
   - **Location**: `ux/cms/scripts/px-to-rem.py`
   - **Functionality**: Convert px values to rem safely in CSS/JS files
   - **Usage**: `px-to-rem.py <file_pattern> [options]`
   - **Features**: Safe conversions for font-size, padding, margin, gap, width/height; excludes borders, shadows, outlines

3. **Node.js Server Scripts** - Development and production server management
   - **Location**: `ux/cms/scripts/server.mjs`, `ux/cms/scripts/runner.mjs`
   - **Functionality**: Start/stop dev services, manage long-lived instances via PID files
   - **Commands**: `npm run serve`, `npm run dev`, `npm run start`

### CMS Submodule Components

#### Core Next.js Application - `ux/cms`
- **Technology**: Next.js 15 application
- **Functionality**:
  - Live Data Directory CMS for observing data assets
  - Tabbed workspace for pinning directories and HTML bundles
  - Multi-surface rendering (inline HTML, apps, markdown viewer)
  - Upload and library management system
  - Automation scaffolding with trigger composer
  - Highlight and commenting system
  - Authentication with policy guardrails
  - Operational tooling for dev runners and validation

- **Key Components**:
  - `app/api/**` - API routes for trees, media, uploads, automation
  - `public/js/shell.js` - Core shell functionality
  - `public/js/visualizers.js` - Multi-surface rendering
  - `packages/highlight-core` - Core automation and highlighting system
  - `public/js/highlight-plugin/` - Runtime for automation system
  - `middleware.ts` - Authentication and security layer
  - `app/lib/store.ts` - Persistence and validation helpers

#### Highlight Automation System
- **Location**: `packages/highlight-core` → `public/js/highlight-plugin/`
- **Functionality**: Selection overlays, trigger placement, scenario orchestration, inline code execution
- **Components**:
  - Scenario manager and trigger composer
  - DOM event mapping to scripted actions
  - Selection and automation system
  - Comment and annotation tools

#### Authentication System
- **Technology**: NextAuth.js with `@ami/auth` integration
- **Functionality**: Authentication and authorization for CMS users
- **Components**:
  - Middleware protection (`middleware.ts`)
  - API authentication handlers (`app/api/auth/[...nextauth]/route.ts`)
  - Guest access support
  - Policy guardrails and capability flags

## CLI Features and Aliases

### Available Aliases
1. `ami-cms-server` - Start CMS server (aliased as `acs`)
2. `ami-cms-test` - Run CMS module tests (aliased as `actest`)

### Required Exposures
1. CMS development and deployment tools
2. Content management and publishing interfaces
3. Automation authoring and orchestration tools
4. Highlight plugin and trigger management
5. File and directory management utilities
6. UI validation and testing tools

## Current Implementation Status

### ✅ Production Ready
- **Next.js 15 Service**: Full-featured CMS for data asset management
- **Multi-tab Workspace**: Tabbed interface for browsing and managing content
- **Multi-surface Rendering**: Different viewing modes for content
- **Upload Management**: Upload and library system for content
- **Automation Scaffolding**: DOM trigger and automation system
- **Highlight Plugin**: Selection and automation system
- **Authentication**: Full authentication and policy system
- **Operational Tooling**: Dev runners, health checks, and validation

### 🚧 Planned Development
- **Full Log & SSH Terminal Console**: Multi-tab terminal integration
- **Auto-Translate File Action**: Translation pipeline integration
- **Event Type Coverage for DOM Triggers**: Full event catalogue in trigger composer
- **Scheduled Triggers**: Cron-style automation scheduling
- **Rich Text Edit**: Inline editor functionality
- **Agents Drawer**: Orchestrator agent integration
- **Data Sources Drawer**: Upstream catalogue connections
- **API Drawer (MCP, REST)**: MCP and REST API client integration
- **Infra Drawer**: Deploy target and service management
- **Chat/Message Thread UI**: Collaborative threads
- **Meta-File Comment System**: Git-friendly comment system
- **Video Streams**: Live observability feeds

## Exposed Functionality for Other Modules

### Web Interface Framework
- Next.js-based CMS platform
- Authentication integration capabilities
- Multi-surface rendering system
- File and directory management UI
- Automation trigger system
- Highlight and annotation tools

### API Integration Framework
- File system APIs through Next.js route handlers
- Upload and serving endpoints
- Library management APIs
- Automation metadata services
- Account management endpoints
- LaTeX rendering capabilities

### User Experience Components
- Tabbed workspace architecture
- React-based drawer system
- Message passing between components
- State persistence system
- Security layer (CSP, path sanitization)
- Multi-surface visualizer system

### Automation Integration
- DOM event trigger system
- Automation scenario management
- Trigger composition tools
- Runtime execution environment
- Meta-data management system
- Highlight plugin framework

### Development and Deployment
- Local development workflows
- Production build and deployment
- Testing and validation scripts
- Linting and quality gates
- Health monitoring capabilities
- CSS dimension conversion tools

## Architecture Integration Points

### Current Integration Points
- **Authentication Module**: Integration with `@ami/auth` for authentication
- **DataOps Module**: File system access and document roots
- **Browser Module**: Shared highlight plugin for automation
- **Docker Compose**: Integration with services profile
- **Production Deployment**: Multi-service orchestration

### Planned Integration Points
- **MCP Services**: API Drawer for MCP endpoint integration
- **Agent Framework**: Agents drawer for orchestrator agent access
- **Translation Services**: Auto-translate file action pipeline
- **Infrastructure Management**: Deploy target and service management
- **Compliance Module**: Audit and policy guardrails

## Shell Integration Requirements

### Current Shell Exposure
1. **ami-cms-server** - Start CMS server (aliased as `acs`)
2. **ami-cms-test** - Run CMS module tests (aliased as `actest`)

### Functions to Add to setup-shell.sh
1. **ami-cms-server** - Enhanced function to run CMS server
   - `ami-cms-server --port 3000` - Start on specific port
   - `ami-cms-server --dev` - Start in development mode
   - `ami-cms-server --prod` - Start in production mode
   - Uses npm scripts for Next.js server management

2. **ami-cms-dev** - Function to start CMS in development mode
   - `ami-cms-dev` - Start CMS with hot reloading
   - `ami-cms-dev --port 3000` - Start on specific port

3. **ami-cms-start** - Function to start CMS in production mode
   - `ami-cms-start` - Start production CMS server
   - `ami-cms-start --port 3000` - Start on specific port

4. **ami-cms-stop** - Function to stop CMS server
   - `ami-cms-stop` - Stop running CMS server
   - Kill any CMS processes

5. **ami-cms-build** - Function to build CMS for production
   - `ami-cms-build` - Build CMS for production deployment
   - Uses `npm run build` command

6. **ami-cms-status** - Function to check CMS status
   - `ami-cms-status` - Check if CMS is running
   - Report port and process information

7. **ami-cms-logs** - Function to view CMS logs
   - `ami-cms-logs` - View CMS server logs
   - `ami-cms-logs --follow` - Follow logs in real-time

8. **ami-cms-config** - Function to manage CMS configuration
   - `ami-cms-config view` - View current configuration
   - `ami-cms-config edit` - Edit configuration
   - `ami-cms-config validate` - Validate configuration

9. **ami-cms-content** - Function to manage content
   - `ami-cms-content list` - List available content
   - `ami-cms-content add <path>` - Add new content
   - `ami-cms-content delete <path>` - Delete content

10. **ami-automation-start** - Function to start automation system
    - `ami-automation-start` - Start automation scenario manager
    - For DOM trigger and automation system

### Aliases to Add
1. `acs` - Already exists for `ami-cms-server`
2. `actest` - Already exists for `ami-cms-test`
3. `acsd` - Alias for `ami-cms-dev`
4. `acss` - Alias for `ami-cms-start`
5. `acss` - Alias for `ami-cms-stop` (would conflict with start)
6. `acsb` - Alias for `ami-cms-build`
7. `acst` - Alias for `ami-cms-status`
8. `aclg` - Alias for `ami-cms-logs`
9. `accfg` - Alias for `ami-cms-config`
10. `accnt` - Alias for `ami-cms-content`

### Required Shell Exposures for Current Functionality
1. **CMS Server Management**:
   - `ami-cms-server`, `ami-cms-dev`, `ami-cms-start`, `ami-cms-stop` functions
   - Development and production workflow tools
   - Status checking and monitoring

2. **Content Management**:
   - `ami-cms-content` for managing content assets
   - Content creation and management tools

3. **CMS Configuration**:
   - `ami-cms-config` for configuration management
   - Validation and editing utilities

4. **Logging and Monitoring**:
   - `ami-cms-logs` for log viewing
   - Status checking with `ami-cms-status`

### Planned Shell Exposures for Future Infrastructure
1. **Automation Management**:
   - Scenario management and trigger composition
   - DOM event automation utilities
   - Automation runtime management

2. **MCP Integration**:
   - API Drawer for MCP endpoint management
   - MCP endpoint configuration and testing
   - API client generation and management

3. **Content Publishing**:
   - Publishing workflow automation
   - Content validation and approval tools
   - Multi-environment deployment

4. **Translation Pipeline**:
   - Translation job management
   - Multi-language content handling
   - Localization workflow tools

### Enhanced Functionality
1. Add CMS lifecycle management commands (start, stop, build, deploy)
2. Add content management utilities
3. Add configuration validation and management tools
4. Add logging and monitoring capabilities
5. Add automation scenario management (future)
6. Add MCP endpoint integration tools (future)
7. Add content publishing workflows (future)
8. Add translation pipeline management (future)
9. Add user and permission management
10. Add backup and restore capabilities