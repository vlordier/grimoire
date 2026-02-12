# Research: Canonical Schema Implementation & Data Ingestion Pipeline

**Date**: 2026-02-12 | **Phase**: 0 (Research & Clarification)  
**Status**: All NEEDS CLARIFICATION items resolved ✅

---

## Research Questions Resolved

### RQ-1: Optimal Embedding Model Selection

**Question**: Which embedding model balances MVP speed, cost, and future scalability?

**Investigation**:
- Evaluated 5 candidates: OpenAI text-embedding-3-large, BAAI/bge-large, sentence-transformers/all-MiniLM-L6-v2, local Hugging Face models, deferred
- Cost analysis: OpenAI ~$0.02/1K tokens (114K traces × avg 200 tokens/step = $456+ per full ingest); local models free
- Latency: all-MiniLM-L6-v2 ~100ms per step on CPU; BAAI/bge-large ~150ms; OpenAI 200-500ms (API round-trip)
- Semantic quality: all-MiniLM sufficient for initial pattern retrieval (384 dims); upgradeable without schema change

**Decision** (clarification Q2): **Configurable embeddings, default to all-MiniLM-L6-v2 (384 dims)**
- Implement as runtime parameter `embedding_model_id` in config
- Default for MVP: `all-MiniLM-L6-v2` (local, deterministic, fast)
- Override path: OpenAI, BAAI, or other HF model by changing config before ingestion
- No code changes needed for model swap; only config update

**Rationale**: Maximizes iteration speed during development; production can upgrade to larger model after validation

**Test Plan**:
- Unit test: Load default model, verify output shape (384,)
- Unit test: Load OpenAI model (mock), verify config override works
- Integration test: Ingest 100 traces with both models; compare latency + quality (manual spot-check)

---

### RQ-2: Dual-Dataset Ingestion Strategy

**Question**: How should 114K and 1.2M datasets be handled for MVP + scaling validation?

**Investigation**:
- OpenThoughts-114k: 114K samples, well-documented, Apache 2.0 license, ~5GB download
- OpenThoughts3-1.2M: 1.2M samples, 16 annotations/question, ~28GB download, same license
- Ingestion speed targets: 200 traces/min = ~333 datasets/hr on single instance

**Decision** (clarification Q1): **Use both iteratively**
- Phase 1a: Ingest 114K dataset end-to-end (MVP validation): target < 15 min
- Phase 1b: Ingest 1.2M dataset (scale validation): target < 300 min (5 hr) to validate 200 traces/min throughput meets SC-001

**Dataset-Specific Considerations**:
- Both use identical canonical schema (no variants)
- Window semantics identical (FSM-adaptive depth)
- Test strategy: Sequential runs (114K then 1.2M) to catch scale-related bugs (memory leaks, index bloat, dedup collisions)

**Deduplication at Scale**:
- 114K: Expect ~95% unique (5% duplicates within dataset due to similar problems)
- 1.2M: Expect ~85-90% unique across full dataset; composite ID strategy (SHA256 base + ULID suffix) enables efficient lookup

**Validation**:
- SC-001: 1,000 traces ingest < 5 min ✓ (if successful, proves ≥200 traces/min throughput)
- SC-001 extended: 1.2M ingest validates sustained 200+ traces/min throughput

---

### RQ-3: Composite ID Strategy with Versioning

**Question**: How to generate IDs that enable deduplication AND versioning AND uniqueness?

**Investigation**:
- Option 1: Fully deterministic (trace_id = SHA256(problem+domain)) → idempotent but reveals data in IDs
- Option 2: Fully random (trace_id = ULID) → unique but no dedup capability
- Option 3: Composite (deterministic base + random suffix) → keeps benefits of both
- Option 4: Deterministic hash + version counter → simple but requires state management

**Decision** (clarification Q3): **Composite approach with trace_version field**

```
trace_id = base58(SHA256(problem + domain + tags))[:12] + "-" + ULID_suffix[:8]
example: "3jkd7fh92k5-a7x3p2n9"
         |____________|  |_____|
         deterministic   random unique suffix
```

