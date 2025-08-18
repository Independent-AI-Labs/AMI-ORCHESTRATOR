# Intelligent Document Processing (IDP) System Specification

## Executive Summary

This specification outlines the design and implementation of an Intelligent Document Processing (IDP) system that elegantly extends the existing filesys MCP server and DataOps infrastructure. The system leverages the powerful multi-storage architecture already in place, requiring only model definitions with appropriate storage configurations to automatically handle document processing, embeddings, and multi-modal storage.

## Core Features

### 1. Document Processing Tools

#### 1.1 index_document
- **Purpose**: Parse and index documents for searchable storage
- **Input**: File path, document type, indexing options
- **Output**: Document metadata, extracted content, storage references
- **Supported Formats**: PDF, DOCX, XLSX, CSV, TXT, MD, JSON, YAML, XML
- **Processing Pipeline**:
  1. Document type detection
  2. Content extraction (text, tables, images, metadata)
  3. Structure analysis (headings, sections, relationships)
  4. Data classification (text, tabular, visual)
  5. Multi-storage persistence

#### 1.2 read_document
- **Purpose**: Read and parse documents into structured data models
- **Input**: File path, extraction template (optional)
- **Output**: Structured document representation
- **Features**:
  - Template-based extraction
  - Schema inference for tabular data
  - Hierarchical content organization
  - Metadata preservation

#### 1.3 read_image
- **Purpose**: Analyze images using multimodal LLM
- **Input**: Image path, analysis instruction/template
- **Output**: Image analysis results, extracted text/data
- **LLM Integration**: Google Gemini 2.5 Pro (multimodal with built-in OCR)
- **Capabilities**:
  - Automatic OCR through Gemini
  - Chart/graph data extraction
  - Object detection and classification
  - Template-based extraction via instructions
  - Results automatically cached via UnifiedCRUD

## Storage Architecture

### Elegant Multi-Storage via StorageModel

The IDP system leverages the existing UnifiedCRUD and StorageModel architecture. Documents are automatically persisted across appropriate storage backends based on their model configuration:

#### Automatic Storage Distribution
```python
class Document(StorageModel):
    class Meta:
        storage_configs = {
            "graph": StorageConfig(storage_type=StorageType.GRAPH),     # Primary - relationships
            "vector": StorageConfig(storage_type=StorageType.VECTOR),   # Auto-embeddings
            "relational": StorageConfig(storage_type=StorageType.RELATIONAL),  # Metadata
            "cache": StorageConfig(storage_type=StorageType.CACHE)      # Fast access
        }
        path = "documents"
        indexes = [
            {"field": "title", "type": "fulltext"},
            {"field": "created_at", "type": "hash"}
        ]
```

**Key Architecture Benefits:**
- **Automatic Embeddings**: Any field stored in VECTOR storage is automatically embedded
- **Transparent Sync**: UnifiedCRUD handles multi-storage synchronization
- **Native Graph Operations**: Dgraph provides built-in traversal algorithms
- **Schema-driven**: Storage distribution defined declaratively in models

## Data Models

### Document Model
```python
class Document(StorageModel):
    id: str  # UUID
    file_path: str
    file_type: str
    file_size: int
    created_at: datetime
    modified_at: datetime
    indexed_at: datetime
    
    # Metadata
    title: str | None
    author: str | None
    subject: str | None
    keywords: list[str]
    language: str
    
    # Content structure
    sections: list[DocumentSection]
    tables: list[DocumentTable]
    images: list[DocumentImage]
    
    # Storage references
    graph_id: str
    vector_ids: list[str]
    relational_ids: dict[str, str]
```

### DocumentSection Model
```python
class DocumentSection(StorageModel):
    id: str
    document_id: str
    parent_section_id: str | None
    
    level: int  # Heading level
    title: str
    content: str
    
    # Navigation
    order: int
    path: str  # e.g., "1.2.3"
    
    # Embeddings
    embedding: list[float]  # Vector representation
    summary: str | None
```

### DocumentTable Model
```python
class DocumentTable(StorageModel):
    id: str
    document_id: str
    section_id: str | None
    
    name: str | None
    headers: list[str]
    rows: list[dict[str, Any]]
    
    # Schema
    schema: dict[str, str]  # Column name -> data type
    primary_key: str | None
    foreign_keys: dict[str, str]  # Column -> referenced table
    
    # Storage
    relational_table: str  # PostgreSQL table name
    indexed_columns: list[str]
```

