# Retrieval API Contract (Qdrant Vector Search)

> **Version 4 (Pass 4)**: Complete rewrite from canonical schemas. Aligns query filters, response types, and examples to [Canonical Schemas](../../docs/reference/canonical-schemas.md) and [Storage Mapping](../../docs/reference/storage-mapping.md).
>
> **Component**: Qdrant Vector Database Query Layer  
> **Input**: Vector query + filters (semantic search over Step or Pattern embeddings)  
> **Output**: Ranked list of Steps/Patterns with full metadata + text references  
> **Requires**: qdrant-client ≥ 1.7, pydantic 2

---

## Connection & Health

```python
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

class QdrantConnection:
    def __init__(self, url: str = "http://localhost:6333", api_key: Optional[str] = None):
        """
        url: "http://localhost:6333" (local) or "https://prod-qdrant.api.com" (cloud)
        api_key: Optional API key for cloud deployments
        """
        self.client = QdrantClient(url=url, api_key=api_key)
    
    def health_check(self) -> bool:
        """Verify Qdrant server is healthy"""
        try:
            info = self.client.get_collections()
            return len(info.collections) > 0
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False


def ensure_collections(qdrant_client: QdrantClient):
    """
    Initialize three collections on app startup (idempotent).
    see [Qdrant Setup](../../docs/reference/qdrant-setup.md) for full config.
    """
    collections_config = [
        ("steps", 384),           # Sentence-transformers output dimension
        ("step_windows", 384),    # FSM context windows
        ("patterns", 384)         # Pattern prototypes
    ]
    
    for collection_name, dim in collections_config:
        try:
            qdrant_client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE)
            )
        except Exception as e:
            if "already" in str(e).lower():
                logger.debug(f"Collection '{collection_name}' already exists")
            else:
                raise
```

---

## Write API: Index Embeddings

### Operation: Upsert Step Embedding (from Ingestion)

```python
from qdrant_client.models import PointStruct

def index_step_embedding(
    qdrant_client: QdrantClient,
    step_id: str,
    trace_id: str,
    vector: List[float],
    step_metadata: Dict[str, Any]
) -> bool:
    """
    Store step embedding vector + searchable payload into 'steps' collection.
    Called by ingestion pipeline after generating embeddings.
    
    Payload schema:
    - Identifiers: step_id, trace_id, index
    - Semantics: role, actor, domain, tags
    - Danger: (Phase 2) danger_ambiguity, danger_adversarial, etc.
    - Versioning: embedding_model, embedding_dim, text_hash
    """
    try:
        payload = {
            # Identifiers
            "step_id": step_id,
            "trace_id": trace_id,
            "index": step_metadata.get("index", 0),
            
            # Semantics
            "role": step_metadata.get("role", "other"),
            "actor": step_metadata.get("actor", "system"),
            "domain": step_metadata.get("domain", "general"),
            "tags": step_metadata.get("tags", []),
            
            # Danger markers (Phase 2: default to 0)
            "danger_ambiguity": step_metadata.get("danger_ambiguity", 0.0),
            "danger_adversarial": step_metadata.get("danger_adversarial", 0.0),
            "danger_irreversibility": step_metadata.get("danger_irreversibility", 0.0),
            "danger_institutional": step_metadata.get("danger_institutional", 0.0),
            
            # Versioning
            "embedding_model": step_metadata.get("embedding_model", "all-MiniLM-L6-v2"),
            "embedding_dim": step_metadata.get("embedding_dim", 384),
            "text_hash": step_metadata.get("text_hash", None),
            
            # Timestamps
            "created_at": datetime.now().isoformat()
        }
        
        qdrant_client.upsert(
            collection_name="steps",
            points=[PointStruct(
                id=step_id,
                vector=vector,
                payload=payload
            )]
        )
        
        logger.debug(f"Indexed step {step_id} into Qdrant")
        return True
    
    except Exception as e:
        logger.error(f"Failed to index step {step_id}: {e}")
        return False
```

---

## Query API: Semantic Search

### Query 1: Search Similar Steps

