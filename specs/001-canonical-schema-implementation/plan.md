# Implementation Plan: Canonical Schema Implementation & Data Ingestion Pipeline

**Branch**: `001-canonical-schema-implementation` | **Date**: 2026-02-12 | **Spec**: [spec.md](spec.md)  
**Constitution Version**: 1.1.0 | **Status**: Phase 0 Research + Phase 1 Design (Complete)

---

## 📚 Reference Documentation

**See Also:**
- [System Architecture](../../docs/architecture/system-architecture.md) — Full system context; 001 is Phase 1 foundation
- [Build Plan](../../docs/architecture/build-plan.md) — Phased roadmap; 001 implements Phase 1 deliverables
- [Capability Requirements](../../docs/architecture/capability-requirements.md) — Capabilities: CR-001 to CR-030 (this feature enables CR-001–CR-010)
- [Canonical Schemas](../../docs/reference/canonical-schemas.md) — Master source for all Pydantic v2 models
- [Storage Mapping](../../docs/reference/storage-mapping.md) — Neo4j + Qdrant mapping (implements this doc)
- [Qdrant Setup](../../docs/reference/qdrant-setup.md) — Exact Qdrant collection/payload schema
- [Problem Archetypes](../../docs/domain/problem-archetypes.md) — Problem types traces encode (parser input validation)
- [FSM Catalogue](../../docs/domain/fsm-catalogue.md) — FSM definitions (trace fsm_id must match catalog)
- [Domain: Problem Archetypes](../../docs/domain/problem-archetypes.md) → Shapes traces will have
- [Domain: Control Pattern Taxonomy](../../docs/domain/control-pattern-taxonomy.md) → Pattern vocabulary (Phase 2 usage)
- [Integration Test Strategy](../../docs/operations/INTEGRATION_TEST_STRATEGY.md) — Test framework for all 001-008 features
- [Authentication & Authorization](../../docs/operations/AUTHENTICATION_SPECIFICATION.md) — Service-to-service auth
- **Phase 2 context:** [MULTI_TENANCY_SPECIFICATION.md](../../docs/operations/MULTI_TENANCY_SPECIFICATION.md), [API_VERSIONING_SPECIFICATION.md](../../docs/operations/API_VERSIONING_SPECIFICATION.md), [CONTROL_FLOW_SPECIFICATION.md](../../docs/operations/CONTROL_FLOW_SPECIFICATION.md)

## Summary

Build foundational data ingestion pipeline that normalizes reasoning traces from HuggingFace datasets (114K and 1.2M scale) into canonical Pydantic schema, stores graph structure in Neo4j, persists embeddings in Qdrant with version tracking and multi-contributor text support. Establishes dual-store architecture (Principle VII) with versioned markdown text storage for future wiki-style collaboration. Achieves ≥200 traces/minute ingestion throughput on single instance with 100% provenance coverage and deduplication support.

---

## Technical Context

**Language/Version**: Python 3.11+ (per Constitution Principle V TDD requirement)

**Primary Dependencies**:

- `datasets >= 2.14.0` (HuggingFace ingestion)
- `pydantic >= 2.0` (canonical schema, per Principle VI, NON-NEGOTIABLE)
- `neo4j-driver >= 5.0` (graph storage)
- `qdrant-client >= 2.7.0` (vector storage)
- `sentence-transformers >= 2.2.2` (embeddings: all-MiniLM-L6-v2 default, configurable override)
- `boto3 >= 1.28.0` (S3 for markdown text storage)
- `python-ulid >= 1.1` (ULID generation for composite IDs)
- `pytest >= 7.4.0`, `pytest-cov` (test harness)
- `ruff`, `mypy` (linting/type-checking, per Principle V)

**Storage**:

- **Neo4j 5.x**: Graph structure (Traces, Steps, Edges, Provenance metadata)
- **Qdrant ≥ 1.7**: Vectors (step embeddings, window embeddings) with version binding and filterable payloads
- **AWS S3 / GCS**: Markdown text versions with audit trail (version_number, content_hash, contributor_id, timestamp, change_note)

**Testing**: `pytest` with integration tests for both 114K and 1.2M datasets (per Constitution Principle V TDD)

**Target Platform**: Linux/macOS server (containerized, serverless-compatible)

**Project Type**: Single Python project (ingestion service as CLI and library)

**Performance Goals**:

- Ingestion throughput ≥ 200 traces/minute on single instance (SC-001: 1K traces < 5 min)
- Neo4j single-trace retrieval < 50ms (SC-003)
- Qdrant top-10 search < 100ms excluding embedding (SC-004)