### DocumentImage Model
```python
class DocumentImage(StorageModel):
    id: str
    document_id: str
    section_id: str | None
    
    file_path: str
    mime_type: str
    dimensions: dict[str, int]  # width, height
    
    # Analysis results
    caption: str | None
    extracted_text: str | None
    detected_objects: list[dict]
    chart_data: dict | None
    
    # Embeddings
    visual_embedding: list[float]
    text_embedding: list[float] | None
    
    # LLM analysis cache
    analysis_prompt: str | None
    analysis_result: str | None
    analysis_timestamp: datetime
```

## Processing Pipelines

### Document Indexing Pipeline
```python
async def index_document_pipeline(file_path: str, options: dict):
    # 1. Document validation and type detection
    doc_type = detect_document_type(file_path)
    
    # 2. Content extraction
    extractor = get_extractor(doc_type)
    raw_content = await extractor.extract(file_path)
    
    # 3. Structure analysis
    structured = analyze_structure(raw_content)
    
    # 4. Multi-storage persistence
    await store_in_graph(structured.relationships)
    await store_in_vector(structured.embeddings)
    await store_in_relational(structured.tables)
    
    # 5. Index creation
    await create_search_indexes(structured)
    
    return structured
```

### Image Analysis Pipeline
```python
async def analyze_image_pipeline(image_path: str, instruction: str):
    # 1. Image preprocessing
    image = preprocess_image(image_path)
    
    # 2. Check cache
    cached = await get_cached_analysis(image_path, instruction)
    if cached:
        return cached
    
    # 3. LLM analysis
    result = await gemini_vision_analyze(image, instruction)
    
    # 4. Result processing
    processed = process_llm_result(result)
    
    # 5. Multi-storage persistence
    await store_in_graph(processed.entities)
    await store_in_vector(processed.embeddings)
    await cache_result(image_path, instruction, processed)
    
    return processed
```

## Query APIs

### Raw Query Methods
```python
class DataOpsQueryAPI:
    # Graph queries
    async def graph_query(self, dql: str, variables: dict = None) -> dict
    
    # Vector queries
    async def vector_search(self, embedding: list[float], limit: int = 10) -> list
    async def semantic_search(self, query: str, limit: int = 10) -> list
    
    # Relational queries
    async def sql_query(self, sql: str, params: dict = None) -> list
    
    # Cross-storage queries
    async def hybrid_search(self, query: dict) -> list
```

### Object-Based Search API
```python
class DocumentSearchAPI:
    async def search_documents(
        self,
        query: str = None,
        filters: dict = None,
        doc_types: list[str] = None,
        date_range: tuple[datetime, datetime] = None,
        limit: int = 20,
        offset: int = 0
    ) -> list[Document]
    
    async def find_similar_documents(
        self,
        document_id: str,
        limit: int = 10
    ) -> list[Document]
    
    async def search_within_document(
        self,
        document_id: str,
        query: str,
        section_only: bool = False
    ) -> list[DocumentSection]
    
    async def extract_entities(
        self,
        document_id: str,
        entity_types: list[str] = None
    ) -> dict[str, list]
    
    async def get_document_graph(
        self,
        document_id: str,
        depth: int = 2
    ) -> dict
```

## Document Extractors

### PDF Extractor
```python
class PDFExtractor:
    async def extract(self, file_path: str) -> dict:
        # Use PyPDF2/pdfplumber for text
        # Use pdf2image for visual content
        # Extract tables with camelot/tabula
        # Preserve formatting and structure
```

### DOCX Extractor
```python
class DOCXExtractor:
    async def extract(self, file_path: str) -> dict:
        # Use python-docx for content
        # Extract styles and formatting
        # Handle embedded images and tables
        # Preserve document structure
```

### Spreadsheet Extractor
```python
class SpreadsheetExtractor:
    async def extract(self, file_path: str) -> dict:
        # Use openpyxl/pandas for XLSX
        # Use csv module for CSV
        # Infer data types and schemas
        # Handle multiple sheets
        # Extract formulas and relationships
```

