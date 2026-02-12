# Storage API Contract (Neo4j Persistence)

> **Version 4 (Pass 4)**: Complete rewrite from canonical schemas. Aligns constraints, Cypher syntax (Neo4j 5.x), and persistence patterns to [Canonical Schemas](../../docs/reference/canonical-schemas.md) and [Storage Mapping](../../docs/reference/storage-mapping.md).
>
> **Component**: Neo4j Graph Persistence Layer  
> **Input**: `TraceBundle` (Trace + Steps + Edges + Artifacts) from ingestion  
> **Output**: Graph constraints enforced, queryable Trace + Step + Edge nodes  
> **Requires**: neo4j ≥ 5.0, pydantic 2

---

## Connection & Session Management

```python
from neo4j import GraphDatabase, Driver, ManagedTransaction
from typing import Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class Neo4jConnection:
    def __init__(self, uri: str, auth: Tuple[str, str], database: str = "neo4j"):
        """
        uri: "neo4j://localhost:7687" (local) or "neo4j+s://prod.db.neo4j.io" (cloud)
        auth: (username, password)
        database: "neo4j" (default) or custom database name
        """
        self.driver = GraphDatabase.driver(uri, auth=auth)
        self.database = database
    
    def close(self):
        self.driver.close()
    
    def health_check(self) -> bool:
        """Verify Neo4j server is reachable"""
        try:
            with self.driver.session(database=self.database) as session:
                result = session.run("RETURN 1 AS status")
                return result.single() is not None
        except Exception as e:
            logger.error(f"Neo4j health check failed: {e}")
            return False
```

---

## Schema Initialization (Neo4j 5.x)

### Constraints & Indexes

```cypher
-- Neo4j 5.x syntax uses "CREATE CONSTRAINT ... FOR (...) REQUIRE ..."

-- Trace constraints
CREATE CONSTRAINT trace_id_unique IF NOT EXISTS
FOR (t:Trace) REQUIRE t.trace_id IS UNIQUE;

CREATE CONSTRAINT trace_domain_required IF NOT EXISTS
FOR (t:Trace) REQUIRE t.domain IS NOT NULL;

-- Step constraints
CREATE CONSTRAINT step_id_unique IF NOT EXISTS
FOR (s:Step) REQUIRE s.step_id IS UNIQUE;

CREATE CONSTRAINT step_trace_required IF NOT EXISTS
FOR (s:Step) REQUIRE s.trace_id IS NOT NULL;

CREATE CONSTRAINT step_index_required IF NOT EXISTS
FOR (s:Step) REQUIRE s.index IS NOT NULL;

-- Artifact constraints
CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS
FOR (a:Artifact) REQUIRE a.artifact_id IS UNIQUE;

-- Pattern constraints
CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS
FOR (p:Pattern) REQUIRE p.pattern_id IS UNIQUE;

-- Indexes for query performance
CREATE INDEX trace_domain_idx IF NOT EXISTS FOR (t:Trace) ON (t.domain);
CREATE INDEX trace_created_at_idx IF NOT EXISTS FOR (t:Trace) ON (t.created_at);

CREATE INDEX step_trace_index_idx IF NOT EXISTS FOR (s:Step) ON (s.trace_id, s.index);
CREATE INDEX step_role_idx IF NOT EXISTS FOR (s:Step) ON (s.role);
CREATE INDEX step_fsm_idx IF NOT EXISTS FOR (s:Step) ON (s.fsm_id, s.fsm_state);

CREATE INDEX artifact_type_idx IF NOT EXISTS FOR (a:Artifact) ON (a.type);
CREATE INDEX pattern_type_idx IF NOT EXISTS FOR (p:Pattern) ON (p.type);
```

### Initialization Python Code

