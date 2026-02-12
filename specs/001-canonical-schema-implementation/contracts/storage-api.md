# Storage API Contract (Neo4j Persistence)

**Component**: Neo4j Graph Persistence Layer  
**Input**: TraceBundle (Trace + Steps + Edges) from ingestion pipeline  
**Output**: Graph constraints enforced, queryable Trace + Step + Edge nodes  

---

## Connection & Session Management

```python
class Neo4jClient:
    def __init__(self, uri: str, auth: Tuple[str, str]):
        """
        uri: "neo4j://localhost:7687" or "neo4j+s://prod.neo4j.io"
        auth: (username, password)
        """
        self.driver = GraphDatabase.driver(uri, auth=auth)
        self.session = self.driver.session()
    
    def close(self):
        self.session.close()
        self.driver.close()
    
    def health_check(self) -> bool:
        """Verify connection and server availability"""
        try:
            result = self.session.run("RETURN 1")
            return result.single() is not None
        except Exception:
            return False
```

---

## Schema Initialization (FR-004a: Constraints)

### Constraint Definitions

```cypher
-- Trace constraints
CREATE CONSTRAINT IF NOT EXISTS trace_id_unique ON (t:Trace) ASSERT t.trace_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS trace_domain_required ON (t:Trace) ASSERT t.domain IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS trace_schema_version_required ON (t:Trace) ASSERT t.provenance_schema_version IS NOT NULL;

-- Step constraints
CREATE CONSTRAINT IF NOT EXISTS step_id_unique ON (s:Step) ASSERT s.step_id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS step_trace_required ON (s:Step) ASSERT s.trace_id IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS step_index_required ON (s:Step) ASSERT s.index IS NOT NULL;

-- Composite unique: (trace_id, step_index)
CREATE INDEX IF NOT EXISTS step_ordering ON (s:Step) FOR (s.trace_id, s.index);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS domain_index ON (t:Trace) FOR (t.domain);
CREATE INDEX IF NOT EXISTS created_at_index ON (t:Trace) FOR (t.created_at);
CREATE INDEX IF NOT EXISTS role_index ON (s:Step) FOR (s.role);
```

**Initialization**: Idempotent; called on app startup

```python
def init_schema(neo4j_client):
    """Create constraints and indexes on server startup"""
    constraints = [
        "CREATE CONSTRAINT IF NOT EXISTS trace_id_unique ON (t:Trace) ASSERT t.trace_id IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS step_id_unique ON (s:Step) ASSERT s.step_id IS UNIQUE",
        # ... (all constraints listed above)
    ]
    
    for constraint in constraints:
        try:
            neo4j_client.session.run(constraint)
            logger.debug(f"Applied constraint: {constraint[:50]}...")
        except Exception as e:
            if "already" in str(e):
                pass  # Already exists, OK
            else:
                raise
```

---

## Write API: Persist TraceBundle

### Operation: Store Trace + Steps + Edges

```python
def store_tracebundle(neo4j_client: Neo4jClient, bundle: TraceBundle) -> StorageResult:
    """
    Atomically store Trace + Steps + Edges to Neo4j.
    If any part fails: entire operation rolled back.
    """
    result = StorageResult(trace_id=bundle.trace.trace_id, success=False, error=None)
    
    tx = neo4j_client.session.begin_transaction()
    try:
        # 1. Create Trace node
        tx.run("""
            CREATE (t:Trace {
                trace_id: $trace_id,
                title: $title,
                domain: $domain,
                problem: $problem,
                n_steps: $n_steps,
                trace_version: $trace_version,
                content_hash: $content_hash,
                provenance_sources: $provenance_sources,
                provenance_license: $provenance_license,
                provenance_sensitivity: $provenance_sensitivity,
                provenance_ingested_at: $provenance_ingested_at,
                provenance_pipeline_version: $provenance_pipeline_version,
                provenance_schema_version: $provenance_schema_version,
                created_at: $created_at,
                updated_at: $updated_at
            })
        """, {
            "trace_id": bundle.trace.trace_id,
            "title": bundle.trace.title,
            "domain": bundle.trace.domain.value,
            "problem": bundle.trace.problem,
            "n_steps": len(bundle.steps),
            "trace_version": bundle.trace.trace_version,
            "content_hash": bundle.trace.content_hash,
            "provenance_sources": [s.dict() for s in bundle.trace.provenance_sources],
            "provenance_license": bundle.trace.provenance_license,
            "provenance_sensitivity": bundle.trace.provenance_sensitivity.value,
            "provenance_ingested_at": bundle.trace.provenance_ingested_at.isoformat(),
            "provenance_pipeline_version": bundle.trace.provenance_pipeline_version,
            "provenance_schema_version": bundle.trace.provenance_schema_version,
            "created_at": bundle.trace.created_at.isoformat(),
            "updated_at": datetime.now().isoformat()
        })
        
        # 2. Create Step nodes
        for step in bundle.steps:
            tx.run("""
                MATCH (t:Trace {trace_id: $trace_id})
                CREATE (s:Step {
                    step_id: $step_id,
                    trace_id: $trace_id,
                    index: $index,
                    role: $role,
                    actor: $actor,
                    text_key: $text_key,
                    text_preview: $text_preview,
                    text_hash: $text_hash,
                    embedding_id: $embedding_id,
                    text_version: $text_version,
                    embedding_version: $embedding_version,
                    created_at: $created_at
                })
                CREATE (t)-[:HAS_STEP {index: $index}]->(s)
            """, {
                "trace_id": bundle.trace.trace_id,
                "step_id": step.step_id,
                "index": step.index,
                "role": step.role.value,
                "actor": step.actor,
                "text_key": step.text_key,
                "text_preview": step.text_preview,
                "text_hash": step.text_hash,
                "embedding_id": step.embedding_id,
                "text_version": step.text_version,
                "embedding_version": step.embedding_version,
                "created_at": step.created_at.isoformat()
            })
        
        # 3. Create NEXT edges between Steps
        for i, edge in enumerate(bundle.edges):
            tx.run("""
                MATCH (src:Step {step_id: $src_id}), (dst:Step {step_id: $dst_id})
                CREATE (src)-[e:NEXT {weight: $weight}]->(dst)
            """, {
                "src_id": edge.src_id,
                "dst_id": edge.dst_id,
                "weight": edge.weight
            })
        
        # 4. Commit transaction
        tx.commit()
        result.success = True
        logger.info(f"Stored trace {bundle.trace.trace_id} with {len(bundle.steps)} steps")
        
    except Exception as e:
        tx.rollback()
        result.error = str(e)
        logger.error(f"Failed to store trace {bundle.trace.trace_id}: {e}", exc_info=True)
    
    return result
```