**Constraints**:

- Storage efficiency: Neo4j nodes < 2KB avg (SC-007), Qdrant payloads < 1KB avg
- Zero data loss on transient failures per-batch (SC-005)
- Schema versioning explicit; migrations tested before deployment

**Scale/Scope**:

- Phase 1: 114K traces (OpenThoughts-114k, MVP validation)
- Phase 1+: 1.2M traces (OpenThoughts3-1.2M, performance benchmark)
- Full text externalized to S3/GCS; Neo4j stores pointers only (lean graph)

---

## Constitution Check

**Status**: ✅ **FULL PASS** — All 10 principles addressed; no violations

| Principle | Status | Evidence |
|-----------|--------|----------|
| **I. Recipe-First** | ✅ | Canonicalization enables recipe extraction; versioning supports pattern library (Phase 3) |
| **II. Verification Before Learning** | ✅ NON-NEG | Schema validation on FR-003; errors logged without data loss FR-009; dedup via content hash FR-002a |
| **III. Federated Quality** | ✅ | Trace versioning (trace_version field) enables quality gates; multi-contributor text FR-013 |
| **IV. Exploitation First** | ✅ | Dual-phase ingestion (114K MVP → 1.2M scale) |
| **V. Test-First Development** | ✅ NON-NEG | Full TDD: unit tests schema, integration tests both datasets, linting (ruff/mypy), pytest |
| **VI. Canonical Schema** | ✅ NON-NEG | Single Pydantic v2; all ingestion normalizes to canonical; versioning tracked (schema_version FR-007) |
| **VII. Dual-Store** | ✅ | Neo4j (graph: Traces/Steps/Edges) + Qdrant (vectors); shared ULID IDs FR-002 |
| **VIII. Provenance** | ✅ | Full metadata FR-007 (source_type, license, sensitivity, ingested_at, pipeline_version); license enforcement |
| **IX. Privacy/Safety** | ✅ | Sensitivity labeling (Sensitivity enum); PII scrubbing deferred Phase 2 (justified: bounded MVP) |
| **X. Continuous Eval** | ✅ | Dedup+versioning FR-002b; benchmark on 114K+1.2M; 8 success criteria (SC-001-SC-008) |

**Technical Stack**:

- ✅ Python 3.11+
- ✅ Pydantic >= 2 (canonical schema)
- ✅ Neo4j (graph storage)
- ✅ Qdrant (vector storage)
- ✅ ULID for IDs (composite: base58[:12](SHA256) + ULID_suffix[:8], per clarification Q3)
- ✅ FSM-aware windows (adaptive depth per FSM, FR-015)
- ✅ Danger signal filters (Qdrant payload, FR-016)

**No violations. All requirements satisfied.**

---

## Project Structure

### Documentation (this feature)

```text
specs/001-canonical-schema-implementation/
├── spec.md                          # ✅ Specification completed
├── plan.md                          # This file (Phase 0→1 output)
├── research.md                      # Phase 0: embedding models, dual-dataset semantics, S3 integration
├── data-model.md                    # Phase 1: Pydantic v2 schemas with version binding
├── quickstart.md                    # Phase 1: setup guide (Neo4j, Qdrant, S3, local dev)
├── contracts/                       # Phase 1: API contracts
│   ├── ingestion-api.md            # Input/output for HF dataset parsing
│   ├── storage-api.md              # Neo4j persistence interface
│   ├── retrieval-api.md            # Qdrant query interface
│   └── text-versioning-api.md      # S3 markdown version management
└── tasks.md                         # Phase 2 output (via /speckit.tasks)
```

### Source Code

