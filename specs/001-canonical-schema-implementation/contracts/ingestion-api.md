# Ingestion API Contract

> **Version 4 (Pass 4)**: Complete rewrite from canonical schemas. Aligns all types, examples, and validation to [Canonical Schemas](../../docs/reference/canonical-schemas.md).
>
> **Component**: HuggingFace Dataset Parser & Ingestion Pipeline  
> **Input**: HuggingFace dataset ID + optional parameters  
> **Output**: `TraceBundle` (Trace + Steps + Edges + Artifacts) persisted to Neo4j / Qdrant / S3  
> **Requires**: Pydantic 2, neo4j, qdrant_client, datasets, ulid

---

## API Endpoint: POST /ingest

### Request Schema

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class IngestionRequest(BaseModel):
    """
    Ingest a HuggingFace dataset and normalize to canonical schema.
    All fields directly correspond to canonical TraceBundle construction.
    """
    
    # Dataset selection (required)
    dataset_id: str = Field(
        ...,
        description="HuggingFace dataset identifier (e.g., 'open-thoughts/OpenThoughts-114k')",
        examples=["open-thoughts/OpenThoughts-114k"]
    )
    
    # Optional parameters
    dataset_split: Optional[str] = Field(
        default="train",
        description="Dataset split to ingest ('train', 'validation', 'test')"
    )
    max_traces: Optional[int] = Field(
        default=None,
        description="Limit number of traces (None = all records)"
    )
    batch_size: int = Field(
        default=100,
        ge=1,
        le=10000,
        description="Records per batch during processing"
    )
    
    # Embedding configuration (Phase 2)
    embedding_model_id: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        description="HuggingFace model for generating step embeddings (384-dim default)"
    )
    embedding_dim_override: Optional[int] = Field(
        default=None,
        description="Override model dimension; if provided, must be ≤ 8192"
    )
    
    # Domain tagging (Phase 1)
    domain_default: str = Field(
        default="general",
        description="Default domain (general|software|ml|data|security|product|legal|health|finance)"
    )
    
    # Dry-run mode
    dry_run: bool = Field(
        default=False,
        description="Validate without storing to Neo4j / Qdrant"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "dataset_id": "open-thoughts/OpenThoughts-114k",
                "dataset_split": "train",
                "max_traces": 1000,
                "batch_size": 100,
                "embedding_model_id": "sentence-transformers/all-MiniLM-L6-v2",
                "domain_default": "general",
                "dry_run": False
            }
        }
```

### Response Schema

```python
class IngestionResponse(BaseModel):
    """Result of a successful ingestion batch"""
    
    trace_ids: List[str] = Field(
        description="List of trace IDs successfully ingested"
    )
    n_traces: int = Field(
        description="Total traces processed"
    )
    n_steps: int = Field(
        description="Total steps created across all traces"
    )
    n_edges: int = Field(
        description="Total edges created (NEXT + signal edges)"
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Non-critical errors (trace skipped but batch continued)"
    )
    duration_seconds: float = Field(
        description="Total processing time"
    )
    status: str = Field(
        examples=["success", "partial", "failed"]
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_ids": ["abc123-def456", "ghi789-jkl012"],
                "n_traces": 2,
                "n_steps": 15,
                "n_edges": 13,
                "errors": [],
                "duration_seconds": 2.34,
                "status": "success"
            }
        }
```

---

## Processing Pipeline

### Stage 1: Validate Request

```python
def validate_ingestion_request(req: IngestionRequest) -> Tuple[bool, Optional[str]]:
    """Return (is_valid, error_message)"""
    if req.embedding_dim_override and req.embedding_dim_override > 8192:
        return False, "embedding_dim_override must be ≤ 8192"
    if req.max_traces and req.max_traces < 1:
        return False, "max_traces must be ≥ 1"
    if req.batch_size < 1 or req.batch_size > 10000:
        return False, "batch_size must be in [1, 10000]"
    return True, None
```

### Stage 2: Load HuggingFace Dataset

```python
from datasets import load_dataset
from typing import Generator, Dict, Any

