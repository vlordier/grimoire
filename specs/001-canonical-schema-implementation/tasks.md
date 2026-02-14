# Feature 001 Implementation Tasks: Canonical Schema & Data Ingestion Pipeline

**Branch**: `001-canonical-schema-implementation`  
**Last Updated**: 2026-02-14  
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

```text
- [ ] [TaskID] [P?] [Story?] Description
       Depends on: [Task1] [Task2]
       Files: src/path/file.py, tests/path/test_file.py
       Acceptance: Clear criteria
```

---

## Phase 0: Setup & Foundation

### Setup Tasks (Execute First - Blocks All Other Tasks)

- [x] **[T-001]** [P1] [Setup] Verify project structure and pyproject.toml configuration
  - Depends on: (none - blocks all)
  - Files: `pyproject.toml`, `src/grimoire/`, `tests/`
  - Acceptance: ✅ Package installs with `pip install -e .`; `pytest --collect-only` finds all test files; `ruff check src/` succeeds

- [x] **[T-002]** [P1] [Setup] Review and document API contracts from plan
  - Depends on: (documentation only)
  - Files: `specs/001-canonical-schema-implementation/contracts/`
  - Acceptance: ✅ All 4 API contracts (ingestion, storage, retrieval, text-versioning) are readable and reference implementation tasks

---

## Phase 1: MVP - User Story 1 - Ingest HuggingFace Dataset (P1 Priority)

**Goal**: Parse HuggingFace OpenThoughts datasets into canonical Trace format with full provenance metadata.

### Implementation Tasks

- [x] **[T-003]** [P1] [US1] Enhance parser with batch processing
  - Depends on: T-001
  - Files: `src/grimoire/ingestion/parser.py`
  - Acceptance: ✅ Add `parse_batch()` method to HuggingFaceParser; Handle multiple records efficiently; Return statistics (success/fail counts)

- [x] **[T-004]** [P1] [US1] Implement HF dataset loader
  - Depends on: T-001
  - Files: `src/grimoire/ingestion/hf_loader.py`
  - Acceptance: ✅ Load 114K variant with configurable limits; Load 1.2M variant with streaming; Parse 100 records in <2 seconds

- [x] **[T-005]** [P1] [US1] Add deduplication detection
  - Depends on: T-003
  - Files: `src/grimoire/ingestion/parser.py`
  - Acceptance: ✅ Generate deterministic trace IDs from problem + domain; Track dedup statistics; Skip duplicate traces

- [x] **[T-006]** [P1] [US1] Extract domain/tag parsing
  - Depends on: T-003
  - Files: `src/grimoire/ingestion/parser.py`
  - Acceptance: ✅ Parse domain from metadata; Handle tags (comma-separated or array); Fallback to 'general' domain

### Testing & Validation Tasks

- [x] **[T-007]** [P1] [US1] Validate schema compliance
  - Depends on: T-003, T-006
  - Files: `src/grimoire/ingestion/validator.py`
  - Acceptance: ✅ Validate Trace structure (all required fields); Validate Step structure with parent Trace; Return detailed error messages

- [x] **[T-008]** [P1] [US1] Log validation errors
  - Depends on: T-001
  - Files: `src/grimoire/logging_setup.py`
  - Acceptance: ✅ All validation errors logged with context; Trace ID in every log record; Color-formatted output in development

### Integration Test Tasks

- [x] **[T-009]** [P1] [US1] E2E test 100 traces
  - Depends on: T-003, T-004, T-005, T-007
  - Files: `tests/integration/test_ingestion_114k.py`
  - Acceptance: ✅ TestIngestion_114k class with 4 test methods; 100% trace ID validity; All provenance fields present; Dedup detection working

- [x] **[T-010]** [P2] [US1] Benchmark 1.2M traces
  - Depends on: T-009
  - Files: `tests/integration/test_ingestion_1_2m.py`
  - Acceptance: ✅ Framework in place; Benchmark execution deferred to optional Phase 2

---

## Phase 2: MVP - User Story 2 - Store Graph in Neo4j (P1 Priority)

**Goal**: Persist Trace, Step, and Edge entities in Neo4j with proper relationships and constraints.

### Implementation Tasks

