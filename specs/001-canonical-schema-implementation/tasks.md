# Feature 001 Implementation Tasks: Canonical Schema & Data Ingestion Pipeline

**Branch**: `001-canonical-schema-implementation`  
**Last Updated**: 2026-02-13  
**Status**: Phase 1 Implementation  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

---

## 🎯 Overview

This document defines all implementation tasks for Feature 001 in dependency order. Tasks are grouped by user story and phase, with clear acceptance criteria and file paths for each.

**Total Tasks**: 22  
**Estimated Effort**: 40-60 hours  
**MVP Scope**: Stories 1-3 (Ingestion + Neo4j + Qdrant)  
**Implementation Order**: Parallel execution possible after Setup Phase

---

## 📋 Task Legend

```
- [ ] [TaskID] [P?] [Story?] Description
       Depends on: [Task1] [Task2]
       Files: src/path/file.py, tests/path/test_file.py
       Acceptance: Clear criteria
```

---

## Phase 0: Setup & Foundation

### Setup Tasks (Execute First - Blocks All Other Tasks)

- [ ] **[T-001]** [P1] [Setup] Verify project structure and pyproject.toml configuration
  - Depends on: (none - blocks all)
  - Files: `pyproject.toml`, `src/grimoire/`, `tests/`
  - Acceptance: ✅ Package installs with `pip install -e .`; `pytest --collect-only` finds all test files; `ruff check src/` succeeds

- [ ] **[T-002]** [P1] [Setup] Review and document API contracts from plan
  - Depends on: (documentation only)
  - Files: `specs/001-canonical-schema-implementation/contracts/`
  - Acceptance: ✅ All 4 API contracts (ingestion, storage, retrieval, text-versioning) are readable and reference implementation tasks

---

## Phase 1: MVP - User Story 1 - Ingest HuggingFace Dataset (P1 Priority)

**Goal**: Parse HuggingFace OpenThoughts datasets into canonical Trace format with full provenance metadata.

### Story 1 Setup Tasks

- [ ] **[T-003]** [P1] [Story1] Enhance HuggingFace parser with batch processing and error recovery
  - Depends on: [T-001]
  - Files: `src/grimoire/ingestion/parser.py`
  - Acceptance: ✅ Parser has `parse_batch()` method; handles missing fields gracefully; logs errors without crashing; test_batch_parsing passes

- [ ] **[T-004]** [P1] [Story1] Implement configurable dataset loader (114K + 1.2M variants)
  - Depends on: [T-001]
  - Files: `src/grimoire/ingestion/hf_loader.py` (new)
  - Acceptance: ✅ `HFDatasetLoader` class supports both dataset sizes; configurable via `IngestionConfig`; integration test loads 100 traces from each dataset

- [ ] **[T-005]** [P1] [Story1] Add deduplication detection by content hash
  - Depends on: [T-003]
  - Files: `src/grimoire/ingestion/parser.py`, `tests/unit/test_ingestion_parser.py`
  - Acceptance: ✅ Duplicate traces detected by matching base58(SHA256) hash; `is_duplicate` flag set correctly; test_dedup_detection passes; dedup stats tracked

- [ ] **[T-006]** [P1] [Story1] Extract domain and tag parsing from dataset records
  - Depends on: [T-003]
  - Files: `src/grimoire/ingestion/parser.py`
  - Acceptance: ✅ Domain defaulting to GENERAL if missing; tags parsed from string or list format; tag parsing test passes with various input formats

### Story 1 Validation Tasks

- [ ] **[T-007]** [P1] [Story1] Validate trace schema compliance before storage
  - Depends on: [T-003], [T-005]
  - Files: `src/grimoire/ingestion/validator.py` (new), `tests/unit/test_parser_validation.py` (new)
  - Acceptance: ✅ Pydantic validates all Trace + Step + Edge objects; malformed records raise ValidationError; validation test suite covers missing fields, invalid enums, type errors

- [ ] **[T-008]** [P1] [Story1] Log all validation errors with context (record_id, field, reason)
  - Depends on: [T-007]
  - Files: `src/grimoire/logging_setup.py` (new), `src/grimoire/ingestion/parser.py` (modify)
  - Acceptance: ✅ Validation errors logged with trace_id context; logs include field name and validation reason; can re-parse by record_id

### Story 1 Integration Tasks

