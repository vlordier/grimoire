# Feature Specification: Canonical Schema Implementation & Data Ingestion Pipeline

**Feature Branch**: `001-canonical-schema-implementation`  
**Created**: 2026-02-12  
**Status**: Draft  
**Input**: Implementation Plan Phase 1 + Constitution Principles VI, VII, VIII

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ingest HuggingFace Dataset (Priority: P1) 🎯 MVP

A data scientist wants to ingest reasoning traces from a HuggingFace dataset into Grimoire's canonical format so they can be stored, queried, and used for pattern mining.

**Why this priority**: This is the foundational capability. Without data ingestion, no other features can function. All downstream features (routing, pattern mining, retrieval) depend on canonicalized data.

**Independent Test**: Can ingest a small HF dataset (e.g., 100 traces from `open-thoughts/OpenThoughts-114k`) and verify all traces are stored in Neo4j with correct schema and provenance metadata.

**Acceptance Scenarios**:

1. **Given** a HuggingFace dataset URL, **When** the ingestion pipeline runs, **Then** all traces are normalized to canonical schema (Trace, Step, Edge) with valid ULID IDs
2. **Given** ingested traces, **When** querying Neo4j, **Then** all Steps have NEXT edges and belong to exactly one Trace
3. **Given** ingested traces, **When** checking provenance, **Then** all Traces have source_type="huggingface", source_id, license, and ingestion timestamp

---

### User Story 2 - Store Graph Structure in Neo4j (Priority: P1) 🎯 MVP

A developer wants the reasoning graph (Traces, Steps, Edges) persisted in Neo4j so they can traverse sequences, query relationships, and validate structural constraints.

**Why this priority**: Graph storage enables procedural traversal and FSM validation. This is core to Constitution Principle VII (Dual-Store Architecture).

**Independent Test**: After ingestion, can query Neo4j to find all Steps in a Trace, traverse NEXT edges in sequence order, and verify no orphaned Steps exist.

**Acceptance Scenarios**:

1. **Given** a Trace in Neo4j, **When** querying `(:Trace)-[:HAS_STEP]->(:Step)`, **Then** all Steps for that Trace are returned
2. **Given** Steps in sequence, **When** traversing `(:Step)-[:NEXT]->(:Step)`, **Then** edges follow index order without gaps
3. **Given** Neo4j constraints, **When** attempting to insert duplicate step_id, **Then** insertion fails with uniqueness violation

---

### User Story 3 - Store Embeddings in Qdrant (Priority: P1) 🎯 MVP

A developer wants step embeddings stored in Qdrant with filterable metadata so semantic search can retrieve similar reasoning steps filtered by FSM, domain, or danger level.

**Why this priority**: Vector retrieval is the recall mechanism for pattern matching. This completes the dual-store architecture (Constitution Principle VII).

**Independent Test**: After ingestion, can search Qdrant for semantically similar steps and filter results by domain or trace_id.

**Acceptance Scenarios**:

1. **Given** ingested Steps, **When** querying Qdrant for similar steps, **Then** top-K results are semantically relevant with distances < threshold
2. **Given** Steps with metadata, **When** filtering by `domain="software"`, **Then** only software domain steps are returned
3. **Given** a step_id, **When** retrieving from Qdrant, **Then** payload contains trace_id, index, role, and text preview

---

### User Story 4 - Validate Schema Compliance (Priority: P2)

A data engineer wants all ingested data validated against the canonical Pydantic schema so schema violations are caught early and logged before storage.

**Why this priority**: Schema validation prevents garbage data from entering the system (Constitution Principle VI).

**Independent Test**: Attempt to ingest malformed data and verify validation errors are logged without crashing the pipeline.

**Acceptance Scenarios**:

1. **Given** a record missing required fields (e.g., no step_id), **When** validation runs, **Then** record is rejected with clear error message
2. **Given** a record with invalid enum value (e.g., role="invalid"), **When** validation runs, **Then** Pydantic raises ValidationError
3. **Given** validation errors, **When** checking logs, **Then** errors include record_id, field name, and reason

---

### User Story 5 - Track Provenance Metadata (Priority: P2)

A compliance officer wants every ingested trace to include provenance (source, license, sensitivity) so the system can audit data origins and enforce license compliance.

**Why this priority**: Legal compliance and ethical AI (Constitution Principle VIII).

**Independent Test**: Query all Traces and verify each has complete provenance metadata (source_type, license, ingested_at, pipeline_version).

**Acceptance Scenarios**:

1. **Given** a HF dataset with known license, **When** ingesting, **Then** all Traces have `license` field matching dataset license
2. **Given** ingested Traces, **When** querying by `sensitivity="PUBLIC"`, **Then** only public traces are returned (no PII)
3. **Given** a Trace, **When** checking provenance, **Then** it includes ingestion timestamp and pipeline version for reproducibility

---

### Edge Cases

- What happens when **HuggingFace dataset is rate-limited or unavailable**?  
  → Pipeline should retry with exponential backoff and log failures without data loss
  
