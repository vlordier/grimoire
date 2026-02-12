# Build Plan

> Phased implementation roadmap. For what capabilities are needed, see [Capability Requirements](capability-requirements.md).
>
> **See also:** [System Architecture](system-architecture.md) · [Canonical Schemas](../reference/canonical-schemas.md) · [Problem Archetypes](../domain/problem-archetypes.md) · [FSM Catalogue](../domain/fsm-catalogue.md) · [Danger Classification](../domain/danger-classification.md) · [Pattern Detection & Pipeline](../reference/pattern-detection-and-pipeline.md) · [Feature Spec: Phase 1 Implementation](../../specs/001-canonical-schema-implementation/)

---

## Phase 0 — Define scope and "done"

1. Select 1–2 HF datasets to start (small + structured).
2. Decide the first product behavior: **"given a new problem statement, route to FSM + suggest next step(s)"**.
3. Define success metrics:
   * Routing accuracy on a small labeled set
   * "Bad transition prevention" rate (guards blocking premature execute/decide)
   * Retrieval quality (human/LLM judge)

---

## Phase 1 — Build the data plane (canonicalization + storage)

### 1) Implement the canonical schema + ID strategy

* Use the Pydantic schema as the only contract.
* Pick ULID/UUID and a deterministic content hash for dedup.

### 2) Ingest one dataset end-to-end → `TraceBundle`

* Parse each record into:
  * `Trace` + `Step[]`
  * Add `NEXT` edges
* Store raw text and minimal metadata.

### 3) Persist to Neo4j (structure)

* Insert `Trace`, `Step`, `NEXT`
* Add artifacts later; start minimal.

### 4) Persist embeddings to Qdrant (recall)

* Create collections: `steps`, `step_windows`, `patterns`
* Embed:
  * Each step text → `steps`
  * Sliding windows (k=5 default) → `step_windows`

**Deliverable:** similar steps and windows can be queried, and sequences traversed, in Neo4j.

---

## Phase 2 — Add routing + guards (the control plane)

### 5) Implement the danger classifier (regex + probes)

* Start with regex-only to avoid costs.
* Add probes once the pipeline is stable.
* Store `Trace.initial_danger` and optionally `Step.danger`.

### 6) Implement FSM assignment (cheap v1)

* A simple router that picks a base FSM from the opening statement:
  * Debugging vs design vs optimize vs verify vs transform…
* Don't over-engineer; it'll be improved later.

### 7) Implement transition guards

* Implement the 4 guards:
  * No execute while ambiguous
  * No irreversible without verification
  * Adversarial requires monitoring to close
  * Institutional requires stakeholder map to decide
* Store guard outcomes as step properties + edges (`BLOCKED_BY_GUARD` optional)

**Deliverable:** the system can safely refuse premature actions and force clarifying gates.

---

## Phase 3 — Extract artifacts (make the graph meaningful)

### 8) Artifact extraction (weak rules first)

From steps, extract and create `Artifact` nodes:

* Goal, Scope, Constraint, Assumption
* Metric, Test, Evidence
* Risk, Stakeholder, Veto
* Threat/Defense, Monitor/Runbook

Start with heuristics + regex + small "slot-filler" LLM call if needed.

### 9) Link steps ↔ artifacts

Create `MENTIONS`, `DEPENDS_ON`, `EVIDENCE_FOR`, `DECISION_FOR`.

**Deliverable:** graph queries like:
* "Show constraints that drove this decision"
* "Find traces where ambiguity was resolved by metric definition"
* "Find verification artifacts used before irreversible decisions"

---

## Phase 4 — Mine "meta-thoughts" into patterns (core value)

### 10) Pattern candidates (3 channels)

A) **FSM subpaths**: frequent sequences of `(fsm_state, role)`
B) **Graph motifs**: frequent edge structures (supports/refutes/revises)
C) **Semantic clusters**: cluster `step_windows` embeddings → prototypes

### 11) Create Pattern objects + instances

* Create `Pattern` nodes and push prototype embeddings to Qdrant `patterns`.
* Create `PatternInstance` and `Step-[:INSTANCE_OF]->Pattern` edges.

### 12) Score patterns (success proxies)

Compute per instance:
* Revision loop count
* Presence of verification
* Ends cleanly

Aggregate into `Pattern.quality`.

**Deliverable:** a **pattern library** with retrieval + ranking.

---

## Phase 5 — Build the runtime recommender ("next-step engine")

### 13) Runtime flow for a new problem statement

1. Create a new `Trace` + first `Step` (the statement)
2. Run danger classifier → set modifiers + autonomy
3. Choose base FSM (router)
4. Retrieve candidate patterns:
   * Query Qdrant `patterns` (and/or `step_windows`) using current context embedding
   * Filter by FSM/state/danger constraints in payload
5. Rerank (optional): LLM or cross-encoder on top-K
6. Emit:
   * Clarifying questions (if ambiguity)
   * Verification gates (if irreversibility)
   * Stakeholder mapping steps (if institutional)
   * Threat model + monitoring (if adversarial)
   * Otherwise, a concrete plan step template from the best pattern

### 14) Log everything back into the stores

* Selected pattern + rationale features
* Whether guards blocked anything
* User feedback if available

**Deliverable:** the system behaves like a procedural assistant, not a text search engine.

---

## Phase 6 — Evaluation + continuous improvement

### 15) Build a benchmark

* 200–500 prompts across archetypes
* Label:
  * Base FSM
  * Danger archetypes present
  * Whether execute/decide should be blocked early
* Measure:
  * Danger recall (high priority)
  * Guard correctness
  * Pattern suggestion usefulness (human or LLM judge)

### 16) Active learning loops

* Sample borderline cases
* Improve:
  * Danger thresholds
  * FSM router
  * Step role/state labeler
  * Artifact extractor

### 17) Versioning

Version:
* Schema
* Embeddings model
* Mining pipeline
* Pattern library snapshot
* Thresholds

---

## Minimal "MVP order" (fastest path)

1. Ingest → Neo4j + Qdrant steps/windows
2. Danger router + guards
3. Pattern mining from window clustering
4. Runtime recommender (retrieve pattern → propose next step)
5. Evaluation harness