```python
from qdrant_client.models import FieldCondition, MatchValue, Filter
from pydantic import BaseModel, Field
from typing import Optional, List

class StepSearchRequest(BaseModel):
    """Request: find steps similar to a query vector"""
    
    query_vector: List[float] = Field(
        ...,
        description="Embedding vector (384-dim for all-MiniLM-L6-v2)",
        min_length=384,
        max_length=384
    )
    
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Max results to return"
    )
    
    # Filters (all optional; combined with AND)
    filters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Metadata filters to apply before ranking"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query_vector": [0.123, 0.456, ...],  # 384 floats
                "limit": 10,
                "filters": {
                    "domain": "ml",
                    "role": "observation",
                    "min_danger_irreversibility": 0.5
                }
            }
        }


def search_similar_steps(
    qdrant_client: QdrantClient,
    req: StepSearchRequest
) -> StepSearchResponse:
    """
    Semantic search: find steps closest to query_vector.
    Apply filters server-side for efficiency.
    """
    
    # Build Qdrant filter from request
    conditions = []
    
    if req.filters:
        if "domain" in req.filters:
            conditions.append(FieldCondition(
                key="domain",
                match=MatchValue(value=req.filters["domain"])
            ))
        
        if "role" in req.filters:
            conditions.append(FieldCondition(
                key="role",
                match=MatchValue(value=req.filters["role"])
            ))
        
        if "trace_id" in req.filters:
            conditions.append(FieldCondition(
                key="trace_id",
                match=MatchValue(value=req.filters["trace_id"])
            ))
        
        if "danger_ambiguity" in req.filters:
            # Range filter: steps with danger_ambiguity >= threshold
            min_val = req.filters.get("min_danger_ambiguity", 0.0)
            conditions.append(FieldCondition(
                key="danger_ambiguity",
                range=FieldCondition.RangeOptions(gte=min_val)
            ))
    
    # Construct query filter
    query_filter = Filter(must=conditions) if conditions else None
    
    # Execute search
    try:
        results = qdrant_client.search(
            collection_name="steps",
            query_vector=req.query_vector,
            query_filter=query_filter,
            limit=req.limit,
            with_payload=True
        )
        
        # Transform to canonical response
        hits = [
            StepSearchHit(
                step_id=result.payload.get("step_id"),
                trace_id=result.payload.get("trace_id"),
                role=result.payload.get("role"),
                domain=result.payload.get("domain"),
                danger_scores={
                    "ambiguity": result.payload.get("danger_ambiguity", 0.0),
                    "adversarial": result.payload.get("danger_adversarial", 0.0),
                    "irreversibility": result.payload.get("danger_irreversibility", 0.0),
                    "institutional": result.payload.get("danger_institutional", 0.0)
                },
                similarity=result.score  # COSINE distance [0, 1]
            )
            for result in results
        ]
        
        return StepSearchResponse(
            hits=hits,
            total=len(hits),
            query_time_ms=0  # Qdrant doesn't expose this; estimate later
        )
    
    except Exception as e:
        logger.error(f"Step search failed: {e}")
        return StepSearchResponse(hits=[], total=0, error=str(e))


class StepSearchHit(BaseModel):
    """Single search result"""
    
    step_id: str
    trace_id: str
    role: str
    domain: str
    danger_scores: Dict[str, float] = Field(
        description="danger_ambiguity, adversarial, irreversibility, institutional"
    )
    similarity: float = Field(
        ge=0.0,
        le=1.0,
        description="Similarity score (COSINE: 1.0 = identical, 0.0 = opposite)"
    )


class StepSearchResponse(BaseModel):
    """Response: ranked list of similar steps"""
    
    hits: List[StepSearchHit] = Field(
        description="Ranked by similarity (highest first)"
    )
    total: int = Field(
        description="Number of hits returned"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if search failed"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "hits": [
                    {
                        "step_id": "01J2K3L4M5N6O7P8Q9R0S1T2",
                        "trace_id": "abc123-def456",
                        "role": "observation",
                        "domain": "ml",
                        "danger_scores": {
                            "ambiguity": 0.1,
                            "adversarial": 0.0,
                            "irreversibility": 0.05,
                            "institutional": 0.2
                        },
                        "similarity": 0.89
                    }
                ],
                "total": 1,
                "error": None
            }
        }
```