```python
def init_schema(neo4j_conn: Neo4jConnection) -> Tuple[bool, Optional[str]]:
    """
    Create all constraints and indexes on server startup (idempotent).
    Returns (success, error_message).
    """
    constraints = [
        # Trace
        "CREATE CONSTRAINT trace_id_unique IF NOT EXISTS FOR (t:Trace) REQUIRE t.trace_id IS UNIQUE",
        "CREATE CONSTRAINT trace_domain_required IF NOT EXISTS FOR (t:Trace) REQUIRE t.domain IS NOT NULL",
        
        # Step
        "CREATE CONSTRAINT step_id_unique IF NOT EXISTS FOR (s:Step) REQUIRE s.step_id IS UNIQUE",
        "CREATE CONSTRAINT step_trace_required IF NOT EXISTS FOR (s:Step) REQUIRE s.trace_id IS NOT NULL",
        "CREATE CONSTRAINT step_index_required IF NOT EXISTS FOR (s:Step) REQUIRE s.index IS NOT NULL",
        
        # Artifact
        "CREATE CONSTRAINT artifact_id_unique IF NOT EXISTS FOR (a:Artifact) REQUIRE a.artifact_id IS UNIQUE",
        
        # Pattern
        "CREATE CONSTRAINT pattern_id_unique IF NOT EXISTS FOR (p:Pattern) REQUIRE p.pattern_id IS UNIQUE",
    ]
    
    indexes = [
        "CREATE INDEX trace_domain_idx IF NOT EXISTS FOR (t:Trace) ON (t.domain)",
        "CREATE INDEX trace_created_at_idx IF NOT EXISTS FOR (t:Trace) ON (t.created_at)",
        "CREATE INDEX step_trace_index_idx IF NOT EXISTS FOR (s:Step) ON (s.trace_id, s.index)",
        "CREATE INDEX step_role_idx IF NOT EXISTS FOR (s:Step) ON (s.role)",
        "CREATE INDEX step_fsm_idx IF NOT EXISTS FOR (s:Step) ON (s.fsm_id, s.fsm_state)",
        "CREATE INDEX artifact_type_idx IF NOT EXISTS FOR (a:Artifact) ON (a.type)",
        "CREATE INDEX pattern_type_idx IF NOT EXISTS FOR (p:Pattern) ON (p.type)",
    ]
    
    try:
        with neo4j_conn.driver.session(database=neo4j_conn.database) as session:
            for constraint in constraints:
                session.run(constraint)
                logger.debug(f"Applied constraint: {constraint[:60]}...")
            
            for index in indexes:
                session.run(index)
                logger.debug(f"Applied index: {index[:60]}...")
        
        logger.info("Neo4j schema initialization complete")
        return True, None
    
    except Exception as e:
        logger.error(f"Schema initialization failed: {e}")
        return False, str(e)
```

---

## Write API: Persist TraceBundle

### Operation: Atomic Store (All-or-Nothing)