**How it enables both dedup + versioning**:
- Same problem (problem+domain+tags match) → same deterministic base → "3jkd7fh92k5"
- Different approaches → different ULID suffix → different trace_id → "3jkd7fh92k5-a7x3p2n9" vs "3jkd7fh92k5-b4k9m1x7"
- Implementation: Check if deterministic base exists in Neo4j before insert; if yes, compare full trace_id
  - If full trace_id matches: skip (exact duplicate)
  - If base matches, different suffix: increment trace_version on original, store as separate trace with trace_version="1.1"

**Deduplication Logic**:
```python
def get_or_create_trace(problem, domain, tags, new_trace_data):
    content_hash = base58(SHA256(f"{problem}+{domain}+{tags}"))[:12]
    existing = neo4j.query(f"MATCH (t:Trace) WHERE t.content_hash = '{content_hash}'")
    
    if existing:
        if existing.trace_id == compute_trace_id(problem, domain, tags):
            return DUPLICATE, existing.trace_id  # Exact match, skip
        else:
            # Same problem, different approach (new suffix)
            existing.is_duplicate = False
            new_trace_data.trace_version = f"{existing.trace_version_major}.{int(existing.trace_version_minor)+1}"
            return NEW_VERSION, create_trace(new_trace_data)
    else:
        # First time seeing this problem signature
        new_trace_data.trace_version = "1.0"
        return NEW, create_trace(new_trace_data)
```

**Validation**:
- Unit test: Generate 10 traces with same (problem, domain), verify same base, different suffixes
- Unit test: Dedup logic detects exact duplicates, skips second copy
- Integration test: Ingest 114K, then re-ingest 500 records; verify duplicates marked and skipped (FR-002b)

---

### RQ-4: Externalized Text Storage with Versioning

**Question**: How to store massive step text while maintaining editability and audit trail?

**Investigation**:
- Storing all text in Neo4j: bloats graph, reduces query speed, locks text to graph schema
- Externalizing to S3: decouples text lifecycle from graph, enables versioning and multi-contributor edits
- Markdown format: human-readable, supports code blocks, compatible with LLM processing
- Versioning: GitHub-style (v1, v2, v3...) with metadata for each version

**Decision** (clarification Q4): **Externalize to S3/GCS as Markdown + version metadata**

**Storage Layout**:
```
s3://grimoire-text-store/
├── trace-{trace_id}/
│   └── step-{step_id}/
│       ├── v1.md                    # Initial ingestion markdown
│       ├── v1.meta.json             # Version metadata
│       ├── v2.md                    # After LLM revision
│       ├── v2.meta.json
│       └── ...
```

**Metadata Schema** (v{n}.meta.json):
```json
{
  "version_number": 1,
  "content_hash": "sha256:abc123def456...",
  "contributor_id": "system_ingestion",
  "timestamp": "2026-02-12T14:30:00Z",
  "change_note": "Initial ingestion from OpenThoughts-114k dataset",
  "language_hint": "english",
  "text_size_bytes": 2048
}
```

**Neo4j Pointers**:
- `step.text_key`: "s3://grimoire-text-store/trace-{id}/step-{id}/v1"
- `step.text_preview`: first 500 chars (quick access without S3 roundtrip)
- `step.text_hash`: SHA256 (validation on retrieval)
- `step.text_version`: 1 (current version number)

**Embedding Binding**:
- Qdrant payload includes `text_version_bound: 1`
- If step text > v1 created: mark Qdrant embedding as stale (`embedding_stale: true`)
- On query: check staleness; if stale, flag for re-embedding in background job

**Future Extension** (Phase 3): Wiki-style interface
- Humans + LLMs can create new versions (v2, v3, ...)
- Each version has contributor attribution + timestamp
- Queries can time-travel: "show me this step as it looked on 2026-03-01"

**Validation**:
- Unit test: Store markdown, retrieve, verify hash match
- Integration test: Ingest 100 steps, verify text in S3, Neo4j pointers correct
- Integration test: Create v2 of step text, verify metadata + embedding staleness flag

---

### RQ-5: FSM-Adaptive Window Creation

**Question**: How to create context windows that align with reasoning semantics?

