# Ingestion API Contract

**Component**: HuggingFace Dataset Parser & Ingestion Pipeline  
**Input**: HuggingFace dataset ID (e.g., "open-thoughts/OpenThoughts-114k")  
**Output**: TraceBundle (Trace + Step[] + Edge[]) streamed to Neo4j / Qdrant / S3

---

## Input Specification

```python
class IngestionRequest:
    dataset_id: str                    # e.g., "open-thoughts/OpenThoughts-114k"
    dataset_split: str = "train"       # "train", "validation", "test"
    max_traces: Optional[int] = None   # Limit ingestion (None = all)
    batch_size: int = 100              # Records per batch (configurable)
    embedding_model_id: str = "all-MiniLM-L6-v2"  # Embedding model override
    dry_run: bool = False              # Validate without storing
```

---

## Processing Pipeline

### Stage 1: Parse HuggingFace Record → Canonical Trace

**Input**: Single HF dataset record (varies by dataset)

**For OpenThoughts datasets**:
```python
hf_record = {
    "problem": "Solve Q: ...",                      # Problem statement
    "messages": [
        {"role": "user", "content": "..."},
        {"role": "assistant", "content": "..."}
    ],
    "thought_process": "Let me think...",          # Extended reasoning
    "answer": "The answer is...",                   # Final response
}

# Transform to canonical:
trace = Trace(
    trace_id = generate_trace_id(problem, domain="general"),      # FR-002a
    title = problem[:100],
    domain = infer_domain(problem, messages),   # Heuristic or ML classifier
    problem = problem,
    provenance_sources = [SourceRef(
        source_type = "huggingface",
        source_id = dataset_id,
        record_id = hf_record.get("id")
    )],
    provenance_license = "apache-2.0",
    provenance_sensitivity = "public",
    provenance_ingested_at = datetime.now(),
    provenance_pipeline_version = "0.1.0-alpha",
    provenance_schema_version = "v1",
    n_steps = len(messages) + 1,  # user + assistant exchanges + thought process
    created_at = datetime.now()
)
```

### Stage 2: Extract Steps from Messages

**Logic**:
- Each message (user/assistant) → 1 Step
- Thought process field (if present) → 1 additional Step (role=CRITIQUE)

```python
steps = []

# Step 0: Initial problem (from traces.problem or first user message)
steps.append(Step(
    step_id = generate_ulid(),
    trace_id = trace.trace_id,
    index = 0,
    role = StepRole.GOAL,
    actor = "user",
    text_key = store_text_s3(problem, version=1),  # FR-013
    text_preview = problem[:500],
    text_hash = sha256(problem),
    created_at = datetime.now()
))

# Steps 1..N: Message exchanges
for i, msg in enumerate(messages):
    role_map = {"user": StepRole.QUESTION, "assistant": StepRole.OBSERVATION}
    step = Step(
        step_id = generate_ulid(),
        trace_id = trace.trace_id,
        index = i + 1,
        role = role_map.get(msg["role"], StepRole.OTHER),
        actor = msg["role"],
        text_key = store_text_s3(msg["content"], version=1),
        text_preview = msg["content"][:500],
        text_hash = sha256(msg["content"]),
        created_at = datetime.now()
    )
    steps.append(step)

# Optional: Thought process as CRITIQUE step
if "thought_process" in hf_record:
    steps.append(Step(
        step_id = generate_ulid(),
        trace_id = trace.trace_id,
        index = len(steps),
        role = StepRole.CRITIQUE,
        actor = "system",
        text_key = store_text_s3(hf_record["thought_process"], version=1),
        text_preview = hf_record["thought_process"][:500],
        text_hash = sha256(hf_record["thought_process"]),
        created_at = datetime.now()
    ))
```

### Stage 3: Create NEXT Edges

**Logic**: Link steps in sequence order

```python
edges = []
for i in range(len(steps) - 1):
    edges.append(Edge(
        edge_id = generate_ulid(),
        type = "NEXT",
        src_id = steps[i].step_id,
        dst_id = steps[i+1].step_id,
        weight = 1.0
    ))
```