def load_hf_records(
    dataset_id: str,
    split: str = "train",
    max_records: Optional[int] = None
) -> Generator[Dict[str, Any], None, None]:
    """
    Stream records from HuggingFace dataset.
    Yields one record at a time (memory-efficient).
    """
    ds = load_dataset(dataset_id, split=split, streaming=False)
    
    if max_records:
        ds = ds.take(max_records)
    
    for record in ds:
        yield record
```

### Stage 3: Normalize Record → Canonical TraceBundle

The canonical schema requires: `TraceBundle(trace, steps, artifacts, edges)`.

For OpenThoughts-like datasets, normalize as follows:

```python
from datetime import datetime
from uuid import uuid4
import hashlib
from grimoire.canonical_schema import (
    Trace, Step, Edge, Artifact, TraceBundle,
    SourceRef, Provenance, LicenseInfo,
    DomainTag, StepRole, EdgeType, NodeRef, NodeRefType,
    Sensitivity, LicenseType, SourceType
)

def normalize_record_to_tracebundle(
    hf_record: Dict[str, Any],
    dataset_id: str,
    split: str,
    domain_default: str = "general"
) -> TraceBundle:
    """
    Transform a single HuggingFace record into a canonical TraceBundle.
    
    Assumes record has structure:
    {
        "problem": str,
        "messages": [{"role": str, "content": str}, ...],
        "thought_process": str (optional),
        "answer": str (optional)
    }
    """
    
    # Extract fields
    problem_text = hf_record.get("problem", "")
    messages = hf_record.get("messages", [])
    thought_text = hf_record.get("thought_process", "")
    answer_text = hf_record.get("answer", "")
    record_id = hf_record.get("id")
    
    # ---- Trace Creation ----
    
    # Generate deterministic trace_id
    trace_id = generate_trace_id(problem_text, domain_default)
    
    # Determine domain (use inference in Phase 2; for now, use default)
    domain = DomainTag(domain_default) if domain_default in DomainTag.__members__ else DomainTag.GENERAL
    
    # Create Provenance
    provenance = Provenance(
        sources=[SourceRef(
            source_type=SourceType.HUGGINGFACE,
            source_id=dataset_id,
            split=split,
            record_id=str(record_id) if record_id else None,
            created_at=datetime.now()
        )],
        license_info=LicenseInfo(
            license=LicenseType.APACHE_2,
            notes="Normalized from OpenThoughts dataset"
        ),
        sensitivity=Sensitivity.PUBLIC,
        ingested_at=datetime.now(),
        pipeline_version="0.1.0-alpha",
        schema_version="v1"
    )
    
    # Create Trace
    trace = Trace(
        trace_id=trace_id,
        title=problem_text[:100] if problem_text else "Untitled",
        domain=domain,
        tags=[],
        problem=problem_text,
        provenance=provenance,
        outcome={},
        n_steps=len(messages) + (2 if thought_text else 1),
        created_at=datetime.now()
    )
    
    # ---- Steps Creation ----
    
    steps = []
    
    # Step 0: Initial problem (GOAL)
    initial_step = Step(
        step_id=generate_ulid(),
        trace_id=trace.trace_id,
        index=0,
        actor="user",
        role=StepRole.GOAL,
        text=problem_text if problem_text else "(empty problem)",
        created_at=datetime.now()
    )
    steps.append(initial_step)
    
    # Steps 1..N: Message exchanges
    for i, msg in enumerate(messages, start=1):
        role_map = {
            "user": StepRole.QUESTION,
            "assistant": StepRole.OBSERVATION,
            "system": StepRole.OBSERVATION
        }
        
        step = Step(
            step_id=generate_ulid(),
            trace_id=trace.trace_id,
            index=i,
            actor=msg.get("role", "system"),
            role=role_map.get(msg.get("role"), StepRole.OTHER),
            text=msg.get("content", ""),
            created_at=datetime.now()
        )
        steps.append(step)
    
    # Optional: Thought process as CRITIQUE step
    if thought_text:
        critique_step = Step(
            step_id=generate_ulid(),
            trace_id=trace.trace_id,
            index=len(steps),
            actor="system",
            role=StepRole.CRITIQUE,
            text=thought_text,
            created_at=datetime.now()
        )
        steps.append(critique_step)
    
    # ---- Edges Creation ----
    
    edges = []
    for i in range(len(steps) - 1):
        edge = Edge(
            edge_id=generate_ulid(),
            trace_id=trace.trace_id,
            type=EdgeType.NEXT,
            src=NodeRef(type=NodeRefType.STEP, id=steps[i].step_id),
            dst=NodeRef(type=NodeRefType.STEP, id=steps[i+1].step_id),
            weight=1.0
        )
        edges.append(edge)
    
    # ---- TraceBundle Assembly ----
    
    bundle = TraceBundle(
        trace=trace,
        steps=steps,
        edges=edges,
        artifacts=[],
        patterns=[],
        pattern_instances=[]
    )
    
    return bundle