```text
src/
├── schema/
│   ├── canonical.py               # Pydantic v2 models: Trace, Step, Edge, Provenance, EmbeddingRef, StepTextVersion
│   ├── validators.py              # Custom validators (composite ID, hash generation, schema_version)
│   └── __init__.py
├── ingestion/
│   ├── hf_loader.py               # HuggingFace dataset loading (114K & 1.2M variants)
│   ├── parser.py                  # Generic trace parser → TraceBundle canonical format
│   ├── batch_processor.py         # Configurable batch ingestion (default 100 traces)
│   └── __init__.py
├── storage/
│   ├── neo4j_client.py            # Neo4j: constraints, transactions, insert/query
│   ├── qdrant_client.py           # Qdrant: collections, payload schema, search
│   ├── s3_text_store.py           # S3: markdown versioning, audit trail, contributor metadata
│   └── __init__.py
├── embedding/
│   ├── model_loader.py            # Configurable embedding model (default all-MiniLM-L6-v2)
│   ├── embedder.py                # Text → vector, version binding to text revision
│   └── __init__.py
├── config.py                      # Environment/CLI config (dataset_url, embedding_model_id, db_urls, etc.)
├── logging_setup.py               # Structured logging (trace_id context on all ops)
└── main.py                        # CLI entry point for ingestion pipeline

tests/
├── unit/
│   ├── test_schema.py             # Pydantic validation, enum coverage
│   ├── test_validators.py         # ID generation, dedup logic, hash collisions
│   ├── test_parsers.py            # HF parsing, edge cases, missing fields
│   └── test_embedding.py          # Embedding generation, version binding
├── integration/
│   ├── test_ingestion_114k.py     # End-to-end: 114K dataset → Neo4j/Qdrant/S3
│   ├── test_ingestion_1_2m.py     # End-to-end: 1.2M dataset (performance target validation)
│   ├── test_neo4j_constraints.py  # Graph constraints, uniqueness, transaction safety
│   ├── test_qdrant_filters.py     # Vector search with domain/FSM/danger filters, windows
│   ├── test_s3_versioning.py      # Markdown versions, audit trail, contributor tracking
│   └── test_deduplication.py      # Duplicate detection, trace_version increments
└── conftest.py                    # pytest fixtures (mock DB, temp S3, test datasets)

README.md                          # Setup, usage, performance validation
requirements.txt                   # Dependencies + versions
pyproject.toml                     # Poetry/setuptools config, pytest, linting (ruff, mypy)
```

---

## Phase 0: Research Findings

### 1. Embedding Model Analysis

**Question**: Which embedding model balances performance, cost, and latency for MVP?

**Decision** (from clarification Q2): **all-MiniLM-L6-v2** (384 dims) as default for development.

- Local execution (no API calls, no rate limits)
- Deterministic outputs (reproducible dedup hashing)
- Fast inference (~100ms for 500 tokens on CPU)
- Sufficient semantic quality for initial pattern retrieval

**Migration Path**: Configurable via `embedding_model_id` runtime parameter to support:

- `text-embedding-3-large` (OpenAI, 3072 dims, best quality, cost trade-off)
- `BAAI/bge-large-en-v1.5` (open-source, 1024 dims, strong performance)
- Custom HuggingFace model ID at deployment time

**Validation**: Unit test embeds 5-10 sample texts, verify shape consistency; integration test validates embedding retrieval on Qdrant window queries.

### 2. Dual-Dataset Semantics

**Question**: How should 114K and 1.2M datasets differ in pipeline setup?

**Decision** (from clarification Q1): Use both iteratively.

- **114K (MVP)**: Fast iteration, schema validation, baseline performance measurement
- **1.2M (Scale)**: Performance benchmark, dedup validation at scale, provenance tracking at volume

**Shared Schema**: Both datasets ingested with identical canonical schema (no variants). Differences:

- Ingestion time targets: 114K < 15min, 1.2M < 5min (per SC-001: ≥200 traces/min)
- Window size validation: FSM-adaptive windows tested on both distributions
- Dedup effectiveness: Measure collision rate, false positive, false negative across scales

**Test Strategy**: Integration test runs both datasets sequentially; success = all SC-001-SC-008 metrics pass on smaller set, then scale metrics validated on 1.2M.

### 3. S3/GCS Text Versioning Architecture

**Question**: How to externalize step text while maintaining audit trail?

**Decision** (from clarification Q4): S3/GCS markdown with version control metadata.

- **Bucket structure**: `s3://grimoire-text-store/trace-{trace_id}/step-{step_id}/v{version_number}.md`
- **Version metadata**: Stored alongside as JSON (`v{version}.meta.json`):

  ```json
  {
    "version_number": 1,
    "content_hash": "sha256:abc123...",
    "contributor_id": "system_ingestion",
    "timestamp": "2026-02-12T14:30:00Z",
    "change_note": "Initial ingestion from OpenThoughts-114k"
  }
  ```

- **Consistency**: Neo4j stores `step.text_key = "s3://grimoire-text-store/trace-{id}/step-{id}/v1"` and `step.text_hash` for validation
- **Embedding Binding**: Qdrant embedding payload includes `text_version_bound: 1`; on text update, flag embedding as stale

**Scaling**: Bucket supports 1.2M traces × 10-1000 steps/trace = 10-100M step text versions; S3 versioning native (automatic rollback via version ID).

---

## Phase 1: Data Model & Contracts

### 1. Canonical Pydantic V2 Schema (data-model.md)

**Core Entities**:

#### Trace