### Image Extractor
```python
class ImageExtractor:
    async def extract(self, file_path: str) -> dict:
        # Use Pillow for image metadata
        # Use pytesseract for OCR
        # Use Google Vision for advanced analysis
        # Extract EXIF data
```

## Integration Points

### Filesys MCP Server Integration
- Add new tools to `tools/definitions.py`
- Implement handlers in `tools/handlers.py`
- Register with `ToolRegistry`
- Extend file validation for document types

### DataOps Integration
- Register document models with DataOps server
- Implement storage-specific DAOs
- Configure multi-storage synchronization
- Add document-specific CRUD operations

### LLM Integration (Google Gemini)
- API client implementation
- Rate limiting and quota management
- Result caching strategy
- Error handling and fallbacks

## Implementation Phases

### Phase 1: Core Infrastructure
1. Document model definitions
2. Basic extractors (PDF, DOCX, CSV)
3. Storage integration setup
4. MCP tool registration

### Phase 2: Advanced Processing
1. Image analysis with Gemini Vision
2. Table extraction and schema inference
3. Multi-storage synchronization
4. Search API implementation

### Phase 3: Intelligence Layer
1. Entity extraction and linking
2. Document similarity and clustering
3. Automatic categorization
4. Cross-document relationships

### Phase 4: Optimization
1. Processing pipeline optimization
2. Caching strategies
3. Index optimization
4. Query performance tuning

## Security Considerations

### Access Control
- Document-level permissions
- Field-level encryption for sensitive data
- Audit logging for all operations
- Role-based access control integration

### Data Privacy
- PII detection and masking
- GDPR compliance features
- Data retention policies
- Secure deletion capabilities

## Performance Requirements

### Processing Metrics
- PDF processing: < 2s per page
- Image analysis: < 5s per image
- Document indexing: < 10s per document
- Search latency: < 100ms

### Scalability
- Horizontal scaling for processing
- Distributed storage support
- Queue-based processing for large batches
- Streaming for large documents

## Testing Strategy

### Unit Tests
- Extractor functionality
- Model serialization/deserialization
- Storage operations
- Query builders

### Integration Tests
- End-to-end document processing
- Multi-storage synchronization
- LLM integration
- Search functionality

### Performance Tests
- Load testing with various document types
- Concurrent processing scenarios
- Large document handling
- Query performance benchmarks

## Dependencies

### Python Libraries
```txt
# Document Processing
PyPDF2==3.0.1
pdfplumber==0.10.3
python-docx==1.1.0
openpyxl==3.1.2
pandas==2.2.0
camelot-py==0.11.0

# Image Processing
Pillow==10.2.0
pytesseract==0.3.10
opencv-python==4.9.0

# LLM Integration
google-generativeai==0.3.2

# Embeddings
sentence-transformers==2.5.1
tiktoken==0.6.0

# Additional Storage
redis==5.0.1
asyncpg==0.29.0
```

## Graph API Proposal

See [GRAPH_API.md](base/backend/dataops/GRAPH_API.md) for detailed graph API specification.

## Success Metrics

### Functional Metrics
- Document type coverage: 95%+
- Extraction accuracy: 98%+
- Search relevance: 90%+
- Processing success rate: 99%+

### Performance Metrics
- Average processing time: < 5s
- Query response time: < 200ms
- Concurrent processing: 100+ documents
- Storage efficiency: 30% compression

### User Metrics
- API adoption rate
- Search usage patterns
- Document retrieval accuracy
- User satisfaction scores

## Future Enhancements

### Short-term (3-6 months)
- Support for additional file formats
- Advanced table extraction
- Multilingual support
- Real-time processing

### Long-term (6-12 months)
- Custom ML models for extraction
- Automated document classification
- Smart contract parsing
- Video/audio transcription

## Conclusion

This IDP system will provide comprehensive document processing capabilities integrated with the existing infrastructure. The multi-storage approach ensures optimal performance for different query patterns while maintaining data consistency. The LLM integration enables advanced analysis capabilities that go beyond traditional extraction methods.

The phased implementation approach allows for incremental delivery of value while maintaining system stability. The architecture is designed to be extensible, allowing for future enhancements without major refactoring.