- What happens when **Neo4j or Qdrant is unreachable during ingestion**?  
  → Batch should be rolled back and retried; ingestion is transactional per batch
  
- What happens when **embedding model fails or times out**?  
  → Step is stored in Neo4j without embedding; Qdrant insertion is skipped and logged for retry
  
- What happens when **duplicate trace_id is detected**?  
  → Skip and log as duplicate; update metadata if source provenance differs
  
- What happens when **schema version changes mid-ingestion**?  
  → New records use new schema version; migration path must be tested before deployment

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST parse HuggingFace datasets into canonical `TraceBundle` format (Trace + Step[] + Edge[])
- **FR-002**: System MUST generate ULID or UUID for all canonical entities (Trace, Step, Edge) with deterministic content hash for deduplication
- **FR-002a**: ID strategy uses composite approach: `trace_id = base58(SHA256(problem+domain+tags))[:12] + "-" + ULID_suffix[:8]`. This enables (1) dedup detection by matching base, (2) version tracking (same problem, different approaches = different suffixes), (3) uniqueness guarantees (ULID suffix), and (4) readability (human-identifiable base)
- **FR-002b**: On dedup detection (matching base), log as duplicate with versioning info; allow trace versioning via `trace_version` field (e.g., "1.0", "1.1") while maintaining different trace_ids
- **FR-003**: System MUST validate all data against Pydantic v2 canonical schema before storage
- **FR-004**: System MUST persist Trace and Step nodes to Neo4j with uniqueness constraints on IDs
- **FR-005**: System MUST persist NEXT edges between Steps in sequence order
- **FR-006**: System MUST generate embeddings for each Step text and store in Qdrant `steps` collection
- **FR-006a**: Embeddings are configurable via `embedding_model_id` parameter; default is `all-MiniLM-L6-v2` (384 dims) for local development; supports override to larger models (OpenAI, BAAI, etc.) without code changes
- **FR-007**: System MUST store provenance metadata (source_type, source_id, license, sensitivity, ingested_at, pipeline_version) on every Trace
- **FR-008**: System MUST support batch ingestion with configurable batch size (default: 100 traces)
- **FR-009**: System MUST log validation errors without crashing the pipeline
- **FR-010**: System MUST enforce Neo4j constraints (trace_id unique, step_id unique)
- **FR-011**: System MUST create required Qdrant collections (`steps`, `step_windows`, `patterns`) with payload indexes on first run
- **FR-012**: System MUST handle missing or null fields gracefully per Pydantic defaults
- **FR-013**: Step text storage strategy: externalize full text to object storage (S3/GCS) in **Markdown format** with version tracking and multi-contributor support. In Neo4j store: `step.text_key` (pointer), `step.text_preview` (first 500 chars), `step.text_hash` (SHA256). Each versioned step text maintains `(version_number, content_hash, contributor_id, timestamp, change_note)` for audit trail. Enables future wiki-style collaborative editing by humans and LLMs. Initial ingestion creates version 1.0.
- **FR-014**: Embedding-text version binding: Qdrant embedding corresponds to specific step text version. If step text undergoes major revision, mark embedding as stale and flag for re-embedding on next query.
- **FR-015**: Step windows creation: adaptive window size per FSM type. For each trace, after FSM assignment, create context windows with variable depth: hierarchical FSMs (e.g., Design/Decide) → depth 4-6 steps; diagnostic FSMs (Diagnose/Fix) → depth 2-3 steps; optimization loops → depth 5 (baseline→intervention→result); constraint satisfaction → depth 4. Embed concatenated window text with markdown formatting preserved. Store in Qdrant `step_windows` collection with payload: `trace_id, window_start_index, window_size, step_ids[], fsm_id, window_text_hash`. Overlapping windows (stride=1) enable retrieval of related reasoning patterns across FSM transitions.
- **FR-016**: Each window point in Qdrant `step_windows` collection searchable by domain, FSM type, danger signals—enables queries like "find design decision windows in software domain with ambiguity > 0.7"

### Key Entities *(include if feature involves data)*

- **Trace**: Represents a complete reasoning session (trace_id, title, domain, tags, provenance, created_at)
- **Step**: Individual reasoning step (step_id, trace_id, index, actor, role, fsm_id, fsm_state, created_at; text stored externally)
- **StepTextVersion**: Versioned markdown document (version_number, content_hash, contributor_id, timestamp, change_note, markdown_content)
- **Edge**: Relationship between nodes (edge_id, type, src_id, dst_id, weight)
- **Provenance**: Metadata bundle (sources[], license_info, sensitivity, ingested_at, pipeline_version, schema_version)
- **EmbeddingRef**: Reference to vector storage with version binding (embedding_id, model, dim, storage_key, content_hash, text_version_bound)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Successfully ingest 1,000 traces from `open-thoughts/OpenThoughts-114k` HuggingFace dataset in under 5 minutes
- **SC-002**: 100% schema validation pass rate on well-formed data; 0% false negatives on malformed data
- **SC-003**: Neo4j query latency < 50ms for single-trace retrieval (7 hops max)
- **SC-004**: Qdrant similarity search returns top-10 results in < 100ms (excluding embedding generation)
- **SC-005**: Zero data loss on transient failures (retry logic successful)
- **SC-006**: 100% provenance coverage (all Traces have complete metadata)
- **SC-007**: Storage efficiency: Neo4j nodes < 2KB avg, Qdrant payloads < 1KB avg per step
- **SC-008**: Deduplication: 100% detection rate on re-ingested identical traces (content hash works)