```python
class Trace(BaseModel):
    trace_id: str                           # Composite: base58(SHA256(problem+domain+tags))[:12] + "-" + ULID[:8]
    title: str
    domain: DomainTag                       # Enum: GENERAL, SOFTWARE, ML, DATA, SECURITY, PRODUCT, LEGAL, HEALTH, FINANCE
    tags: List[str] = []
    problem: Optional[str] = None           # Initial problem statement (truncated if > 5KB, full stored in S3)
    created_at: datetime
    updated_at: datetime
    status: str = "ingested"                # ingested, validated, processed, failed
    trace_version: int = 1                  # Integer version; increments when same problem re-solved

    n_steps: int                            # Step count for quick access
    outcome: Optional[Dict[str, Any]] = None  # Result summary (JSON serializable)

    # Provenance (flattened from Provenance model)
    provenance_sources: List[SourceRef]
    provenance_license: LicenseType
    provenance_license_url: Optional[HttpUrl] = None
    provenance_attribution: Optional[str] = None
    provenance_sensitivity: Sensitivity = Sensitivity.PUBLIC
    provenance_ingested_at: datetime
    provenance_pipeline_version: str        # e.g., "0.1.0-alpha"
    provenance_schema_version: str = "v1"   # Increments on breaking changes

    # Danger scores (optional, computed later in Phase 2)
    danger_ambiguity: float = 0.0
    danger_adversarial: float = 0.0
    danger_irreversibility: float = 0.0
    danger_institutional: float = 0.0

    # Deduplication
    content_hash: str                       # SHA256(problem+domain+tags) base58-encoded
    is_duplicate: bool = False
    duplicate_of: Optional[str] = None      # trace_id of canonical version
```

#### Step

```python
class Step(BaseModel):
    step_id: str                            # ULID (random, ensures uniqueness within trace)
    trace_id: str                           # Foreign key to Trace
    index: int                              # Sequence within trace (0-indexed)
    created_at: datetime
    actor: Optional[str] = None             # e.g., "user", "assistant", "tool"
    role: StepRole                          # Enum: GOAL, QUESTION, PLAN, ACTION, OBSERVATION, CRITIQUE, DECISION, etc.
    fsm_id: Optional[str] = None            # Assigned FSM type (computed Phase 2)
    fsm_state: Optional[FSMState] = None    # Current state in FSM (S0-S9)

    # Text storage (externalized)
    text_key: str                           # S3 URI: s3://bucket/trace-{id}/step-{id}/v{version}.md
    text_preview: str                       # First 500 chars (Neo4j stores for quick access)
    text_hash: str                          # SHA256 of full text (validation)
    text_version: int = 1                   # Current text version in S3

    # Embeddings
    embedding_id: Optional[str] = None      # Qdrant point ID
    embedding_version: int = 1              # Version of text that was embedded
    embedding_stale: bool = False           # Flag if text updated after embedding

    # Tool calls (optional)
    tool_name: Optional[ToolName] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
```

#### StepTextVersion

```python
class StepTextVersion(BaseModel):
    """Stored in S3 as markdown + metadata JSON"""
    version_number: int
    content_hash: str                       # SHA256 of markdown content
    contributor_id: str                     # "system_ingestion", LLM ID, or user email
    timestamp: datetime
    change_note: str                        # Why this version exists
    markdown_content: str                   # Full step text in markdown format
    language_hint: Optional[str] = None     # e.g., "python", "sql", "english"
```

#### Edge

```python
class Edge(BaseModel):
    edge_id: str                            # ULID
    type: str                               # "NEXT" (sequence), "SUPPORTS", "REFUTES", "DEPENDS_ON", etc.
    src_id: str                             # step_id or artifact_id
    dst_id: str                             # step_id or artifact_id
    weight: float = 1.0                     # Confidence/importance [0.0, 1.0]
```

#### EmbeddingRef

```python
class EmbeddingRef(BaseModel):
    """Metadata for Qdrant point; embedding vectors stored separately"""
    embedding_id: str                       # ULID (Qdrant point_id)
    model: str                              # "all-MiniLM-L6-v2" or other ID
    dimensions: int                         # 384, 1024, 3072, etc.
    content_hash: str                       # Hash of embedded text
    text_version_bound: int                 # Step text version that was embedded (detect staleness)
    storage_key: str                        # S3/Qdrant pointer
```

#### StepWindow (computed, stored in Qdrant)

