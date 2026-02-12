# Retrieval API Contract (Qdrant Vector Search)

**Component**: Qdrant Vector Database Search Layer  
**Input**: Vector query + filters (similar to Step embeddings)  
**Output**: Ranked list of Steps with metadata + text_key references  

---

## Connection & Collection Management

```python
class QdrantClient:
    def __init__(self, url: str = "http://localhost:6333"):
        """
        url: "http://localhost:6333" or "https://prod-qdrant.api.com"
        """
        self.client = qdrant_client.QdrantClient(url=url)
    
    def health_check(self) -> bool:
        """Verify Qdrant server availability"""
        try:
            info = self.client.get_collection("steps")
            return info is not None
        except Exception:
            return False
```

### Collection Initialization (FR-006: Steps collection)

```python
def init_collection(qdrant_client: QdrantClient):
    """Create 'steps' collection with vector config on app startup"""
    try:
        qdrant_client.client.create_collection(
            collection_name="steps",
            vectors_config=VectorsConfig(
                size=384,  # Embedding dimension (all-MiniLM-L6-v2)
                distance=Distance.COSINE
            ),
            optimizers_config=OptimizersConfig(
                default_segment_number=5,
                snapshot_on_idle=True  # Auto-snapshot for durability
            )
        )
        logger.info("Created Qdrant collection 'steps'")
        
    except Exception as e:
        if "already" in str(e):
            logger.debug("Collection 'steps' already exists")
        else:
            raise
```

---

## Write API: Index Embeddings

### Operation: Upsert Step Embeddings (from Ingestion)

```python
def index_step_embeddings(qdrant_client: QdrantClient,
                         step_id: str,
                         trace_id: str,
                         vector: List[float],
                         step_metadata: Dict) -> IndexResult:
    """
    Store embedding vector with filterable metadata (payload).
    Called by ingestion-api.md after generating embeddings for a step.
    """
    try:
        qdrant_client.client.upsert(
            collection_name="steps",
            points=[Point(
                id=hash_to_int(step_id),  # Qdrant requires integer IDs
                vector=vector,
                payload={
                    # Step identity
                    "trace_id": trace_id,
                    "step_id": step_id,
                    "step_index": step_metadata["index"],
                    "role": step_metadata["role"],
                    
                    # Trace identity
                    "domain": step_metadata["domain"],
                    "trace_title": step_metadata["trace_title"],
                    
                    # Versioning (FR-006a: bind to text version)
                    "text_version_bound": step_metadata["text_version"],
                    "embedding_version": step_metadata["embedding_version"],
                    "text_hash": step_metadata["text_hash"],
                    
                    # Danger markers (Phase 2: computed from context)
                    "danger_ambiguity": 0.0,
                    "danger_adversarial": 0.0,
                    "danger_irreversibility": 0.0,
                    "danger_institutional": 0.0,
                    
                    # Timestamps
                    "created_at": datetime.now().isoformat()
                }
            )]
        )
        
        return IndexResult(
            success=True,
            step_id=step_id,
            vector_dim=len(vector),
            stored_at=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Failed to index embedding for step {step_id}: {e}")
        return IndexResult(success=False, error=str(e))
```

---

## Query API: Vector Search

### Query 1: Semantic Search (Find Similar Steps)

```python
def search_similar_steps(qdrant_client: QdrantClient,
                        query_vector: List[float],
                        limit: int = 10,
                        filters: Optional[Dict] = None) -> SearchResult:
    """
    Find steps most similar to query vector.
    Optionally filter by domain, role, or other metadata.
    """
    # Build filter if provided
    query_filter = None
    if filters:
        conditions = []
        if "domain" in filters:
            conditions.append(HasValueFilter(
                key="domain",
                value=filters["domain"]
            ))
        if "role" in filters:
            conditions.append(HasValueFilter(
                key="role",
                value=filters["role"]
            ))
        if "trace_id" in filters:
            conditions.append(HasValueFilter(
                key="trace_id",
                value=filters["trace_id"]
            ))
        
        if conditions:
            query_filter = Filter(must=conditions)
    
    try:
        results = qdrant_client.client.search(
            collection_name="steps",
            query_vector=query_vector,
            query_filter=query_filter,
            limit=limit,
            score_threshold=0.0,  # Return all results; caller thresholds
            with_payload=True,
            with_vectors=False  # Don't return full vector (save bandwidth)
        )
        
        return SearchResult(
            success=True,
            results=[SearchHit(
                step_id=hit.payload["step_id"],
                trace_id=hit.payload["trace_id"],
                similarity_score=hit.score,
                role=hit.payload["role"],
                domain=hit.payload["domain"],
                text_version=hit.payload["text_version_bound"],
                trace_title=hit.payload["trace_title"]
            ) for hit in results],
            query_count=len(results)
        )
        
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return SearchResult(success=False, error=str(e))
```

