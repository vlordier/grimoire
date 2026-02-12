# Grimoire — Meta-Thought Engine

A continuously improving reasoning engine that accumulates structured thinking patterns: **problem → lookup recipe → execute with verification → learn → improve**.

---

## Documentation map

### Vision — *why* and *what*

| Document | Description |
|----------|-------------|
| [Spec](docs/vision/spec.md) | Plain-language project overview — "a living cookbook for problem-solving" |
| [PRD](docs/vision/prd.md) | Full product requirements document |
| [PRD Executive](docs/vision/prd-executive.md) | One-page stakeholder summary |

### Architecture — *how* and *when*

| Document | Description |
|----------|-------------|
| [System Architecture](docs/architecture/system-architecture.md) | ASCII box-and-flow diagram of the full system |
| [Capability Requirements](docs/architecture/capability-requirements.md) | Nine capability areas + 95% checklist |
| [Build Plan](docs/architecture/build-plan.md) | Phased implementation roadmap (Phase 0–6 + MVP) |

### Domain — *the reasoning model*

| Document | Description |
|----------|-------------|
| [Problem Archetypes](docs/domain/problem-archetypes.md) | 15 canonical problem archetypes with steps, failure modes, graph signatures |
| [FSM Catalogue](docs/domain/fsm-catalogue.md) | 10 universal FSMs + transition guards + FSM template mapping |
| [Danger Classification](docs/domain/danger-classification.md) | Four danger archetypes, scoring model, routing decisions |
| [Control Pattern Taxonomy](docs/domain/control-pattern-taxonomy.md) | 10 pattern groups → 6 primitives → formal algebra |

### Reference — *code & schemas*

| Document | Description |
|----------|-------------|
| [Canonical Schemas](docs/reference/canonical-schemas.md) | Authoritative Pydantic v2 contract (Trace, Step, Artifact, Pattern, …) |
| [Storage Mapping](docs/reference/storage-mapping.md) | Neo4j property graph + Qdrant payload 1:1 mapping |
| [Qdrant Setup](docs/reference/qdrant-setup.md) | Collection creation + payload indexes (Python) |
| [Danger Classification Impl](docs/reference/danger-classification-impl.md) | Regex + probe classifier, FSM guards, pytest tests |
| [Pattern Detection & Pipeline](docs/reference/pattern-detection-and-pipeline.md) | Op detection, motif mining, corpus aggregation, embedding pipeline |

---

## Suggested reading order

1. [Spec](docs/vision/spec.md) → [PRD](docs/vision/prd.md) (optionally [PRD Executive](docs/vision/prd-executive.md) for a one-page summary) — understand the project
2. [System Architecture](docs/architecture/system-architecture.md) → [Capability Requirements](docs/architecture/capability-requirements.md) — understand the system
3. [Problem Archetypes](docs/domain/problem-archetypes.md) → [FSM Catalogue](docs/domain/fsm-catalogue.md) → [Danger Classification](docs/domain/danger-classification.md) → [Control Pattern Taxonomy](docs/domain/control-pattern-taxonomy.md) — understand the reasoning model
4. [Canonical Schemas](docs/reference/canonical-schemas.md) → [Storage Mapping](docs/reference/storage-mapping.md) → [Qdrant Setup](docs/reference/qdrant-setup.md) — understand the data layer
5. [Pattern Detection & Pipeline](docs/reference/pattern-detection-and-pipeline.md) → [Danger Classification Impl](docs/reference/danger-classification-impl.md) — understand runtime detection
6. [Build Plan](docs/architecture/build-plan.md) — understand the roadmap

---

## Feature specs

Active feature specifications live in `specs/`:

| Feature | Status |
|---------|--------|
| [001 — Canonical Schema Implementation](specs/001-canonical-schema-implementation/) | In progress |

Each feature directory contains: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, and `contracts/`.

---

## Implementation Roadmap

**Current Phase:** Phase 1 — Schema & Ingestion (Feature [001 — Canonical Schema Implementation](specs/001-canonical-schema-implementation/))

| Phase | Deliverables | Status |
|-------|--------------|--------|
| **0** | Research, requirements capture, architectural vision | ✅ Complete |
| **1** | Canonical schemas (Pydantic v2), data model, ingestion pipeline | 🔄 In progress |
| **2** | Storage layer (Neo4j + Qdrant), retrieval API, pattern mining | ⏳ Queued |
| **3** | FSM engine, danger router, procedural recommendations | ⏳ Queued |
| **4** | Federated learning, improvements loop, quality metrics | ⏳ Queued |

**For detailed roadmap:** See [Build Plan](docs/architecture/build-plan.md) → Phased Implementation.

---

## Common Pitfalls

### Pydantic v1 vs v2

- ❌ `@validator` (v1) — use `@field_validator` (v2)
- ❌ `min_items=N, max_items=M` (v1 syntax) — use `min_length=N, max_length=M` (v2 syntax) for lists
- ❌ `ge=-1` (invalid constraint) — constraints must be meaningful; use `ge=0` or omit
- ✅ `field_validator(..., mode='before' | 'after')` — v2 requires explicit mode
- ✅ `model_validate_json()` instead of `parse_obj()`

**Reference:** [Canonical Schemas](docs/reference/canonical-schemas.md) and [Feature Spec Data Model](/specs/001-canonical-schema-implementation/data-model.md) show v2 patterns.

### ID Format Consistency

All canonical IDs **must** follow:
- `trace_id`: `^[a-zA-Z0-9]{12}-[a-zA-Z0-9]{8}$` — composite (base58(SHA256)[:12] + ULID[:8])
- `step_id`, `edge_id`, `pattern_id`: ULID (26 chars, alphanumeric)
- `content_hash`: `^[a-f0-9]{64}$` — SHA256 lowercase hex

Mismatch causes Neo4j constraint violations and Qdrant query failures.

### Enum Values

All enums **must** use lowercase string values matching canonical definitions:
- `DomainTag`: "general", "software", "ml", "data", "security", "product", "legal", "health", "finance"
- `StepRole`: "goal", "question", "plan", "action", "tool_call", "observation", "critique", "revision", "decision", "verification", "summary", "other"
- `EdgeType`: "next", "supports", "refutes", "revises", "depends_on", "uses_tool", "mentions", "evidence_for", "decision_for", "instance_of", "creates", "uses", "other"

Mismatches between contracts, data-model, and canonical-schemas cause type errors at validation time.

---

## Development workflow

This project uses the **Speckit** workflow system (`.github/agents/`, `.github/prompts/`). See [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for agent definitions and conventions.