---

## Output: TraceBundle

```python
class TraceBundle:
    """Atomic unit for storage; if any component fails validation, entire bundle rejected"""
    trace: Trace
    steps: List[Step]
    edges: List[Edge]
```

---

## Quality Checks (FR-001 through FR-003)

### Validation Stage (before storage)

```python
def validate_tracebundle(bundle: TraceBundle) -> Tuple[bool, List[str]]:
    errors = []
    
    # 1. Schema validation (FR-003: Pydantic)
    try:
        Trace.model_validate(bundle.trace)
    except ValidationError as e:
        errors.append(f"Trace validation failed: {e}")
    
    for i, step in enumerate(bundle.steps):
        try:
            Step.model_validate(step)
        except ValidationError as e:
            errors.append(f"Step {i} validation failed: {e}")
    
    # 2. Structural validation
    if len(bundle.steps) == 0:
        errors.append("TraceBundle has no steps")
    
    if len(bundle.edges) != len(bundle.steps) - 1:
        errors.append(f"Expected {len(bundle.steps)-1} NEXT edges, got {len(bundle.edges)}")
    
    # 3. ID consistency
    for edge in bundle.edges:
        if edge.type != "NEXT":
            errors.append(f"Non-NEXT edge {edge.type} not supported in ingest")
        
        # Verify edge.src_id references a step
        if not any(s.step_id == edge.src_id for s in bundle.steps):
            errors.append(f"Edge references missing step {edge.src_id}")
    
    # 4. Domain inference
    if bundle.trace.domain == DomainTag.GENERAL:
        # Log warning; not an error
        print(f"Warning: Trace domain inferred as GENERAL (heuristic may be improved)")
    
    return len(errors) == 0, errors
```

---

## Storage Actions

### 1. Deduplication (FR-002b)

```python
# Check if trace already exists
existing = neo4j.query(f"""
    MATCH (t:Trace) 
    WHERE t.content_hash = '{bundle.trace.content_hash}'
    RETURN t
""")

if existing:
    if existing.trace_id == bundle.trace.trace_id:
        # Exact duplicate → skip
        return DUPLICATE, existing.trace_id
    else:
        # Same problem, different approach → increment version
        bundle.trace.trace_version = increment_version(existing.trace_version)

# No duplicate → proceed to storage
```

### 2. Persist to Neo4j (FR-004, FR-005)

```python
# Transaction: all-or-nothing
with neo4j.transaction() as tx:
    # Insert Trace node
    tx.run("""
        CREATE (t:Trace) SET t = $props
    """, props=bundle.trace.dict())
    
    # Insert Step nodes + properties
    for step in bundle.steps:
        tx.run("""
            CREATE (s:Step) SET s = $props
        """, props=step.dict())
    
    # Insert NEXT edges
    for edge in bundle.edges:
        tx.run("""
            MATCH (src:Step {step_id: $src_id}), (dst:Step {step_id: $dst_id})
            CREATE (src)-[e:NEXT {weight: $weight}]->(dst) SET e = $props
        """, src_id=edge.src_id, dst_id=edge.dst_id, 
             weight=edge.weight, props=edge.dict())
    
    # If any error: rollback all
    tx.commit()
```

### 3. Generate Embeddings (FR-006, FR-006a)

```python
embedding_model = load_embedding_model(embedding_model_id)  # Default: all-MiniLM-L6-v2

for step in bundle.steps:
    # Retrieve full text from S3
    full_text = s3.get_object(step.text_key.replace("v{}\n", f"v{step.text_version}"))
    
    # Embed
    vector = embedding_model.encode(full_text)
    
    # Store in Qdrant
    qdrant.upsert(
        collection_name="steps",
        points=[Point(
            id=step.step_id,
            vector=vector.tolist(),
            payload={
                "trace_id": step.trace_id,
                "step_id": step.step_id,
                "index": step.index,
                "role": step.role.value,
                "domain": bundle.trace.domain.value,
                "danger_ambiguity": 0.0,  # Computed in Phase 2
                "danger_adversarial": 0.0,
                "danger_irreversibility": 0.0,
                "danger_institutional": 0.0,
                "text_version_bound": step.text_version
            }
        )]
    )
    
    # Update step.embedding_id in Neo4j
    neo4j.run("""
        MATCH (s:Step {step_id: $step_id})
        SET s.embedding_id = $embedding_id, s.embedding_version = $version
    """, step_id=step.step_id, embedding_id=step.step_id, 
         version=step.text_version)
```