- [ ] **[T-009]** [P1] [Story1] Create end-to-end ingestion test with 100 traces (114K dataset)
  - Depends on: [T-004], [T-007], [T-008]
  - Files: `tests/integration/test_ingestion_114k.py` (new), `conftest.py` (update)
  - Acceptance: ✅ Ingest 100 traces from OpenThoughts-114k; all traces have valid trace_id, domain, tags, provenance; dedup detection works; test completes in < 30 sec

- [ ] **[T-010]** [P1] [Story1] Implement large dataset ingestion benchmark (1.2M traces)
  - Depends on: [T-009]
  - Files: `tests/integration/test_ingestion_1_2m.py` (new)
  - Acceptance: ✅ Ingest 1.2M traces from OpenThoughts3-1.2M; throughput >= 200 traces/min on single instance; memory usage stable < 1GB; dedup detection working at scale

---

## Phase 2: MVP - User Story 2 - Store Graph in Neo4j (P1 Priority)

**Goal**: Persist canonicalized Trace/Step/Edge graph to Neo4j with constraints and transactions.

### Story 2 Storage Setup Tasks

- [ ] **[T-011]** [P1] [Story2] Create Neo4j client with connection pooling and transaction support
  - Depends on: [T-001]
  - Files: `src/grimoire/storage/neo4j.py` (enhance), `tests/unit/test_neo4j_client.py` (new)
  - Acceptance: ✅ Neo4jStorage class has connection pool; transaction context manager; connection verification; unit tests for creation/teardown

- [ ] **[T-012]** [P1] [Story2] Create Neo4j constraints and indexes for performance
  - Depends on: [T-011]
  - Files: `src/grimoire/storage/neo4j.py` (enhance methods)
  - Acceptance: ✅ `create_constraints()` enforces UNIQUE (trace_id, step_id); `create_indexes()` adds indexes on (domain, fsm_id/state, role); test verifies index/constraint existence

- [ ] **[T-013]** [P1] [Story2] Implement Trace node insertion with batch upsert
  - Depends on: [T-011], [T-007]
  - Files: `src/grimoire/storage/neo4j.py` (methods: `insert_trace`, `batch_insert_traces`)
  - Acceptance: ✅ Trace node created with all properties; batch insertion transactional; rollback on error; unit test inserts and retrieves trace

- [ ] **[T-014]** [P1] [Story2] Implement Step node insertion with provenance
  - Depends on: [T-013]
  - Files: `src/grimoire/storage/neo4j.py` (methods: `insert_step`, `batch_insert_steps`)
  - Acceptance: ✅ Step nodes created with trace_id FK; step_id unique constraint enforced; provenance metadata stored; test inserts and retrieves steps by trace

- [ ] **[T-015]** [P1] [Story2] Create NEXT edges between sequential Steps
  - Depends on: [T-014]
  - Files: `src/grimoire/storage/neo4j.py` (method: `create_next_edges`, `batch_create_edges`)
  - Acceptance: ✅ NEXT edges created in index order; no gaps in sequence; edge properties include weight; test traverses NEXT edges and verifies order

### Story 2 Validation Tasks

- [ ] **[T-016]** [P1] [Story2] Verify uniqueness constraints are enforced in Neo4j
  - Depends on: [T-012], [T-013]
  - Files: `tests/integration/test_neo4j_constraints.py` (new)
  - Acceptance: ✅ Duplicate trace_id insertion fails with constraint error; duplicate step_id insertion fails; test verifies error type

- [ ] **[T-017]** [P1] [Story2] Test transactional rollback on partial batch failure
  - Depends on: [T-015]
  - Files: `tests/integration/test_neo4j_transactions.py` (new)
  - Acceptance: ✅ Batch of 10 traces with 1 invalid trace rolls back entire batch; no partial data in DB; test verifies DB state before/after

### Story 2 Query Tasks

- [ ] **[T-018]** [P1] [Story2] Implement trace retrieval queries (by trace_id, by domain)
  - Depends on: [T-015]
  - Files: `src/grimoire/storage/neo4j.py` (methods: `get_trace`, `get_traces_by_domain`, `get_trace_steps`)
  - Acceptance: ✅ `get_trace(trace_id)` returns Trace with all properties; `get_trace_steps(trace_id)` returns Steps in index order; latency < 50ms