- [x] **[T-011]** [P1] [US2] Create Neo4j client with pooling
  - Depends on: T-001
  - Files: `src/grimoire/storage/neo4j.py`
  - Acceptance: ✅ Neo4jStorage class with driver management; Connection pooling (pool_size=50); Graceful failure handling

- [x] **[T-012]** [P1] [US2] Create constraints/indexes
  - Depends on: T-011
  - Files: `src/grimoire/storage/neo4j.py`
  - Acceptance: ✅ UNIQUE constraint on Trace(trace_id); UNIQUE constraint on Step(step_id); Index on domain; Index on (fsm_id, fsm_state)

- [x] **[T-013]** [P1] [US2] Implement Trace insertion
  - Depends on: T-012
  - Files: `src/grimoire/storage/neo4j.py`
  - Acceptance: ✅ Insert Trace node with all properties; Flatten Trace.provenance to properties; Return inserted trace ID

- [x] **[T-014]** [P1] [US2] Implement Step insertion
  - Depends on: T-013
  - Files: `src/grimoire/storage/neo4j.py`
  - Acceptance: ✅ Insert Step node with metadata; Create HAS_STEP relationship to Trace; Preserve index for ordering

- [x] **[T-015]** [P1] [US2] Create NEXT edges
  - Depends on: T-014
  - Files: `src/grimoire/storage/neo4j.py`
  - Acceptance: ✅ Create NEXT edges from Step[i] to Step[i+1]; Preserve step sequence; Batch relationship creation

### Testing & Validation Tasks

- [x] **[T-016]** [P1] [US2] Verify constraints
  - Depends on: T-012
  - Files: `tests/integration/test_neo4j_fullstack.py`
  - Acceptance: ✅ Test uniqueness constraint prevents duplicates; Test index performance

- [x] **[T-017]** [P1] [US2] Test transactional rollback
  - Depends on: T-015
  - Files: `tests/integration/test_neo4j_fullstack.py`
  - Acceptance: ✅ Test all-or-nothing semantics; Test partial rollback

- [x] **[T-018]** [P1] [US2] Implement retrieval queries
  - Depends on: T-013
  - Files: `src/grimoire/storage/neo4j.py`
  - Acceptance: ✅ Get Trace by ID with all properties; Get Steps in original order; Filter by domain/role/fsm_id

### Integration Test Tasks

- [x] **[T-019]** [P1] [US2] E2E Neo4j test
  - Depends on: T-013, T-014, T-015, T-018
  - Files: `tests/integration/test_neo4j_fullstack.py`
  - Acceptance: ✅ TestNeo4jPersistence with 4 test methods; Insert/retrieve/batch operations work

---

## Phase 3: MVP - User Story 3 - Store Embeddings in Qdrant (P1 Priority)

**Goal**: Generate and store step embeddings in Qdrant with metadata filtering for semantic search.

### Implementation Tasks

- [x] **[T-020]** [P1] [US3] Create embedding loader
  - Depends on: T-001
  - Files: `src/grimoire/embedding/model_loader.py`
  - Acceptance: ✅ Load all-MiniLM-L6-v2 (384 dimensions); Generate embeddings from text list; Configurable model_id

- [x] **[T-021]** [P1] [US3] Create Qdrant client
  - Depends on: T-001
  - Files: `src/grimoire/storage/qdrant_client.py`
  - Acceptance: ✅ QdrantStorage class; Create 'steps' collection (384-dim); HNSW index with COSINE distance

- [x] **[T-022]** [P1] [US3] Implement embedding generation
  - Depends on: T-020
  - Files: `src/grimoire/embedding/embedder.py`
  - Acceptance: ✅ Generate embeddings with metadata; Compute content hash; Version binding for staleness

- [x] **[T-023]** [P1] [US3] Implement vector insertion
  - Depends on: T-021, T-022
  - Files: `src/grimoire/storage/qdrant_client.py`
  - Acceptance: ✅ Insert single vector with metadata; Batch insert 5+ vectors; Include trace_id, domain, role, danger signals

- [x] **[T-024]** [P1] [US3] Implement search with filters
  - Depends on: T-023
  - Files: `src/grimoire/storage/qdrant_client.py`
  - Acceptance: ✅ Search similar steps by embedding; Filter by domain and role; Return top-K with scores

