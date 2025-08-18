# IDP System Design Overview

## Executive Summary

The Intelligent Document Processing (IDP) system is designed as an elegant extension to the existing infrastructure, leveraging the powerful multi-storage architecture already in place. Rather than building new systems, we maximize the use of existing capabilities through strategic model definitions and minimal code additions.

## Key Design Principles

### 1. **Leverage Existing Infrastructure**
- Uses UnifiedCRUD for automatic multi-storage synchronization
- Extends StorageModel for declarative storage distribution
- Utilizes Dgraph's native graph algorithms
- Relies on automatic embedding generation for vector storage

### 2. **Elegant Simplicity**
- Document models with storage_configs automatically handle distribution
- No manual embedding code - pgvector DAO handles it
- No custom graph algorithms - Dgraph provides them natively
- Minimal new code, maximum functionality

### 3. **Smart Storage Distribution**
```python
# A single model definition handles everything
class Document(StorageModel):
    class Meta:
        storage_configs = {
            "graph": StorageConfig(storage_type=StorageType.GRAPH),      # Relationships
            "vector": StorageConfig(storage_type=StorageType.VECTOR),    # Embeddings
            "relational": StorageConfig(storage_type=StorageType.RELATIONAL), # Metadata
            "cache": StorageConfig(storage_type=StorageType.CACHE)       # Fast access
        }
```

## Architecture Overview

### Document Processing Flow

```
User Request → MCP Tool → Document Extractor → StorageModel → UnifiedCRUD
                   ↓                                              ↓
              [index_document]                          [Automatic Distribution]
              [read_document]                                    ↓
              [read_image]                          ┌─────────────┴─────────────┐
                                                    │                           │
                                                 Dgraph    PgVector    PostgreSQL    Redis
                                               (Relations) (Embeddings) (Tables)   (Cache)
```

### Component Interactions

1. **MCP Tools Layer**
   - Three new tools added to filesys MCP server
   - Minimal handlers that delegate to extractors
   - Automatic registration with ToolRegistry

2. **Document Extractors**
   - Pluggable extractors for each format
   - Common base class for consistency
   - Direct use of best-in-class libraries (PyPDF2, python-docx, etc.)

3. **Storage Models**
   - Define data structure and storage distribution
   - Automatic serialization/deserialization
   - Built-in validation and type safety

4. **UnifiedCRUD**
   - Handles all multi-storage operations
   - Configurable sync strategies (parallel, sequential, eventual)
   - Automatic rollback on failures

5. **Storage DAOs**
   - DgraphDAO: Already supports graph operations via DQL
   - PgVectorDAO: Auto-generates embeddings on create
   - PostgreSQL: Dynamic table creation from schemas
   - RedisDAO: Simple key-value caching

## Key Features

### 1. **Automatic Embeddings**
When a Document is saved with vector storage configured:
1. PgVectorDAO serializes all fields to text
2. Generates embeddings using sentence-transformers
3. Stores both original data and embeddings
4. Enables similarity search automatically

### 2. **Native Graph Operations**
Using Dgraph's built-in capabilities:
- K-hop traversal with `@recurse`
- Shortest path with native `shortest` function
- Pattern matching with DQL
- No custom graph algorithm implementation needed

### 3. **Smart Table Extraction**
For structured data in documents:
1. Extract tables with appropriate library
2. Infer schema using pandas
3. Create DocumentTable model with relational storage
4. PostgreSQL DAO creates actual tables dynamically

### 4. **LLM-Powered Image Analysis**
Using Gemini 2.5 Pro:
1. Send image with instruction/template
2. Gemini handles OCR automatically
3. Parse structured response
4. Cache in Redis, store in appropriate storages

## Implementation Strategy

### Phase 1: Foundation (Critical Path)
- Create core models (Document, DocumentSection, etc.)
- Add MCP tools to filesys
- Implement basic extractors

### Phase 2: Storage (Parallel Work)
- Implement PgVectorDAO (if not exists)
- Extend DgraphDAO with graph methods
- Setup Redis caching

### Phase 3: Intelligence
- Integrate Gemini 2.5 Pro
- Build analysis pipelines
- Implement caching strategy

### Phase 4: Query Layer
- Raw query methods for power users
- Object-based search for ease of use
- Cross-storage hybrid queries

## Why This Design Works

### 1. **Minimal New Code**
- Reuses 90% of existing infrastructure
- Only adds domain-specific models and extractors
- Leverages third-party capabilities

### 2. **Automatic Scaling**
- UnifiedCRUD handles distribution
- Storage backends handle their own scaling
- No custom orchestration needed

### 3. **Type Safety**
- Pydantic models ensure data integrity
- MyPy catches type errors at development
- Runtime validation prevents bad data

### 4. **Maintainability**
- Clear separation of concerns
- Pluggable extractors for new formats
- Declarative storage configuration

## Technical Advantages

### 1. **Storage Optimization**
- Graph: Only relationships, not full documents
- Vector: Only embeddings, not raw data
- Relational: Only structured/tabular data
- Cache: Only frequently accessed items

### 2. **Query Performance**
- Each storage optimized for its query type
- Indexes configured per storage
- Parallel query execution possible

### 3. **Fault Tolerance**
- Multi-storage redundancy
- Transaction support with rollback
- Graceful degradation if storage unavailable

## Risk Mitigation

### 1. **Complexity Management**
- Use existing patterns, don't invent new ones
- Extensive testing at each layer
- Clear documentation and examples

### 2. **Performance**
- Async/await throughout
- Batch processing where applicable
- Caching at multiple levels

### 3. **Security**
- PII detection before storage
- Secure API key management
- Document-level access controls

## Success Metrics

### Technical Metrics
- Document processing: < 10s per document
- Query latency: < 200ms average
- Storage efficiency: 30% compression
- Uptime: 99.9%

### Business Metrics
- Document types supported: 10+
- Extraction accuracy: 98%+
- User adoption rate
- Time saved vs manual processing

## Conclusion

This design achieves sophisticated document processing capabilities through elegant use of existing infrastructure. By leveraging the power of StorageModel, UnifiedCRUD, and native storage capabilities, we create a system that is both powerful and maintainable. The key insight is that we don't need to build complex new systems - we need to thoughtfully compose existing ones.

The result is a document processing system that:
- Automatically distributes data across optimal storage types
- Provides powerful search and analysis capabilities
- Scales with the underlying infrastructure
- Requires minimal new code to implement

This is not just a document processor - it's a demonstration of how well-designed infrastructure can be extended elegantly to solve new problems.