---

## Query API: Retrieve Traces

### Query 1: Fetch Trace by ID

```python
def get_trace(neo4j_client: Neo4jClient, trace_id: str) -> Optional[TraceWithSteps]:
    """Retrieve full trace with all steps and edges"""
    result = neo4j_client.session.run("""
        MATCH (t:Trace {trace_id: $trace_id})
        OPTIONAL MATCH (t)-[:HAS_STEP]->(s:Step)
        OPTIONAL MATCH (s)-[e:NEXT]->(s2:Step)
        RETURN t, collect(s) AS steps, collect(e) AS edges
    """, trace_id=trace_id)
    
    record = result.single()
    if not record:
        return None
    
    trace_data = dict(record["t"])
    steps = [dict(s) for s in record["steps"]]
    
    return TraceWithSteps(
        trace=Trace(**trace_data),
        steps=[Step(**s) for s in steps],
        step_count=len(steps)
    )
```

### Query 2: Search Traces by Domain

```python
def search_traces_by_domain(neo4j_client: Neo4jClient, 
                           domain: DomainTag, 
                           limit: int = 100) -> List[TraceMetadata]:
    """Find traces in a specific domain"""
    result = neo4j_client.session.run("""
        MATCH (t:Trace {domain: $domain})
        RETURN t.trace_id, t.title, t.domain, t.n_steps, t.created_at
        ORDER BY t.created_at DESC
        LIMIT $limit
    """, domain=domain.value, limit=limit)
    
    return [TraceMetadata(**dict(record)) for record in result]
```

### Query 3: Retrieve Step Lineage (for FSM-adaptive windows)

```python
def get_step_lineage(neo4j_client: Neo4jClient, 
                     step_id: str, 
                     window_depth: int = 5) -> StepWindow:
    """
    Retrieve step + context steps (predecessors/successors).
    Used for computing FSM-adaptive windows (RQ-5).
    """
    result = neo4j_client.session.run("""
        // Find the step
        MATCH (center:Step {step_id: $step_id})
        
        // Find predecessors (up to window_depth hops back)
        OPTIONAL MATCH (center)<-[:NEXT*0..$(window_depth-1)]-(pred:Step)
        WHERE pred.index < center.index
        
        // Find successors (up to window_depth hops forward)
        OPTIONAL MATCH (center)-[:NEXT*0..$(window_depth-1)]->(succ:Step)
        WHERE succ.index > center.index
        
        RETURN 
            center,
            collect(DISTINCT pred) AS predecessors,
            collect(DISTINCT succ) AS successors
    """, step_id=step_id, window_depth=window_depth)
    
    record = result.single()
    if not record:
        return None
    
    center = Step(**dict(record["center"]))
    preds = [Step(**dict(s)) for s in record["predecessors"] if s]
    succs = [Step(**dict(s)) for s in record["successors"] if s]
    
    return StepWindow(
        center=center,
        predecessors=preds,
        successors=succs,
        depth_used=min(window_depth, max(len(preds), len(succs)))
    )
```