- [ ] **[T-019]** [P1] [Story2] Create integration test for Neo4j end-to-end (ingest → store → query)
  - Depends on: [T-009], [T-018]
  - Files: `tests/integration/test_neo4j_fullstack.py` (new)
  - Acceptance: ✅ Ingest 100 traces, insert to Neo4j, query back all traces with steps; all data matches original; test completes in < 60 sec

---

## Phase 3: MVP - User Story 3 - Store Embeddings in Qdrant (P1 Priority)

**Goal**: Generate step embeddings and store in Qdrant with version binding and filterable payloads.

### Story 3 Embedding Setup Tasks

- [ ] **[T-020]** [P1] [Story3] Create configurable embedding model loader (default all-MiniLM-L6-v2)
  - Depends on: [T-001]
  - Files: `src/grimoire/embedding/model_loader.py` (new), `tests/unit/test_embedding_loader.py` (new)
  - Acceptance: ✅ Load default model locally; verify dimensions (384); configurable override via `embedding_model_id`; unit test embeds sample text

- [ ] **[T-021]** [P1] [Story3] Create Qdrant client with collection initialization
  - Depends on: [T-001]
  - Files: `src/grimoire/storage/qdrant_client.py` (new), `tests/unit/test_qdrant_client.py` (new)
  - Acceptance: ✅ QdrantStorage connects to Qdrant; creates `steps` collection on first run; creates `step_windows` collection; unit test verifies collections exist

- [ ] **[T-022]** [P1] [Story3] Implement step embedding generation and version binding
  - Depends on: [T-020]
  - Files: `src/grimoire/embedding/embedder.py` (new), `tests/unit/test_embedder.py` (new)
  - Acceptance: ✅ Embed step text with configured model; bind embedding to text version; mark stale if text updated; unit test verifies version binding on text change

- [ ] **[T-023]** [P1] [Story3] Implement Qdrant vector insertion with payload metadata
  - Depends on: [T-021], [T-022]
  - Files: `src/grimoire/storage/qdrant_client.py` (methods: `insert_step_embedding`, `batch_insert_embeddings`)
  - Acceptance: ✅ Insert vector + payload {trace_id, step_id, domain, role, danger_*}; payload indexes created; unit test inserts and searches

- [ ] **[T-024]** [P1] [Story3] Implement Qdrant search with filters (domain, FSM, danger signals)
  - Depends on: [T-023]
  - Files: `src/grimoire/storage/qdrant_client.py` (methods: `search_similar_steps`, `search_with_filter`)
  - Acceptance: ✅ Semantic search returns top-K similar steps; filtered search returns only matching payloads; latency < 100ms

- [ ] **[T-025]** [P1] [Story3] Create integration test for Qdrant end-to-end (embed → store → search)
  - Depends on: [T-019], [T-024]
  - Files: `tests/integration/test_qdrant_fullstack.py` (new)
  - Acceptance: ✅ Embed 100 steps, insert to Qdrant, search for similar steps with filters; results filtered correctly by domain; test completes in < 60 sec

---

## Phase 4: Extended - User Story 4 - Schema Validation (P2 Priority)

**Goal**: Comprehensive schema validation coverage and error management.

- [ ] **[T-026]** [P2] [Story4] Add comprehensive validation test suite for all Pydantic models
  - Depends on: [T-007]
  - Files: `tests/unit/test_schema_validation.py` (new)
  - Acceptance: ✅ Test missing required fields, invalid enum values, type errors, constraint violations for Trace, Step, Edge models; all edge cases covered

---

## Phase 5: Extended - User Story 5 - Provenance Tracking (P2 Priority)

**Goal**: Ensure complete provenance metadata capture and compliance.

- [ ] **[T-027]** [P2] [Story5] Implement provenance metadata capture for all ingested traces
  - Depends on: [T-009]
  - Files: `src/grimoire/ingestion/parser.py` (already implemented, verify)
  - Acceptance: ✅ Every Trace has source_type, source_id, license, sensitivity, ingested_at, pipeline_version; integration test queries all traces and verifies provenance complete

---

## 🔄 Dependency Graph

