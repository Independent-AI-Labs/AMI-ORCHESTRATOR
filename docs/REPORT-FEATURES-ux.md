# UX Module Features Report

## MCP Servers

### Current Status
- **No MCP servers currently implemented** in the main ux module
- Module focuses on user experience and interface components
- Primary component is a CMS system (ux/cms) with web interface

### Planned MCP Servers (Future)
Based on the architectural vision, potential future MCP servers may include:
- Interface component management server
- UX automation server
- CMS management server
- Authentication and authorization server

## Tools and Scripts

### Core Scripts
1. **ami_path.py** - AMI Path Setup
   - **Location**: `ux/scripts/ami_path.py`
   - **Functionality**: Standalone, zero-dependency path configuration for AMI modules
   - **Purpose**: Automatically configure Python paths for cross-module imports without dependencies
   - **CLI Access**: Used internally by other scripts for path setup

2. **setup-shell.sh** - UX module shell environment setup
   - **Location**: `ux/scripts/setup-shell.sh`
   - **Functionality**: Defines UX-specific aliases and functions
   - **CLI Access**: `ami-ux-list`, `ami-ux-test`

### UX Submodules

#### CMS (Content Management System) - `ux/cms`
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

#### Auth System - `ux/auth`
- **Technology**: TypeScript/Node.js application
- **Functionality**: Authentication system for AMI modules
- **Components**:
  - `src/` - Source code for authentication
  - `package.json` - Dependencies and scripts
  - `tsconfig.json` - TypeScript configuration

#### Research Documentation - `ux/research`
- **Content**: Research on schema-driven UI concepts
- **Files**:
  - `SCHEMA_DRIVEN_UI_CONCEPT.md` - UI concept research
  - `SCHEMA_UI_COMPONENT_CATALOG.md` - Component catalog research
  - `SCHEMA_UI_ENTERPRISE_RESEARCH.md` - Enterprise UI research

## CLI Features and Aliases

### Available Aliases
1. `ami-ux-list` - List UX submodules (aliased as `aul`)
2. `ami-ux-test` - Run UX module tests (aliased as `aut`)

### Required Exposures
1. CMS development and deployment tools
2. UX component management
3. Authentication system management
4. UI validation and testing tools
5. Highlight automation system

## Current Implementation Status

### ✅ CMS (Live Data Directory)
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
- **Event Type Coverage**: Full DOM trigger event catalog
- **Scheduled Triggers**: Cron-style automation scheduling
- **Rich Text Edit**: Inline editor functionality
- **Agents Drawer**: Orchestrator agent integration
- **Data Sources Drawer**: Upstream catalogue connections
- **API Drawer**: MCP and REST API client integration
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

### UI Component System
- Tabbed workspace architecture
- React-based drawer system
- Message passing between components
- State persistence system
- Security layer (CSP, path sanitization)
- API integration framework

### Automation Integration
- DOM event trigger system
- Automation scenario management
- Trigger composition tools
- Runtime execution environment
- Meta-data management system

### Development and Deployment
- Local development workflows
- Production build and deployment
- Testing and validation scripts
- Linting and quality gates
- Health monitoring capabilities

## Shell Integration Requirements

### Current Shell Exposure
1. **ami-ux-mcp** - Placeholder for UX-specific MCP server (not implemented)
2. **ami-ux-test** - Run UX module tests (aliased as `aut`)
3. **ami-ux-list** - List UX submodules (aliased as `aul`)

### Functions to Add to setup-shell.sh
1. **ami-ux-mcp** - Function to run UX MCP server (future implementation)
   - `ami-ux-mcp --transport stdio` - Launch with specific transport
   - For future interface component and UX automation MCP functionality

2. **ami-cms-start** - Function to start CMS server
   - `ami-cms-start` - Start Next.js CMS server
   - `ami-cms-start --port 3000` - Start on specific port
   - Uses npm scripts for Next.js development server

3. **ami-cms-stop** - Function to stop CMS server
   - `ami-cms-stop` - Stop Next.js CMS server
   - Kill any running CMS processes

4. **ami-cms-build** - Function to build CMS for production
   - `ami-cms-build` - Build CMS for production deployment
   - Uses `npm run build` command

5. **ami-cms-dev** - Function to start CMS in development mode
   - `ami-cms-dev` - Start CMS in development mode
   - With hot reloading and development features

6. **ami-cms-status** - Function to check CMS status
   - `ami-cms-status` - Check if CMS is running
   - Report port and process information

7. **ami-auth-start** - Function to start authentication service
   - `ami-auth-start` - Start auth service for AMI modules
   - For authentication system management

8. **ami-ux-components** - Function to manage UI components
   - `ami-ux-components list` - List available UI components
   - `ami-ux-components add <component>` - Add a new component

9. **ami-ux-validate** - Function to validate UI
   - `ami-ux-validate` - Run UI validation and testing
   - Includes linting and accessibility checks

10. **ami-ux-deploy** - Function to deploy UX components
    - `ami-ux-deploy --env production` - Deploy to production
    - For production deployment of UX components

### Aliases to Add
1. `aum` - Alias for `ami-ux-mcp`
2. `aucms` - Alias for `ami-cms-start`
3. `aucmsd` - Alias for `ami-cms-dev`
4. `aucmsb` - Alias for `ami-cms-build`
5. `aucmsst` - Alias for `ami-cms-status`
6. `auauth` - Alias for `ami-auth-start`
7. `auc` - Alias for `ami-ux-components`
8. `auv` - Alias for `ami-ux-validate`
9. `aud` - Alias for `ami-ux-deploy`
10. `aul` - Already exists for `ami-ux-list`

### Required Shell Exposures for Current Functionality
1. **CMS Management**:
   - `ami-cms-start`, `ami-cms-stop`, `ami-cms-dev`, `ami-cms-build` functions
   - Development and production workflow tools
   - Status checking and monitoring

2. **UX Component Management**:
   - `ami-ux-components` for managing UI components
   - Component creation and validation tools

3. **UI Validation and Testing**:
   - `ami-ux-validate` for UI quality assurance
   - Linting and accessibility checking

4. **Authentication System**:
   - `ami-auth-start` for auth service management

### Planned Shell Exposures for Future Infrastructure
1. **Interface Component Management**:
   - Component lifecycle management
   - Version control and updates
   - Component registry and discovery

2. **UX Automation**:
   - Automation scenario management
   - Trigger composition tools
   - DOM event automation utilities

3. **CMS Management**:
   - Content creation and management workflows
   - User management and permissions
   - Publishing and workflow automation

4. **Authentication Server**:
   - User authentication and authorization
   - Policy management and enforcement
   - Credential management tools

### Enhanced Functionality
1. Add CMS lifecycle management commands (start, stop, build, deploy)
2. Add UI component management tools
3. Add authentication service management
4. Add UI validation and testing utilities
5. Add Next.js development workflow tools
6. Add content management utilities
7. Add user management capabilities
8. Add automation trigger management (future)
9. Add interface component registry tools (future)
10. Add UX testing and monitoring capabilities