```python
from grimoire.canonical_schema import TraceBundle
import json

def store_tracebundle(
    neo4j_conn: Neo4jConnection,
    bundle: TraceBundle
) -> Tuple[bool, Optional[str]]:
    """
    Atomically persist TraceBundle to Neo4j.
    Single transaction: if any part fails, entire operation rolls back.
    
    Returns (success, error_message).
    """
    
    trace_id = bundle.trace.trace_id
    
    try:
        with neo4j_conn.driver.session(database=neo4j_conn.database) as session:
            # Begin transaction
            tx = session.begin_transaction()
            
            try:
                # 1. Create Trace node
                tx.run("""
                    CREATE (t:Trace {
                        trace_id: $trace_id,
                        title: $title,
                        domain: $domain,
                        problem: $problem,
                        tags: $tags,
                        n_steps: $n_steps,
                        
                        provenance_source_types: $source_types,
                        provenance_source_ids: $source_ids,
                        provenance_license: $license,
                        sensitivity: $sensitivity,
                        ingested_at: $ingested_at,
                        pipeline_version: $pipeline_version,
                        schema_version: $schema_version,
                        
                        created_at: $created_at,
                        updated_at: $updated_at
                    })
                """, {
                    "trace_id": bundle.trace.trace_id,
                    "title": bundle.trace.title or "(untitled)",
                    "domain": bundle.trace.domain.value,
                    "problem": bundle.trace.problem or "",
                    "tags": bundle.trace.tags,
                    "n_steps": bundle.trace.n_steps or len(bundle.steps),
                    
                    "source_types": [s.source_type.value for s in bundle.trace.provenance.sources],
                    "source_ids": [s.source_id for s in bundle.trace.provenance.sources if s.source_id],
                    "license": bundle.trace.provenance.license_info.license.value if bundle.trace.provenance.license_info else "unknown",
                    "sensitivity": bundle.trace.provenance.sensitivity.value,
                    "ingested_at": bundle.trace.provenance.ingested_at.isoformat() if bundle.trace.provenance.ingested_at else None,
                    "pipeline_version": bundle.trace.provenance.pipeline_version,
                    "schema_version": bundle.trace.provenance.schema_version,
                    
                    "created_at": bundle.trace.created_at.isoformat() if bundle.trace.created_at else datetime.now().isoformat(),
                    "updated_at": bundle.trace.updated_at.isoformat() if bundle.trace.updated_at else None
                })
                
                logger.debug(f"Created Trace {trace_id}")
                
                # 2. Create Step nodes
                for step in bundle.steps:
                    tx.run("""
                        MATCH (t:Trace {trace_id: $trace_id})
                        CREATE (s:Step {
                            step_id: $step_id,
                            trace_id: $trace_id,
                            index: $index,
                            actor: $actor,
                            role: $role,
                            text: $text,
                            fsm_id: $fsm_id,
                            fsm_state: $fsm_state,
                            created_at: $created_at
                        })
                        CREATE (t)-[:HAS_STEP]->(s)
                    """, {
                        "trace_id": bundle.trace.trace_id,
                        "step_id": step.step_id,
                        "index": step.index,
                        "actor": step.actor,
                        "role": step.role.value,
                        "text": step.text[:500] if step.text else "",  # Store preview; full text lives in S3
                        "fsm_id": step.fsm_id.value if step.fsm_id else None,
                        "fsm_state": step.fsm_state.value if step.fsm_state else None,
                        "created_at": step.created_at.isoformat() if step.created_at else datetime.now().isoformat()
                    })
                
                logger.debug(f"Created {len(bundle.steps)} steps")
                
                # 3. Create Artifact nodes
                for artifact in bundle.artifacts:
                    tx.run("""
                        MATCH (t:Trace {trace_id: $trace_id})
                        CREATE (a:Artifact {
                            artifact_id: $artifact_id,
                            type: $type,
                            title: $title,
                            domain: $domain,
                            priority: $priority
                        })
                        CREATE (t)-[:HAS_ARTIFACT]->(a)
                    """, {
                        "trace_id": bundle.trace.trace_id,
                        "artifact_id": artifact.artifact_id,
                        "type": artifact.type.value,
                        "title": artifact.title or "(untitled)",
                        "domain": artifact.domain.value if artifact.domain else "general",
                        "priority": artifact.priority
                    })
                
                logger.debug(f"Created {len(bundle.artifacts)} artifacts")
                
                # 4. Create relationship edges
                for edge in bundle.edges:
                    # Determine source/dest nodes
                    src_label = "Step" if edge.src.type.value == "step" else "Artifact"
                    dst_label = "Step" if edge.dst.type.value == "step" else "Artifact"
                    
                    tx.run(f"""
                        MATCH (src:{src_label} {{{src_label.lower()}_id: $src_id}})
                        MATCH (dst:{dst_label} {{{dst_label.lower()}_id: $dst_id}})
                        CREATE (src)-[r:{edge.type.value.upper()} {{
                            edge_id: $edge_id,
                            weight: $weight,
                            label: $label
                        }}]->(dst)
                    """, {
                        "src_id": edge.src.id,
                        "dst_id": edge.dst.id,
                        "edge_id": edge.edge_id,
                        "weight": edge.weight or 1.0,
                        "label": edge.label or None
                    })
                
                logger.debug(f"Created {len(bundle.edges)} edges")
                
                # Commit
                tx.commit()
                logger.info(f"Successfully stored TraceBundle {trace_id}")
                return True, None
            
            except Exception as e:
                tx.rollback()
                logger.error(f"Transaction failed for {trace_id}: {e}", exc_info=True)
                return False, str(e)
    
    except Exception as e:
        logger.error(f"Session error for {trace_id}: {e}", exc_info=True)
        return False, str(e)
```

---

## Query API: Retrieve Traces

### Query 1: Get Trace with All Steps