### Query 4: Performance Statistics

```python
def get_storage_stats(neo4j_client: Neo4jClient) -> StorageStats:
    """Get graph health metrics"""
    result = neo4j_client.session.run("""
        MATCH (t:Trace)
        RETURN 
            count(t) AS trace_count,
            avg(t.n_steps) AS avg_steps_per_trace,
            max(t.n_steps) AS max_steps,
            count(DISTINCT t.domain) AS domain_count
    """)
    
    record = result.single()
    return StorageStats(
        trace_count=record["trace_count"],
        avg_steps=record["avg_steps_per_trace"],
        max_steps=record["max_steps"],
        domain_count=record["domain_count"]
    )
```

---

## Update API: Version Management (FR-011)

### Update Step Text Version (when predecessor edited)

```python
def update_step_text_version(neo4j_client: Neo4jClient,
                            step_id: str,
                            new_text_key: str,
                            new_text_hash: str,
                            new_text_version: int,
                            contributor_id: str) -> UpdateResult:
    """
    Mark embedding as stale when text version increments.
    Called by text-versioning-api.md when contributor edits markdown in S3.
    """
    tx = neo4j_client.session.begin_transaction()
    try:
        # 1. Update step text metadata
        tx.run("""
            MATCH (s:Step {step_id: $step_id})
            SET s.text_key = $new_text_key,
                s.text_hash = $new_text_hash,
                s.text_version = $new_text_version,
                s.embedding_version = NULL,  -- Mark as stale
                s.updated_at = $now
        """, {
            "step_id": step_id,
            "new_text_key": new_text_key,
            "new_text_hash": new_text_hash,
            "new_text_version": new_text_version,
            "now": datetime.now().isoformat()
        })
        
        # 2. Log edit in audit trail (optional: separate AUDIT_EDIT node)
        tx.run("""
            MATCH (s:Step {step_id: $step_id})
            CREATE (s)-[:EDITED_BY {
                contributor_id: $contributor_id,
                timestamp: $timestamp,
                new_version: $new_version
            }]->()
        """, {
            "step_id": step_id,
            "contributor_id": contributor_id,
            "timestamp": datetime.now().isoformat(),
            "new_version": new_text_version
        })
        
        tx.commit()
        return UpdateResult(success=True, step_id=step_id, new_version=new_text_version)
        
    except Exception as e:
        tx.rollback()
        logger.error(f"Failed to update step version {step_id}: {e}")
        return UpdateResult(success=False, error=str(e))
```

---

## Deletion API (Cleanup/Retention)

```python
def delete_trace(neo4j_client: Neo4jClient, trace_id: str) -> DeleteResult:
    """
    Soft delete: mark as deleted but preserve in graph for audit.
    Hard delete: remove all nodes/relationships.
    """
    tx = neo4j_client.session.begin_transaction()
    try:
        # Option 1: Soft delete
        tx.run("""
            MATCH (t:Trace {trace_id: $trace_id})
            SET t.deleted_at = $now, t.is_deleted = true
        """, trace_id=trace_id, now=datetime.now().isoformat())
        
        # Option 2: Hard delete (use with caution)
        # tx.run("""
        #     MATCH (t:Trace {trace_id: $trace_id})
        #     DETACH DELETE t
        # """, trace_id=trace_id)
        
        tx.commit()
        logger.info(f"Soft-deleted trace {trace_id}")
        return DeleteResult(success=True, trace_id=trace_id)
        
    except Exception as e:
        tx.rollback()
        return DeleteResult(success=False, error=str(e))
```

---

## Transaction Semantics (FR-005)

- **All-or-nothing**: If any step, edge, or constraint fails, entire TraceBundle rollback
- **Isolation Level**: SNAPSHOT (default for Neo4j)
- **Durability**: Committed transactions survive server restart
- **Consistency**: Constraints enforced on write; query results always satisfy constraints

---

## Performance Targets (SR-001)

| Operation | Target | Validation |
|-----------|--------|-----------|
| Store TraceBundle (100 steps) | < 50ms | Measure with timer; log slow queries |
| Query trace by ID | < 10ms | Verify trace_id_unique index exists |
| Search domain (1K results) | < 50ms | Verify domain_index exists |
| Lineage retrieval (depth=5) | < 30ms | Use EXPLAIN to analyze query plan |

---

## Error Codes

| Code | Meaning | Handling |
|------|---------|----------|
| `CONSTRAINT_VIOLATION` | Duplicate trace_id or invalid data | Retry with new trace_id or validate schema |
| `CONNECTION_TIMEOUT` | Neo4j server unavailable | Exponential backoff; max 3 retries |
| `TRANSACTION_CONFLICT` | Concurrent writes to same trace | Retry from ingestion layer |
| `DISK_FULL` | Graph database storage exhausted | Alert operator; trigger retention cleanup |