## Non-Functional Requirements

- **Performance**: Ingestion throughput ≥ 200 traces/minute on single instance
- **Reliability**: Pipeline crash recovery via checkpoint/resume (batch-level granularity)
- **Scalability**: Support datasets up to 100K traces without re-architecture; tested on both 114K and 1.2M scale datasets
- **Observability**: Structured logging with trace_id context on all operations
- **Testability**: Unit tests for schema validation, integration tests for end-to-end ingestion (both dataset sizes)
- **Compliance**: License violations block ingestion; sensitivity labels enforced

## Clarifications

### Session 2026-02-12

- **Q: Which HuggingFace dataset should be the primary ingestion target?** → **A: Use both iteratively. Start with `open-thoughts/OpenThoughts-114k` (114K rows) for MVP validation and pipeline testing. Then scale to `open-thoughts/OpenThoughts3-1.2M` (1.2M rows, 16x QwQ-32B annotations) for performance benchmarking, deduplication validation, and provenance tracking at scale. Both datasets use Apache 2.0 license (safe for experimentation).**

- **Q: What embedding model should the ingestion pipeline use?** → **A: Configurable embeddings with sensible defaults for MVP. Start with local `all-MiniLM-L6-v2` (384 dims) for development—no API calls, no rate limits, deterministic. Allow runtime override via `embedding_model_id` config parameter to support larger models (OpenAI 3072 dims, BAAI/bge-large-en-v1.5, etc.) without code changes. This balances iteration speed with future flexibility.**

- **Q: How should canonical entity IDs be generated and handled for deduplication?** → **A: Composite approach with versioning: `trace_id = base58(SHA256(problem+domain+tags))[:12] + "-" + ULID_suffix[:8]`. Deterministic base enables dedup detection and version tracking (same problem, different ULID suffixes = different approaches); ULID suffix guarantees uniqueness. Per-trace `trace_version` field (e.g., "1.0", "1.1") supports iterative improvements without ID collisions. Separates identity(ULID) from signature(hash).**

- **Q: How should Step text be stored to optimize query performance and storage efficiency?** → **A: Externalize to object storage (S3/GCS) in Markdown format with version tracking and multi-contributor support. Neo4j stores pointers (`step.text_key`, `step.text_preview`, `step.text_hash`) only. Each text version maintains audit trail: `(version_number, content_hash, contributor_id, timestamp, change_note)`. This enables future wiki-style collaborative editing by humans and LLMs while keeping graph lean. Embeddings version-bound to specific text revision; stale embeddings marked for refresh on text update.**

- **Q: How should Step windows (context groups) be created and stored for reasoning retrieval?** → **A: Adaptive window size per FSM type (NOT fixed k=5). Hierarchical FSMs (Design/Decide) use depth 4-6; diagnostic FSMs (Diagnose/Fix) use depth 2-3; optimization loops use depth 5; constraint satisfaction use depth 4. Windows are variable-length context groups aligned to FSM semantics. Store in Qdrant `step_windows` collection with payload: `(trace_id, window_start_index, window_size, step_ids[], fsm_id, window_text_hash)`. Create overlapping windows (stride=1) for pattern retrieval across FSM transitions. Enables semantic queries: "find design windows with ambiguity > 0.7 in software domain."**

## Constitution Compliance Check

**Constitution Version**: 1.1.0

This feature implements:
- ✅ **Principle VI**: Canonical Schema Contract (Pydantic schema is single source of truth)
- ✅ **Principle VII**: Dual-Store Architecture (Neo4j + Qdrant with shared IDs)
- ✅ **Principle VIII**: Provenance and Licensing (full metadata tracking)
- ✅ **Principle V**: Test-First Development (TDD workflow planned in tasks.md)
- ⚠️ **Principle IX**: Privacy and Safety (PII scrubbing deferred to future feature; sensitivity labeling only)

**Quality Gates Applied**:
1. Linting (Python: ruff/mypy)
2. Test Suite (pytest with integration tests)
3. Schema Validation (automated on every record)
4. Provenance Check (required metadata enforced)
5. Benchmark Validation (ingestion performance tracked)

## Summary: Clarification Outcomes

All 5 critical ambiguities successfully resolved. Results integrated above into Functional Requirements, Key Entities, and FSM/Storage decisions.