### Query 2: Retrieve Pattern Recommendations

```python
class PatternSearchRequest(BaseModel):
    """Request: find applicable patterns for current context"""
    
    query_vector: List[float] = Field(
        ...,
        description="Embedding of current FSM state + recent steps",
        min_length=384,
        max_length=384
    )
    
    fsm_id: Optional[str] = Field(
        default=None,
        description="Active FSM (e.g., 'fsm_diagnose_fix')"
    )
    
    current_state: Optional[str] = Field(
        default=None,
        description="Current FSM state (e.g., 'S6_evaluate')"
    )
    
    limit: int = Field(
        default=5,
        ge=1,
        le=50
    )

    class Config:
        json_schema_extra = {
            "example": {
                "query_vector": [0.5, ...],
                "fsm_id": "fsm_diagnose_fix",
                "current_state": "S6_evaluate",
                "limit": 5
            }
        }


def search_patterns(
    qdrant_client: QdrantClient,
    req: PatternSearchRequest
) -> PatternSearchResponse:
    """
    Find patterns applicable to current FSM + state.
    Patterns embedding captures: template semantics + applicability constraints.
    """
    
    conditions = []
    
    if req.fsm_id:
        conditions.append(FieldCondition(
            key="fsm_id",
            match=MatchValue(value=req.fsm_id)
        ))
    
    if req.current_state:
        conditions.append(FieldCondition(
            key="allowed_states",
            match=MatchValue(value=req.current_state)
        ))
    
    query_filter = Filter(must=conditions) if conditions else None
    
    try:
        results = qdrant_client.search(
            collection_name="patterns",
            query_vector=req.query_vector,
            query_filter=query_filter,
            limit=req.limit,
            with_payload=True
        )
        
        hits = [
            PatternSearchHit(
                pattern_id=result.payload.get("pattern_id"),
                name=result.payload.get("name", "Unnamed"),
                type=result.payload.get("type", "fsm_subpath"),
                support=result.payload.get("quality_support", 0),
                similarity=result.score
            )
            for result in results
        ]
        
        return PatternSearchResponse(hits=hits, total=len(hits))
    
    except Exception as e:
        logger.error(f"Pattern search failed: {e}")
        return PatternSearchResponse(hits=[], total=0, error=str(e))


class PatternSearchHit(BaseModel):
    pattern_id: str
    name: str
    type: str
    support: int = Field(description="Number of instances across corpus")
    similarity: float


class PatternSearchResponse(BaseModel):
    hits: List[PatternSearchHit]
    total: int
    error: Optional[str] = None
```

---

## Pagination & Caching

### Cursor-Based Pagination

```python
class PaginatedStepSearchRequest(StepSearchRequest):
    """Add cursor for large result sets"""
    
    cursor: Optional[str] = Field(
        default=None,
        description="Opaque cursor for fetching next page (from previous response)"
    )


class PaginatedStepSearchResponse(StepSearchResponse):
    """Add cursor for large result sets"""
    
    next_cursor: Optional[str] = Field(
        default=None,
        description="Cursor to fetch next page (None = no more results)"
    )
    
    has_more: bool = Field(
        description="Whether more results exist"
    )
```

### Caching Strategy (Phase 2)

- Cache frequent queries (e.g., patterns for each FSM state) in Redis
- TTL: 24 hours or until pattern corpus is updated
- Key: `sha256(fsm_id + current_state)[:16]`

---

## Integration Checklist

- [ ] QdrantConnection class with health check
- [ ] `ensure_collections()` creates all 3 collections with correct dimension
- [ ] `index_step_embedding()` successfully upserts with correct payload schema
- [ ] `search_similar_steps()` returns Steps filtered by metadata (domain, role, danger)
- [ ] `search_patterns()` returns Patterns filtered by FSM applicability
- [ ] Filter conditions use canonical enum values (role, domain, etc.)
- [ ] Response schemas match canonical DangerScores structure
- [ ] Error handling for connection failures, malformed queries
- [ ] Unit tests for each search type (with mock Qdrant)
- [ ] Integration test with real Qdrant (100+ steps) query performance < 200ms