```

### Stage 4: Validate TraceBundle

```python
def validate_tracebundle(bundle: TraceBundle) -> Tuple[bool, List[str]]:
    """
    Validate bundle consistency before storage.
    Return (is_valid, list_of_errors).
    """
    errors = []
    
    # Check all steps reference correct trace_id
    for step in bundle.steps:
        if step.trace_id != bundle.trace.trace_id:
            errors.append(f"Step {step.step_id} has mismatched trace_id")
    
    # Check all edges reference correct trace_id and valid nodes
    step_ids = {s.step_id for s in bundle.steps}
    artifact_ids = {a.artifact_id for a in bundle.artifacts}
    valid_node_ids = step_ids | artifact_ids
    
    for edge in bundle.edges:
        if edge.trace_id != bundle.trace.trace_id:
            errors.append(f"Edge {edge.edge_id} has mismatched trace_id")
        if edge.src.id not in valid_node_ids:
            errors.append(f"Edge {edge.edge_id}: source node {edge.src.id} not found")
        if edge.dst.id not in valid_node_ids:
            errors.append(f"Edge {edge.edge_id}: destination node {edge.dst.id} not found")
    
    # Check trace has at least one step
    if len(bundle.steps) == 0:
        errors.append(f"Trace {bundle.trace.trace_id} has no steps")
    
    # Check no duplicate step_ids
    if len(step_ids) != len(bundle.steps):
        errors.append("Duplicate step_ids in bundle")
    
    return len(errors) == 0, errors


def handle_bundle_error(bundle: TraceBundle, errors: List[str]) -> None:
    """Log and potentially skip bundle"""
    logger.warning(f"TraceBundle {bundle.trace.trace_id} failed validation:")
    for error in errors:
        logger.warning(f"  - {error}")
```

### Stage 5: Persist to Stores

```python
def persist_bundle(
    bundle: TraceBundle,
    neo4j_session,
    qdrant_client,
    embedding_provider
) -> IngestionResult:
    """
    Atomically persist bundle to Neo4j + Qdrant.
    Neo4j: structure (nodes, edges)
    Qdrant: embeddings + searchable payload
    """
    
    # 1. Store to Neo4j
    try:
        store_tracebundle_neo4j(neo4j_session, bundle)
    except Exception as e:
        logger.error(f"Neo4j storage failed for trace {bundle.trace.trace_id}: {e}")
        return IngestionResult(success=False, error=str(e))
    
    # 2. Generate embeddings for steps (Phase 2: optional)
    # (For now, skip; store structure only)
    
    return IngestionResult(
        success=True,
        trace_id=bundle.trace.trace_id,
        n_steps=len(bundle.steps),
        n_edges=len(bundle.edges)
    )


class IngestionResult(BaseModel):
    success: bool
    trace_id: Optional[str] = None
    n_steps: Optional[int] = None
    n_edges: Optional[int] = None
    error: Optional[str] = None
```

---

## Helper Functions

```python
from ulid import ULID
import hashlib

def generate_ulid() -> str:
    """Generate a ULID (sortable, 26-char base32 string)"""
    return str(ULID())