**Example Usage**:
```python
# Embed query text
query_text = "How do I optimize database performance?"
query_vector = embedding_model.encode(query_text).tolist()

# Search with domain filter
results = search_similar_steps(
    qdrant_client,
    query_vector=query_vector,
    limit=10,
    filters={"domain": "database"}
)

# Caller receives top-10 similar steps in 'database' domain
for hit in results["results"]:
    print(f"Trace {hit.trace_id}: {hit.similarity_score:.3f}")
```

### Query 2: Filtered Search by Domain

```python
def search_by_domain(qdrant_client: QdrantClient,
                    domain: str,
                    limit: int = 100) -> BrowseResult:
    """
    Retrieve all steps in a domain (for dataset exploration).
    Returns step metadata without vectors.
    """
    try:
        points = qdrant_client.client.scroll(
            collection_name="steps",
            scroll_filter=Filter(must=[
                HasValueFilter(key="domain", value=domain)
            ]),
            limit=limit,
            with_payload=True,
            with_vectors=False
        )
        
        return BrowseResult(
            steps=[StepMetadata(**p.payload) for p, _ in points[0]],
            total_count=len(points[0])
        )
        
    except Exception as e:
        logger.error(f"Browse by domain failed: {e}")
        return BrowseResult(steps=[], error=str(e))
```

### Query 3: Batch Search

```python
def batch_search(qdrant_client: QdrantClient,
                query_vectors: List[List[float]],
                limit_per_query: int = 10) -> BatchSearchResult:
    """
    Efficient multi-query search (e.g., find similar steps for top-K reasoning chains).
    Qdrant processes batch internally; better than sequential calls.
    """
    try:
        results = qdrant_client.client.search_batch(
            collection_name="steps",
            requests=[SearchRequest(
                vector=qv,
                limit=limit_per_query,
                with_payload=True
            ) for qv in query_vectors]
        )
        
        return BatchSearchResult(
            batch_results=[
                [SearchHit(
                    step_id=hit.payload["step_id"],
                    similarity_score=hit.score
                ) for hit in batch_result]
                for batch_result in results
            ]
        )
        
    except Exception as e:
        logger.error(f"Batch search failed: {e}")
        return BatchSearchResult(error=str(e))
```

---

## Update API: Version Management (FR-006a)

### Operation: Invalidate Embeddings When Text Updates

```python
def invalidate_embedding(qdrant_client: QdrantClient,
                        step_id: str) -> InvalidateResult:
    """
    Mark embedding as stale when contributor edits text in S3.
    Called by text-versioning-api.md → storage-api.md → retrieval-api.md callback.
    
    Implementation: Set danger_* flags to -1.0 (sentinel for "needs re-embedding").
    Re-embedding happens on-demand or batch during off-peak hours.
    """
    try:
        # Update payload without re-computing vector
        qdrant_client.client.set_payload(
            collection_name="steps",
            payload={
                "danger_ambiguity": -1.0,  # Sentinel: re-embedding needed
                "danger_adversarial": -1.0,
                "text_version_bound": None,  # Unbound from text version
                "stale_embedding": True,
                "invalidated_at": datetime.now().isoformat()
            },
            points_selector=PointIdsList(
                ids=[hash_to_int(step_id)]
            )
        )
        
        logger.info(f"Invalidated embedding for step {step_id}")
        return InvalidateResult(success=True, step_id=step_id)
        
    except Exception as e:
        logger.error(f"Invalidate embedding failed: {e}")
        return InvalidateResult(success=False, error=str(e))
```

### Operation: Re-embed Single Step (On-Demand)

