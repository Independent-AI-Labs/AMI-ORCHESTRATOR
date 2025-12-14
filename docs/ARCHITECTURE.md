# AMI-ORCHESTRATOR Architecture

## System Overview

AMI-ORCHESTRATOR is a modular enterprise automation framework built on a multi-storage architecture with intelligent document processing, browser automation, and compliance validation capabilities.

## Core Architecture Principles

### 1. Multi-Storage Synchronization
- **Primary Source of Truth**: Dgraph graph database for relationships and ACL
- **Automatic Sync**: UnifiedCRUD handles multi-backend synchronization
- **Storage Types**: Graph, Vector, Relational, Cache, Blob, Time-series
- **Consistency Model**: Primary-first with eventual consistency

### 2. Security-First Design
- **ACL at Core**: Every operation validated against Dgraph ACLs
- **Role-Based Access**: User, role, and group-based permissions
- **Audit Trail**: UUID v7 ensures time-ordered, traceable operations
- **Secure Defaults**: No permissive defaults, explicit grants only

### 3. Event-Driven Architecture
- **No Polling**: All operations are event-driven
- **Reactive Design**: Components respond to state changes
- **Worker Pools**: Intelligent resource management with hibernation
- **Async Everything**: Non-blocking operations throughout

## Module Architecture

### Base Module (Core Infrastructure)
```
base/
├── backend/
│   ├── dataops/               # Multi-storage data layer
│   │   ├── storage_model.py   # Base model with DAO integration
│   │   ├── security_model.py  # ACL and permissions
│   │   ├── unified_crud.py    # Multi-backend CRUD operations
│   │   └── implementations/   # Storage-specific DAOs
│   │       ├── dgraph_dao.py      # Graph operations
│   │       ├── pgvector_dao.py    # Vector embeddings
│   │       ├── postgresql_dao.py  # Relational with dynamic schema
│   │       └── redis_dao.py       # Caching with TTL
│   ├── mcp/                   # Model Context Protocol servers
│   └── workers/               # Worker pool management
```

**Key Components:**
- **StorageModel**: Base class for all data objects
- **UnifiedCRUD**: Automatic multi-storage synchronization
- **DAOFactory**: Dynamic DAO instantiation
- **SecurityContext**: Permission validation

### Files Module (Document Processing)
```
files/
├── backend/
│   ├── extractors/           # Document extractors
│   │   ├── pdf_extractor.py     # PyMuPDF-based PDF processing
│   │   ├── docx_extractor.py    # Word document processing
│   │   └── image_extractor.py   # Image analysis
│   ├── models/               # Document models
│   │   └── document.py          # Multi-storage document model
│   ├── services/             # External services
│   │   └── gemini_client.py    # AI-powered image analysis
│   └── mcp/                  # MCP server
│       └── filesys/
│           └── tools/           # Document processing tools
```

**Key Components:**
- **DocumentExtractor**: Base class for format-specific extractors
- **Document StorageModel**: Multi-storage document representation
- **GeminiClient**: Rate-limited AI image analysis
- **MCP Tools**: index_document, read_document, read_image

### Browser Module (Web Automation)
```
browser/
├── backend/
│   ├── core/
│   │   ├── browser/          # Browser lifecycle management
│   │   ├── management/       # Profile and session management
│   │   ├── monitoring/       # Real-time monitoring
│   │   └── security/         # Anti-detection
│   ├── facade/               # High-level API
│   │   ├── navigation/      # Page navigation
│   │   ├── input/           # User input simulation
│   │   └── media/           # Screenshots and recording
│   └── mcp/                  # MCP server
```

**Key Components:**
- **ChromeManager**: Browser instance management
- **ProfileManager**: Persistent profile management
- **AntiDetect**: Fingerprint manipulation
- **MCP Server**: AI-controlled browser operations

## Data Flow Architecture

### Document Processing Pipeline
```
1. Document Input (PDF/DOCX/Image)
   ↓
2. Format Detection & Extractor Selection
   ↓
3. Content Extraction (Text/Tables/Images)
   ↓
4. Model Creation (Document/Section/Table)
   ↓
5. UnifiedCRUD Storage
   ├→ Dgraph (Graph relationships)
   ├→ PgVector (Embeddings for search)
   ├→ PostgreSQL (Structured data)
   └→ Redis (Cache for fast access)
```

### Security Flow
```
1. Request with SecurityContext
   ↓
2. ACL Check in Dgraph
   ↓
3. Permission Validation
   ↓
4. Operation Execution
   ↓
5. Audit Log Creation
```

### MCP Communication Flow
```
1. AI Agent Request
   ↓
2. MCP Server Router
   ↓
3. Tool Executor
   ↓
4. Backend Operation
   ↓
5. Response Formatting
   ↓
6. AI Agent Response
```

## Storage Architecture