def generate_trace_id(problem: str, domain: str) -> str:
    """
    Generate deterministic trace_id from problem text + domain.
    Format: base58(SHA256)[:12] + '-' + ULID[:8]
    """
    h = hashlib.sha256(f"{problem}{domain}".encode()).hexdigest()
    base58_prefix = encode_base58(bytes.fromhex(h))[:12]
    return f"{base58_prefix}-{str(ULID())[:8]}"

def encode_base58(data: bytes) -> str:
    """Encode bytes to base58 (Bitcoin alphabet)"""
    alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    num = int.from_bytes(data, 'big')
    encoded = ""
    while num > 0:
        num, remainder = divmod(num, 58)
        encoded = alphabet[remainder] + encoded
    return encoded or "1"
```

---

## End-to-End Ingestion Flow

```python
async def ingest_dataset_batch(req: IngestionRequest) -> IngestionResponse:
    """
    Main entry point: ingest a dataset batch.
    
    Flow:
    1. Validate request
    2. Load HuggingFace dataset
    3. For each record: normalize → validate → persist
    4. Return aggregated response
    """
    
    # Validate
    is_valid, error = validate_ingestion_request(req)
    if not is_valid:
        return IngestionResponse(
            trace_ids=[],
            n_traces=0,
            n_steps=0,
            n_edges=0,
            errors=[error],
            duration_seconds=0,
            status="failed"
        )
    
    start_time = datetime.now()
    trace_ids = []
    total_steps = 0
    total_edges = 0
    errors = []
    
    # Neo4j + Qdrant connections
    neo4j_session = neo4j_driver.session()
    qdrant_cli = QdrantClient(url="http://localhost:6333")
    
    try:
        # Stream records from HuggingFace
        for record in load_hf_records(
            req.dataset_id,
            split=req.dataset_split or "train",
            max_records=req.max_traces
        ):
            try:
                # Normalize
                bundle = normalize_record_to_tracebundle(
                    record,
                    dataset_id=req.dataset_id,
                    split=req.dataset_split or "train",
                    domain_default=req.domain_default
                )
                
                # Validate
                is_valid, bundle_errors = validate_tracebundle(bundle)
                if not is_valid:
                    for err in bundle_errors:
                        errors.append(f"Trace {bundle.trace.trace_id}: {err}")
                    continue
                
                # Persist
                if not req.dry_run:
                    result = persist_bundle(
                        bundle,
                        neo4j_session,
                        qdrant_cli,
                        embedding_provider=None  # Phase 2
                    )
                    if result.success:
                        trace_ids.append(result.trace_id)
                        total_steps += result.n_steps
                        total_edges += result.n_edges
                    else:
                        errors.append(f"Persist failed: {result.error}")
                else:
                    # Dry-run: just count
                    trace_ids.append(bundle.trace.trace_id)
                    total_steps += len(bundle.steps)
                    total_edges += len(bundle.edges)
                    logger.info(f"[DRY RUN] Would ingest {bundle.trace.trace_id}")
                
            except Exception as e:
                logger.exception(f"Failed to process record: {e}")
                errors.append(str(e))
        
        duration = (datetime.now() - start_time).total_seconds()
        
        return IngestionResponse(
            trace_ids=trace_ids,
            n_traces=len(trace_ids),
            n_steps=total_steps,
            n_edges=total_edges,
            errors=errors,
            duration_seconds=duration,
            status="success" if len(errors) == 0 else ("partial" if trace_ids else "failed")
        )
    
    finally:
        neo4j_session.close()
```

---

## Integration Checklist

- [ ] `IngestionRequest` model complete + validated
- [ ] HuggingFace dataset loader (supports streaming)
- [ ] `normalize_record_to_tracebundle()` handles all common HF formats
- [ ] `validate_tracebundle()` catches structural errors
- [ ] Neo4j write path (`store_tracebundle_neo4j()`) implemented and tested
- [ ] Qdrant write path (Phase 2) stubbed
- [ ] Error handling + retry logic for large batches
- [ ] Logging at each stage (load → normalize → validate → persist)
- [ ] Unit tests for each normalizer per dataset format
- [ ] Integration test with sample HuggingFace dataset (10 records)
