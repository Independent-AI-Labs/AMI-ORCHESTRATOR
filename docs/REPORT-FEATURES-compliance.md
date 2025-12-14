# Compliance Module Features Report

## MCP Servers

### Audit MCP Server (Research/Future Implementation)
- **Status**: Theoretical - Planned MCP server for audit and compliance tools
- **File**: `compliance/backend/mcp/audit/` (directories exist but not yet implemented)
- **Purpose**: Planned to provide compliance and audit functionality through MCP protocol
- **Functionality**: (Planned features based on documentation)
  - Audit trail collection and management
  - Compliance requirement tracking
  - Regulatory mapping and validation
  - Cryptographically signed state snapshots
  - Evidence collection tools
- **Note**: Current MCP server is theoretical - actual implementation planned for future
- **Shell Exposure**:
  - `ami-compliance-mcp` - Placeholder function in setup-shell.sh (needs implementation)
  - Planned: `ami-compliance-mcp --transport stdio` for specific transport
  - Alias: `acm` (requires additional alias in setup-shell.sh)

## Tools and Scripts

### Core Scripts
1. **ami-audit** - Compliance audit CLI wrapper
   - **Location**: `compliance/scripts/ami-audit`
   - **Functionality**: Bash wrapper for compliance audit CLI (references non-existent audit_cli.py)
   - **Shell Exposure**:
     - `ami-audit [options]` - Main compliance audit CLI (requires audit_cli.py implementation)
     - Direct access: `ami-run compliance/scripts/ami-audit [options]`
     - Note: Currently references non-existent audit_cli.py file, needs implementation
     - Requires compliance module venv setup

2. **download_standards.py** - Compliance standards downloader
   - **Location**: `compliance/scripts/download_standards.py`
   - **Functionality**: Downloads reference PDFs listed in the compliance standards catalog
   - **Shell Exposure**:
     - `ami-compliance-standards` - Function in setup-shell.sh (requires implementation)
     - Direct access: `ami-run compliance/scripts/download_standards.py`
     - Purpose: Downloads regulatory standard documents (EU AI Act, ISO 42001, etc.)
     - Alias: `acs` (requires additional alias in setup-shell.sh)

### Core Audit System (Research Implementation)
- **Location**: `compliance/backend/audit/core/`
- **Components**:
  - `models.py` - Core audit data models and enumerations
  - `audit_store.py` - Persistent storage for audit records with multiple backends (PostgreSQL, Dgraph, Redis planned)
  - `audit_chain.py` - Blockchain-style immutable audit chain with cryptographic verification
  - `audit_context.py` - Audit context management
- **Shell Exposure**:
  - `ami-audit-store` - Function to manage audit storage (requires implementation)
  - `ami-audit-chain` - Function to manage audit chains (requires implementation)
  - `ami-audit-models` - Function to manage audit data models (requires implementation)

### Data Models
- **File**: `compliance/backend/audit/core/models.py`
- **Classes**:
  - `AuditRecord` - Immutable audit records with cryptographic verification
  - `AuditFinding` - Analysis findings from audit analyzers
  - `AuditViolation` - Code quality or security violations
  - `AuditSignature` - Cryptographic signatures for audit records
  - `AuditFilter` - Filter criteria for querying audit records
  - `AuditOptions` - Options for audit collection
- **Shell Exposure**:
  - Through audit management commands (require implementation)
  - `ami-audit-create` - Create audit records (requires implementation)
  - `ami-audit-query` - Query audit records with filters (requires implementation)

### Storage System
- **File**: `compliance/backend/audit/core/audit_store.py`
- **Class**: `AuditStore`
- **Functionality**:
  - Persistent storage for audit records
  - Multiple backend support (PostgreSQL, Dgraph, Redis - planned)
  - In-memory fallback implementation
  - Record querying with filters
  - Provenance chain tracking
  - Integrity verification
- **Shell Exposure**:
  - `ami-audit-store` - Manage audit storage backends (requires implementation)
  - `ami-audit-store-postgres` - PostgreSQL backend operations (requires implementation)
  - `ami-audit-store-query` - Query audit records (requires implementation)

### Audit Chain System
- **File**: `compliance/backend/audit/core/audit_chain.py`
- **Class**: `AuditChain`
- **Functionality**:
  - Blockchain-style immutable chain of audit records
  - Proof-of-work mining for computational cost
  - Cryptographic verification of chain integrity
  - Time-based chain slicing
  - Filtered record finding
  - Chain export in multiple formats (JSON, YAML)
  - Signature verification across chain
  - Chain statistics
- **Shell Exposure**:
  - `ami-audit-chain` - Manage audit chains (requires implementation)
  - `ami-audit-chain-export` - Export audit chains (requires implementation)
  - `ami-audit-chain-verify` - Verify chain integrity (requires implementation)
  - `ami-audit-chain-stats` - Get chain statistics (requires implementation)