### 4. Store Text to S3 (FR-013)

```python
# Text already stored during Step creation, but create version audit trail
for step in bundle.steps:
    full_text = retrieve_from_s3_temp(step.text_key)  # Already uploaded
    
    # Write metadata
    s3.put_object(
        Key=f"{step.text_key.replace('.md', '.meta.json')}",
        Body=json.dumps({
            "version_number": 1,
            "content_hash": step.text_hash,
            "contributor_id": "system_ingestion",
            "timestamp": datetime.now().isoformat(),
            "change_note": f"Initial ingestion from {bundle.trace.provenance_sources[0].source_id}",
            "language_hint": "english",
            "text_size_bytes": len(full_text)
        })
    )
```

### 5. Log Provenance (FR-007)

```python
# All provenance fields already set in Trace during parsing
# Validation: ensure all required fields present
assert bundle.trace.provenance_sources is not None
assert bundle.trace.provenance_license is not None
assert bundle.trace.provenance_ingested_at is not None
assert bundle.trace.provenance_pipeline_version is not None

# Log to structured logger
logger.info(f"Ingested trace {bundle.trace.trace_id}", extra={
    "trace_id": bundle.trace.trace_id,
    "n_steps": len(bundle.steps),
    "source": bundle.trace.provenance_sources[0].source_type,
    "license": bundle.trace.provenance_license,
    "domain": bundle.trace.domain,
    "created_at": bundle.trace.created_at,
    "pipeline_version": bundle.trace.provenance_pipeline_version
})
```

---

## Error Handling (FR-009)

```python
def ingest_batch(records: List[Dict]) -> IngestResult:
    """Ingest batch with error logging, no crash on validation failure"""
    result = IngestResult(total=len(records), success=0, failed=0, failed_records=[])
    
    for i, record in enumerate(records):
        try:
            # Parse HF record → TraceBundle
            bundle = parse_record_to_bundle(record)
            
            # Validate
            is_valid, errors = validate_tracebundle(bundle)
            if not is_valid:
                result.failed += 1
                result.failed_records.append({
                    "index": i,
                    "record_id": record.get("id"),
                    "errors": errors
                })
                continue
            
            # Store
            store_tracebundle(bundle)
            result.success += 1
            
        except Exception as e:
            result.failed += 1
            result.failed_records.append({
                "index": i,
                "record_id": record.get("id"),
                "errors": [str(e)]
            })
            logger.error(f"Ingestion error record {i}: {e}", exc_info=True)
    
    logger.info(f"Batch result: {result.success}/{result.total} succeeded, {result.failed} failed")
    return result
```

---

## Transactional Semantics (FR-005)

- **Per-batch atomicity**: If batch ingestion fails at any point (validation, Neo4j, Qdrant, S3), entire batch reported as failed but previous batches remain committed
- **No partial records**: A single record either fully ingests (Trace + Steps + Edges + Embeddings + S3) or not at all
- **Retry logic**: Failed batches logged; can be retried via idempotent re-ingestion (dedup handles re-runs)

---

## Success Metrics

| Criterion | Target | Validation |
|-----------|--------|-----------|
| SR-001: Ingest 1K traces | < 5 min | 114K dataset in < 15 min |
| SR-002: 100% validation | No false negatives | Malformed data rejected with clear error |
| SR-007: Storage efficiency | < 1KB Qdrant payload | Verify payload size in collection |