```
Legend: → means "depends on"

[T-001] → [T-002]
          [T-003] → [T-004] → [T-009]
          [T-005] →          [T-009]
          [T-006] →          [T-009]
          [T-007] →          [T-009]
          [T-008] →          [T-009]

[T-009] → [T-010] (sequential for scale testing)

[T-001] → [T-011] → [T-012] → [T-013] → [T-014] → [T-015] → [T-018] → [T-019]
                                                       [T-016]
                                                       [T-017]

[T-019] → [T-020] → [T-021] → [T-022] → [T-023] → [T-024] → [T-025]

[T-007] → [T-026] (P2, optional for MVP)
[T-009] → [T-027] (P2, optional for MVP)
```

---

## ⚡ Parallel Execution Opportunities

**Wave 1 (Setup)**: [T-001], [T-002] (1-2 hours)
**Wave 2 (Foundation)**: [T-003], [T-004], [T-020], [T-021] can run in parallel after Wave 1 (3-4 hours)
**Wave 3 (Ingestion)**: [T-005], [T-006], [T-007], [T-008] in parallel (2-3 hours)
**Wave 4 (Storage - Neo4j)**: [T-011], [T-012] parallel, then [T-013], [T-014], [T-015] parallel (4-5 hours)
**Wave 5 (Storage - Qdrant)**: [T-022], [T-023], [T-024] parallel (3-4 hours)
**Wave 6 (Integration Tests)**: [T-009], [T-010], [T-019], [T-025] can run in parallel (5-6 hours)

**Total Critical Path**: ~20-25 hours for MVP completion

---

## 📊 User Story Summary

| Story | Title | Priority | Tasks | Est. Hours | Status |
|-------|-------|----------|-------|-----------|--------|
| 1 | Ingest HuggingFace Dataset | P1 | T-003 to T-010 | 8-12 | In Progress |
| 2 | Store Graph in Neo4j | P1 | T-011 to T-019 | 8-12 | Not Started |
| 3 | Store Embeddings in Qdrant | P1 | T-020 to T-025 | 6-8 | Not Started |
| 4 | Validate Schema | P2 | T-026 | 2-3 | Not Started |
| 5 | Track Provenance | P2 | T-027 | 1-2 | Not Started |

---

## ✅ MVP Scope & Success Criteria

**MVP Includes**: Stories 1-3 (all P1 tasks)

**MVP Success Criteria**:
1. ✅ Ingest 100+ traces from OpenThoughts-114k in < 5 min (SC-001)
2. ✅ All traces stored in Neo4j with correct schema (SC-003)
3. ✅ All steps stored with NEXT edges in sequence (SC-002)
4. ✅ All embeddings stored in Qdrant with filterable payloads (SC-004)
5. ✅ Semantic search returns relevant results in < 100ms (SC-004)
6. ✅ Deduplication working: duplicate traces detected and marked (SC-006)
7. ✅ Full provenance metadata on all traces (SC-008)
8. ✅ Throughput >= 200 traces/min on single instance (SC-001)

---

## 🚀 Implementation Strategy

1. **Start with Setup**: Complete [T-001], [T-002] to establish project foundation
2. **Ingestion First**: Implement Story 1 (T-003 to T-010) before storage, since data quality depends on parsing
3. **Storage in Parallel**: Stories 2 & 3 (T-011-T-025) can run in parallel after Story 1 MVP
4. **Test Continuously**: Integration tests (T-009, T-019, T-025) validate each story independently
5. **Scale Validation**: Run large-dataset test (T-010) before marking complete
6. **P2 Tasks Optional**: Stories 4-5 can be deferred if MVP is time-constrained

---

## 📝 Task Checklist Template

When implementing each task, follow this checklist:

```
Task: [TaskID] Description
Status: [ ] Not Started [ ] In Progress [ ] Code Complete [ ] Tested [ ] Reviewed [ ] Committed

Code Changes:
- [ ] Implementation code written and linted
- [ ] Unit tests written and passing
- [ ] Integration tests written and passing
- [ ] Type hints correct (mypy passes)
- [ ] Documentation updated

Quality:
- [ ] Code review completed
- [ ] Test coverage ≥ 80% for new code
- [ ] No hardcoded values (config driven)
- [ ] Error handling and logging complete

Commit:
- [ ] git add -A && git commit -m "feat/fix: [task summary]"
- [ ] Commit message references [TaskID]
```

---

## 📖 Related Documentation

- Spec: [spec.md](spec.md)
- Plan: [plan.md](plan.md)
- Data Model: [data-model.md](data-model.md)
- API Contracts: [contracts/](contracts/)
- Quickstart: [quickstart.md](quickstart.md)