```cypher
-- Retrieve full trace + steps + edges
MATCH (t:Trace {trace_id: $trace_id})
OPTIONAL MATCH (t)-[:HAS_STEP]->(s:Step)
OPTIONAL MATCH (s1)-[e]->(s2) WHERE s1.trace_id = $trace_id AND s2.trace_id = $trace_id
OPTIONAL MATCH (t)-[:HAS_ARTIFACT]->(a:Artifact)
RETURN t, collect(DISTINCT s) as steps, collect(DISTINCT e) as edges, collect(DISTINCT a) as artifacts
ORDER BY s.index ASC
```

### Query 2: Search Traces by Domain + Tags

```cypher
-- Find traces by domain and tags
MATCH (t:Trace)
WHERE t.domain = $domain
  AND (size($tags) = 0 OR any(tag IN t.tags WHERE tag IN $tags))
RETURN t
ORDER BY t.created_at DESC
LIMIT $limit
```

### Query 3: Traverse Steps by FSM State

```cypher
-- Find sequences of steps in a specific FSM state
MATCH (t:Trace {trace_id: $trace_id})
MATCH (t)-[:HAS_STEP]->(s:Step)
WHERE s.fsm_state = $state
OPTIONAL MATCH (s)-[:NEXT]->(next:Step)
RETURN s, next
ORDER BY s.index ASC
```

---

## Bulk Operations

### Batch Store (Multiple Traces)

```python
def store_tracebundles_batch(
    neo4j_conn: Neo4jConnection,
    bundles: List[TraceBundle],
    batch_size: int = 100
) -> Tuple[int, int]:
    """
    Store multiple bundles (e.g., from ingestion batch).
    Returns (successful_count, failed_count).
    """
    
    success_count = 0
    failure_count = 0
    
    for i, bundle in enumerate(bundles):
        success, error = store_tracebundle(neo4j_conn, bundle)
        if success:
            success_count += 1
        else:
            failure_count += 1
            logger.warning(f"Failed to store bundle {i}: {error}")
    
    logger.info(f"Batch result: {success_count} successful, {failure_count} failed")
    return success_count, failure_count
```

---

## Maintenance

### Soft Delete (Mark Deleted, Not Removed)

```python
def soft_delete_trace(
    neo4j_conn: Neo4jConnection,
    trace_id: str
) -> bool:
    """Mark a trace as deleted (set deleted_at timestamp)"""
    
    try:
        with neo4j_conn.driver.session(database=neo4j_conn.database) as session:
            result = session.run("""
                MATCH (t:Trace {trace_id: $trace_id})
                SET t.deleted_at = $deleted_at
                RETURN t
            """, {
                "trace_id": trace_id,
                "deleted_at": datetime.now().isoformat()
            })
            
            return result.single() is not None
    
    except Exception as e:
        logger.error(f"Soft delete failed for {trace_id}: {e}")
        return False
```

### Index Maintenance

```python
def rebuild_indexes(neo4j_conn: Neo4jConnection) -> bool:
    """Rebuild all indexes for optimization (requires ADMIN privilege)"""
    
    try:
        with neo4j_conn.driver.session(database=neo4j_conn.database) as session:
            session.run("CALL db.indexes.fulltext.await()")
            logger.info("Indexes rebuilt successfully")
            return True
    
    except Exception as e:
        logger.error(f"Index rebuild failed: {e}")
        return False
```

---

## Integration Checklist

- [ ] Neo4jConnection class with health check
- [ ] `init_schema()` creates all constraints and indexes (Neo4j 5.x syntax)
- [ ] `store_tracebundle()` uses transaction (all-or-nothing semantics)
- [ ] Trace node stores provenance metadata correctly
- [ ] Step nodes use canonical role enums (lowercase values)
- [ ] Edges created with correct relationship type (NEXT, SUPPORTS, REVISES, etc.)
- [ ] Artifacts created with canonical type enums
- [ ] Error handling + logging at each stage
- [ ] Batch operations (`store_tracebundles_batch`) with partial success handling
- [ ] Soft delete implementation
- [ ] Unit tests for schema init
- [ ] Integration test: store 100-step trace + verify full traversal
- [ ] Performance test: store 10K traces, query time < 200ms