### Analysis Components (directories exist but empty)
- **Location**: `compliance/backend/audit/analyzers/` - Analysis engines (planned)
- **Location**: `compliance/backend/audit/sources/` - Audit sources (git, file, logs) (planned)
- **Location**: `compliance/backend/audit/collectors/` - Collection strategies (planned)
- **Location**: `compliance/backend/audit/reporting/` - Output formatters (planned)
- **Shell Exposure**:
  - `ami-audit-analyze` - Run audit analysis (requires implementation)
  - `ami-audit-collect` - Collect audit data (requires implementation)
  - `ami-audit-report` - Generate compliance reports (requires implementation)

### MCP Tools Framework (empty directory)
- **Location**: `compliance/backend/mcp/audit/tools/` - Planned MCP tools (currently empty)
- **Shell Exposure**: Will be exposed through MCP server once implemented

## CLI Features and Aliases

### Available Aliases
1. `ami-compliance-mcp` - Placeholder for compliance-specific MCP server (from setup-shell.sh)
2. `ami-compliance-test` - Run compliance module tests (aliased as `act`)
3. `ami-compliance-validate` - Compliance validation (from setup-shell.sh)

### Shell Exposures to Implement
1. **Audit system access**:
   - Complete `ami-audit` CLI implementation (requires audit_cli.py)
   - Audit record creation and management tools
   - Audit chain operations and verification
   - Audit storage management commands

2. **Compliance checking**:
   - `ami-compliance-validate` enhancement with real validation logic
   - Compliance requirement checking tools
   - Regulatory compliance verification

3. **Standards documentation**:
   - `ami-compliance-standards` for downloading standards
   - Standards catalog management
   - Regulatory mapping tools

4. **Audit management**:
   - Audit record querying and filtering
   - Audit chain export and import
   - Evidence collection tools

### Required Exposures
1. Audit trail collection and management tools (needs implementation)
2. Regulatory compliance checking through `ami-compliance-validate`
3. Evidence collection capabilities (needs implementation)
4. Compliance reporting functions (needs implementation)
5. Standards documentation and downloader through `ami-compliance-standards` (needs implementation)
6. Compliance testing framework via `ami-compliance-test`
7. MCP server access through `ami-compliance-mcp` (needs implementation)

## Current Status

According to the README, the compliance module is currently in the **Research & Documentation Phase**:
- Most advanced features described are theoretical
- Current production capability: audit trail exists at `base/backend/dataops/security/audit_trail.py`
- The compliance module contains research on AI governance and regulatory compliance
- Consolidated regulatory standards documented (EU AI Act, ISO 42001, ISO 27001, NIST AI RMF)
- Basic audit trail system implemented with data models, storage, and chain systems

## Exposed Functionality for Other Modules

### Research Framework
- Audit trail system components
- Cryptographically signed state snapshots concept
- Regulatory compliance mapping research
- Evidence collection framework
- Compliance requirements specification research
- Isolated execution environments concept

### Core Services (Theoretical)
- Compliance checking and validation
- Audit record management
- Regulatory reporting
- Evidence registry concepts
- Risk assessment frameworks
- Gap analysis and remediation tracking

## Shell Integration Requirements

### Functions to Add to setup-shell.sh
1. **ami-compliance-mcp** - Function to run compliance MCP server (needs implementation)
2. **ami-compliance-standards** - Function to download compliance standards
3. **ami-audit-store** - Function to manage audit storage
4. **ami-audit-chain** - Function to manage audit chains
5. **ami-audit-create** - Function to create audit records
6. **ami-audit-query** - Function to query audit records
7. **ami-compliance-status** - Function to check compliance status
8. **ami-compliance-report** - Function to generate compliance reports
9. **ami-compliance-check** - Function to perform compliance checks
10. **ami-compliance-generate** - Function to generate compliance artifacts

### Aliases to Add
1. `acm` - Alias for `ami-compliance-mcp`
2. `acs` - Alias for `ami-compliance-standards`
3. `aas` - Alias for `ami-audit-store`
4. `aac` - Alias for `ami-audit-chain`
5. `aacr` - Alias for `ami-audit-create`
6. `aaq` - Alias for `ami-audit-query`
7. `acst` - Alias for `ami-compliance-status`
8. `acr` - Alias for `ami-compliance-report`
9. `acc` - Alias for `ami-compliance-check`
10. `acg` - Alias for `ami-compliance-generate`

### Enhanced Functionality
1. Implement the missing `audit_cli.py` to enable the `ami-audit` command
2. Add full MCP server implementation for compliance
3. Add audit record management commands (create, query, export)
4. Add compliance checking and validation tools
5. Add regulatory standards management utilities
6. Add evidence collection and reporting capabilities
7. Add audit chain management tools (verify, export, stats)
8. Add storage backend management for audit records