### Multi-Storage Strategy
```
┌─────────────────────────────────────────┐
│           UnifiedCRUD Layer             │
├─────────────────────────────────────────┤
│         Primary: Dgraph (Graph)         │
│  - Relationships                        │
│  - ACL/Permissions                      │
│  - BPMN Workflows                       │
├─────────────────────────────────────────┤
│      Secondary Storage Backends         │
├─────────────────────────────────────────┤
│ PgVector          │ PostgreSQL          │
│ - Embeddings      │ - Structured data   │
│ - Semantic search │ - Dynamic tables    │
├───────────────────┼─────────────────────┤
│ Redis             │ MongoDB             │
│ - Cache           │ - Documents         │
│ - TTL support     │ - Flexible schema   │
└─────────────────────────────────────────┘
```

### Synchronization Strategies

**PRIMARY_FIRST** (Default)
- Write to Dgraph first
- Sync to other backends
- Best for consistency

**PARALLEL**
- Write to all backends simultaneously
- Best for performance
- Risk of partial failures

**TRANSACTIONAL**
- All-or-nothing writes
- Rollback on any failure
- Best for critical data

## Security Architecture

### Permission Model
```
User → Roles → Groups → Permissions
  ↓       ↓       ↓          ↓
  └───────┴───────┴──────────┘
              ↓
         ACL in Dgraph
              ↓
    Operation Authorization
```

### ACL Structure
```python
{
    "resource": "Document:123",
    "principal": "user:alice",
    "permissions": ["read", "write"],
    "conditions": {
        "ip_range": "10.0.0.0/8",
        "time_window": "business_hours"
    }
}
```

## Performance Optimizations

### Caching Strategy
- **Redis L1 Cache**: Hot data with TTL
- **Local Memory Cache**: Frequently accessed metadata
- **Query Result Cache**: Expensive computations

### Worker Pool Management
- **Dynamic Scaling**: 2-10 workers based on load
- **Worker Hibernation**: Idle workers sleep
- **Warm Pool**: Pre-initialized workers ready

### Batch Processing
- **Bulk Operations**: Batch inserts/updates
- **Pipeline Execution**: Chain operations
- **Async I/O**: Non-blocking throughout

## Deployment Architecture

### Container Deployment
```
┌─────────────────────────────────┐
│        Docker Compose           │
├─────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐   │
│  │  Dgraph  │  │PostgreSQL│   │
│  │  :9080   │  │  :5432   │   │
│  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐   │
│  │  Redis   │  │ MongoDB  │   │
│  │  :6379   │  │  :27017  │   │
│  └──────────┘  └──────────┘   │
└─────────────────────────────────┘
```

### Network Architecture
- **Service Mesh**: Internal service communication
- **API Gateway**: External access point
- **Load Balancer**: Request distribution
- **TLS Everywhere**: Encrypted communication

## Monitoring & Observability

### Metrics Collection
- **Application Metrics**: Request rates, latencies
- **System Metrics**: CPU, memory, disk
- **Business Metrics**: Documents processed, searches

### Logging Strategy
- **Structured Logging**: JSON format
- **Log Levels**: DEBUG, INFO, WARNING, ERROR
- **Centralized Collection**: ELK stack compatible

### Tracing
- **Distributed Tracing**: Request flow across services
- **Performance Profiling**: Bottleneck identification
- **Error Tracking**: Exception aggregation

## Future Architecture Considerations

### Scalability Path
- **Horizontal Scaling**: Stateless services
- **Database Sharding**: Partition by tenant
- **Edge Caching**: CDN integration
- **Microservices**: Service decomposition

### AI Integration Expansion
- **Local LLMs**: On-premise AI models
- **Vector Database**: Dedicated vector storage
- **ML Pipeline**: Training and inference
- **Agent Orchestration**: Multi-agent systems

### Compliance Extensions
- **Policy Engine**: Declarative policies
- **Audit Vault**: Immutable audit logs
- **Encryption at Rest**: Full database encryption
- **Data Residency**: Geographic constraints

## Architecture Decision Records

### ADR-001: Dgraph as Primary Storage
**Decision**: Use Dgraph as the primary source of truth
**Rationale**: Native graph operations, built-in ACL, GraphQL support
**Consequences**: All other storage must sync from Dgraph

### ADR-002: UUID v7 for Identifiers
**Decision**: Use UUID v7 for all entity IDs
**Rationale**: Time-ordered, naturally sortable, globally unique
**Consequences**: Consistent ID format across all modules

### ADR-003: MCP for AI Integration
**Decision**: Implement Model Context Protocol servers
**Rationale**: Standard interface for AI agents
**Consequences**: All tools exposed via MCP

### ADR-004: Event-Driven Architecture
**Decision**: No polling loops anywhere in the system
**Rationale**: Better resource utilization, lower latency
**Consequences**: More complex state management