**Investigation**:
- Fixed k=5 windows: simple, uniform, but misaligned with FSM transitions
- Dynamic FSM-aligned windows: semantic but complex (requires FSM assignment first)
- Hybrid: FSM-aware depths, overlapping (stride=1) for pattern retrieval

**Decision** (clarification Q5): **FSM-adaptive depth with overlapping windows**

**Window Sizes by FSM Type** (from [FSM Catalogue](../../docs/domain/fsm-catalogue.md)):
- Hierarchical FSMs (Design/Decide, Clarify/Frame): depth 4-6 steps (captures full decision cycle)
- Diagnostic FSMs (Diagnose/Fix): depth 2-3 steps (tight hypothesis-test loops)
- Optimization loops: depth 5 (baseline → intervention → result)
- Conflict resolution: depth 3-4 (rounds of negotiation)

**Example Window Extraction**:
```
Trace steps: [S0, S1, S2, S3, S4, S5, S6, S7, S8, S9]
FSM states:  [I,  C,  M,  P,  E,  Ob, Ev, D,  H,  Cl] (intake, clarify, model, plan, execute, observe, evaluate, decide, harden, close)

FSM Assignment: DIAGNOSE_FIX (hierarchical, depth=6)
Windows (stride=1):
- Window 1: [S0:I, S1:C, S2:M, S3:P, S4:E, S5:Ob]
- Window 2: [S1:C, S2:M, S3:P, S4:E, S5:Ob, S6:Ev]
- Window 3: [S2:M, S3:P, S4:E, S5:Ob, S6:Ev, S7:D]
- Window 4: [S3:P, S4:E, S5:Ob, S6:Ev, S7:D, S8:H]
- Window 5: [S4:E, S5:Ob, S6:Ev, S7:D, S8:H, S9:Cl]
```

**Qdrant Payload for Each Window**:
```python
{
  "trace_id": "3jkd7fh92k5-a7x3p2n9",
  "window_start_index": 0,
  "window_size": 6,
  "step_ids": ["step001", "step002", "step003", "step004", "step005", "step006"],
  "fsm_id": "fsm_clarify_frame",
  "domain": "software",
  "danger_ambiguity": 0.3,
  "danger_adversarial": 0.0,
  "danger_irreversibility": 0.8,
  "danger_institutional": 0.0
}
```

**Query Examples**:
- "Find windows with ambiguity > 0.7 in software domain" (filter by payload)
- "Find similar design windows" (vector search on design FSM payload filter)

**Validation**:
- Unit test: Generate FSM-adaptive windows for mock traces; verify depth per FSM type
- Integration test: Ingest 100 traces, compute windows, verify Qdrant payloads correct
- Integration test: Query Qdrant by FSM type + danger; verify results are semantically grouped

---

## Investigation Artifacts

### Benchmark Dataset Specifications

| Dataset | Size | License | Splits | Quality | Use Case |
|---------|------|---------|--------|---------|----------|
| OpenThoughts-114k | 114K | Apache 2.0 | train/eval | Coarse | MVP validation speed |
| OpenThoughts3-1.2M | 1.2M | Apache 2.0 | train | High (16 annot/Q) | Scale validation |

### Performance Baseline (Expected)

| Metric | Target | Method |
|--------|--------|--------|
| Ingestion throughput | ≥200 traces/min | 114K in <15min; 1.2M in <300min |
| Dedup accuracy | 100% recall | All duplicates detected + marked |
| Embedding latency | <100ms top-10 | Qdrant local search |
| Neo4j query latency | <50ms | Single-trace full retrieval (7 hops) |
| Storage efficiency | <2KB/node Neo4j; <1KB/payload Qdrant | Compression + pointer strategy |

---

## Resolved Clarifications Summary

✅ **Q1**: Dataset source → Dual-phase (114K MVP + 1.2M scale)  
✅ **Q2**: Embedding model → Configurable (default: all-MiniLM-L6-v2)  
✅ **Q3**: ID generation → Composite (deterministic base + ULID suffix) + trace_version  
✅ **Q4**: Text storage → S3 markdown + version audit trail + wiki-style edit foundation  
✅ **Q5**: Window creation → FSM-adaptive depth + overlapping windows  

**All research questions resolved. Ready for Phase 1 design & implementation planning.**