```python
def reembed_step(qdrant_client: QdrantClient,
                step_id: str,
                new_text: str,
                embedding_model) -> ReembedResult:
    """
    Re-compute embedding after text update.
    Called by background job or on-demand when querying stale steps.
    """
    try:
        # Generate new vector
        new_vector = embedding_model.encode(new_text).tolist()
        
        # Upsert with new vector
        qdrant_client.client.upsert(
            collection_name="steps",
            points=[Point(
                id=hash_to_int(step_id),
                vector=new_vector,
                payload={
                    "stale_embedding": False,
                    "embedding_updated_at": datetime.now().isoformat(),
                    "danger_ambiguity": 0.0,  # Reset to recompute (Phase 2)
                    "danger_adversarial": 0.0,
                    "danger_irreversibility": 0.0,
                    "danger_institutional": 0.0
                }
            )]
        )
        
        return ReembedResult(success=True, step_id=step_id)
        
    except Exception as e:
        logger.error(f"Re-embedding failed for step {step_id}: {e}")
        return ReembedResult(success=False, error=str(e))
```

### Background Job: Re-embed Stale Steps

```python
def reembed_stale_steps(qdrant_client: QdrantClient,
                       embedding_model,
                       s3_client,
                       batch_size: int = 1000,
                       max_age_hours: int = 24) -> ReembedBatchResult:
    """
    Periodic background job to re-embed steps with stale embeddings.
    Runs during off-peak hours; can be interrupted and resumed.
    Pulls text from S3 and stores new vectors.
    """
    
    # Find stale embeddings
    stale_points = qdrant_client.client.scroll(
        collection_name="steps",
        scroll_filter=Filter(must=[
            HasValueFilter(key="stale_embedding", value=True)
        ]),
        limit=batch_size,
        with_payload=True
    )
    
    reembedded = 0
    failed = []
    
    for point, _ in stale_points[0]:
        try:
            step_id = point.payload["step_id"]
            text_key = point.payload.get("text_key")  # Should be stored in payload
            
            if not text_key:
                failed.append((step_id, "Missing text_key"))
                continue
            
            # Retrieve text from S3
            full_text = s3_client.get_object(text_key)
            
            # Re-embed
            new_vector = embedding_model.encode(full_text).tolist()
            
            # Update Qdrant
            qdrant_client.client.upsert(
                collection_name="steps",
                points=[Point(
                    id=point.id,
                    vector=new_vector,
                    payload={
                        "stale_embedding": False,
                        "embedding_updated_at": datetime.now().isoformat()
                    }
                )]
            )
            
            reembedded += 1
            
        except Exception as e:
            failed.append((step_id, str(e)))
            logger.error(f"Failed to re-embed {step_id}: {e}")
    
    logger.info(f"Re-embedding batch: {reembedded} succeeded, {len(failed)} failed")
    return ReembedBatchResult(
        reembedded_count=reembedded,
        failed_steps=failed,
        batch_size=len(stale_points[0])
    )
```

---

## Analytics & Maintenance

### Collection Statistics

```python
def get_collection_stats(qdrant_client: QdrantClient) -> CollectionStats:
    """Health metrics for vector store"""
    info = qdrant_client.client.get_collection("steps")
    
    return CollectionStats(
        point_count=info.points_count,
        vector_count=info.vectors_count,
        segments=info.config.params.vectors_size,
        indexed=info.indexed_vectors_count if hasattr(info, "indexed_vectors_count") else None
    )
```

### Collection Maintenance

```python
def optimize_collection(qdrant_client: QdrantClient):
    """Optimize performance (compact segments, rebuild indexes)"""
    try:
        qdrant_client.client.optimize_collection("steps")
        logger.info("Optimized 'steps' collection")
    except Exception as e:
        logger.warning(f"Collection optimization skipped: {e}")
```

---

## Performance Targets (SR-001)

| Operation | Target | Validation |
|-----------|--------|-----------|
| Index single vector | < 10ms | Measure latency; verify upsert completes |
| Search top-10 (no filter) | < 50ms | Measure latency on 1M+ points |
| Search filtered (domain) | < 100ms | Verify pre-filter reduces candidate set |
| Batch search (100 queries) | < 5 sec | All queries processed in parallel |
| Re-embedding stale batch (1K) | < 60 sec | CPU-bound; acceptable for background job |

---

## Error Codes

| Code | Meaning | Handling |
|------|---------|----------|
| `COLLECTION_NOT_FOUND` | 'steps' collection doesn't exist | Call `init_collection()` |
| `POINT_NOT_FOUND` | step_id not in collection | Retry ingestion for this step |
| `INVALID_VECTOR_SIZE` | Vector dimension mismatch | Verify embedding model (should be 384) |
| `PAYLOAD_EXCEEDED` | Payload too large | Externalize large fields or compress |
| `SEARCH_TIMEOUT` | Query took too long | Increase timeout; verify indexes exist |