```python
class StepWindow(BaseModel):
    """Variable-length context group, stored in Qdrant step_windows collection"""
    window_id: str                          # ULID
    trace_id: str
    window_start_index: int                 # Index of first step
    window_size: int                        # Number of steps (2-6 typically)
    step_ids: List[str]                     # Sequence of step_ids
    fsm_id: Optional[str]                   # FSM type (for semantic alignment)
    concatenated_text: str                  # All step texts concatenated (markdown preserved)
    concatenated_hash: str                  # SHA256 of concatenated text

    # Payload metadata (filterable in Qdrant)
    domain: DomainTag
    danger_ambiguity: float = 0.0
    danger_adversarial: float = 0.0
    danger_irreversibility: float = 0.0
    danger_institutional: float = 0.0
```

**Versioning Strategy**:

- `schema_version: "v1"` on all Traces (increments on breaking schema changes)
- `trace_version: "1.0"` per trace (increments when trace re-ingested with different approach)
- `text_version: int` on Steps (increments on text revision, triggers embedding staleness flag)
- All versions explicit in provenance; migration paths tested before deployment

### 2. Storage API Contracts (contracts/)

#### **ingestion-api.md**: HF Dataset → Neo4j/Qdrant

```text
Input: HuggingFace dataset ID (e.g., "open-thoughts/OpenThoughts-114k")
Output: TraceBundle
- Trace (1 per dataset record / conversation)
- Step[] (N per conversation, sequence order)
- Edge[] (NEXT edges chaining steps)
Actions:
1. Parse dataset record → Trace + Step[] (FR-001)
2. Generate composite IDs (FR-002a)
3. Deduplicate (FR-002b): check content_hash, skip if exists
4. Validate schema (FR-003): Pydantic raises ValidationError
5. Batch insert to Neo4j (FR-004, FR-005): upsert safe
6. Generate embeddings (FR-006a): configured model
7. Insert to Qdrant (FR-006): steps collection + payloads (FR-016)
8. Store text to S3 (FR-013): markdown v1, audit trail
9. Log provenance (FR-007): all metadata stored
```

#### **storage-api.md**: Neo4j Persistence

```text
Constraints:
- UNIQUE (trace_id)
- UNIQUE (step_id)
- Foreign key: Step.trace_id → Trace.trace_id
- Index on: (domain), (step.fsm_id, fsm_state), (role)

Transactions:
- Batch insert Trace nodes with properties
- Batch insert Step nodes
- Batch insert NEXT edges with index validation
- Rollback on any error (FR-005)

Queries:
- Retrieve Trace by trace_id (↓ FR-004)
- Retrieve all Steps for trace_id in index order
- Traverse NEXT edges (↓ FR-005)
- Query by domain, FSM type (↓ FR-015, FR-016)
```

#### **retrieval-api.md**: Qdrant Search

```text
Collections:
- steps: vectors (384 dims default) + payload {trace_id, step_id, index, role, domain, danger_*}
- step_windows: vectors + payload {trace_id, window_size, fsm_id, danger_*, step_ids[]}
- patterns: (Phase 3) extracted meta-thought vectors

Queries:
- Semantic search (top-K): "similar steps to: [query text]"
- Filtered search: "design decision steps where domain='software' AND danger_ambiguity > 0.7"
- Window search: "find context windows for this step_id"

Latency Target: top-10 < 100ms (SC-004)
```

#### **text-versioning-api.md**: S3 Markdown Management

```text
PUT /trace/{trace_id}/step/{step_id}/v{version}.md
- Store markdown content
- Store metadata JSON (contributor_id, timestamp, change_note)

GET /trace/{trace_id}/step/{step_id}/latest
- Return current version + metadata

GET /trace/{trace_id}/step/{step_id}/v{version}
- Return specific version (audit trail)

LIST /trace/{trace_id}/step/{step_id}
- All versions with timestamps
```

---

## Phase 1 Deliverables

✅ **data-model.md**: Complete Pydantic v2 schema with all versions, constraints, relationships  
✅ **contracts/**: 4 API specifications (ingestion, storage, retrieval, text-versioning)  
✅ **quickstart.md**: Setup guide (Neo4j, Qdrant, S3, Python env, run first ingestion)

---

## Next Steps

**→ /speckit.tasks**: Convert this plan into 15-25 actionable tasks with dependencies, parallelization opportunities, and acceptance criteria.

**Estimated task breakdown**:

- Schema + validation: 2-3 tasks
- Ingestion + parsing: 3-4 tasks
- Neo4j persistence: 2-3 tasks
- Qdrant storage: 2-3 tasks
- S3 text versioning: 2 tasks
- Embedding pipeline: 2-3 tasks
- Testing (unit + integration): 5-6 tasks
- Total: ~20-24 tasks, estimated 40-60 implementation hours