### Integration Test Tasks

- [x] **[T-025]** [P1] [US3] E2E Qdrant test
  - Depends on: T-023, T-024
  - Files: `tests/integration/test_qdrant_fullstack.py`
  - Acceptance: ✅ TestQdrantEmbeddings with 4 test methods; Insert/search/filter operations work

---

## Phase 4: P2 - Enhanced Features (Optional)

### User Story 4 - Enhanced Schema Validation (P2)

- [ ] **[T-026]** [P2] [US4] Schema validation suite
  - Depends on: T-007
  - Files: `src/grimoire/ingestion/validator.py`
  - Acceptance: ⏸️ Deferred to Phase 2

### User Story 5 - Enhanced Provenance (P2)

- [ ] **[T-027]** [P2] [US5] Enhanced provenance reporting
  - Depends on: T-019
  - Files: `src/grimoire/ingestion/`
  - Acceptance: ⏸️ Deferred to Phase 2

---

## 📊 Dependency Graph

```
Phase 0 (Setup)
  ├── T-001 ──┬── T-003 ──┬── T-005 ──┬── T-007 ──┬── T-009 ──┬── T-010
  │           │            │            │            │            │
  │           ├── T-004 ───┤            │            │            │
  │           │            ├── T-006 ───┤            │            │
  │           │                         ├── T-008 ───┘            │
  │           │                                                          (Story 1)
  └── T-002 ──┴── T-011 ──┬── T-012 ──┬── T-013 ──┬── T-014 ──┬── T-019
                          │            │            │            │
                          │            │            ├── T-015 ───┤
                          │            │            │            │
                          │            │            ├── T-016 ───┤
                          │            │            │            │
                          │            │            ├── T-017 ───┤
                          │            │            │            │
                          │            └── T-018 ───┘            │
                          │                                         (Story 2)
                          └── T-020 ──┬── T-022 ──┬── T-023 ──┬── T-025
                                       │            │            │
                                       ├── T-021 ───┤            │
                                       │            │            │
                                       └── T-024 ───┘            │
                                                                   (Story 3)
```

---

## 🚀 Parallel Execution Opportunities

### Story 1 (Ingestion) - After T-001
- T-003, T-004 can run in parallel (different files)

### Story 2 (Neo4j) - After T-011
- T-012, T-018 can run in parallel (different methods)

### Story 3 (Qdrant) - After T-020, T-021
- T-022, T-023 can run in parallel (different files)

---

## ✅ Acceptance Criteria Summary

### MVP (Stories 1-3) - Must Complete
- [ ] T-001: Project structure verified
- [ ] T-002: API contracts reviewed
- [ ] T-003: Batch processing parser
- [ ] T-004: HuggingFace dataset loader
- [ ] T-005: Deduplication detection
- [ ] T-006: Domain/tag parsing
- [ ] T-007: Schema validation
- [ ] T-008: Structured logging
- [ ] T-009: E2E 100-trace test
- [ ] T-011: Neo4j client with pooling
- [ ] T-012: Constraints & indexes
- [ ] T-013: Trace insertion
- [ ] T-014: Step insertion
- [ ] T-015: NEXT edges
- [ ] T-018: Retrieval queries
- [ ] T-019: E2E Neo4j test
- [ ] T-020: Embedding loader
- [ ] T-021: Qdrant client
- [ ] T-022: Embedding generation
- [ ] T-023: Vector insertion
- [ ] T-024: Search with filters
- [ ] T-025: E2E Qdrant test

### Optional (Phase 2)
- [ ] T-010: 1.2M benchmark (framework ready)
- [ ] T-016: Constraint verification
- [ ] T-017: Transaction rollback
- [ ] T-026: Enhanced validation suite
- [ ] T-027: Enhanced provenance reporting

---

## 📝 Notes

- **Constitution Alignment**: All tasks satisfy Principles I-X (see plan.md)
- **MVP Definition**: Stories 1-3 (22 tasks) constitute the MVP
- **P2 Deferral**: Stories 4-5 are optional and can be addressed in Phase 2
- **Test Strategy**: Unit tests for schema/logic, integration tests for E2E
