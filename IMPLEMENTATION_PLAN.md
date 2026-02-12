## Step-by-step implementation plan (high level)

### Phase 0 — Define scope and “done”

1. Pick 1–2 HF datasets to start (small + structured).
2. Decide the first product behavior: **“given a new problem statement, route to FSM + suggest next step(s)”**.
3. Define success metrics:

* routing accuracy on a small labeled set
* “bad transition prevention” rate (guards blocking premature execute/decide)
* retrieval quality (human/LLM judge)

---

## Phase 1 — Build the data plane (canonicalization + storage)

### 1) Implement the canonical schema + ID strategy

* Use the Pydantic schema you now have as the only contract.
* Pick ULID/UUID and a deterministic content hash for dedup.

### 2) Ingest one dataset end-to-end → `TraceBundle`

* Parse each record into:

  * `Trace` + `Step[]`
  * add `NEXT` edges
* Store raw text and minimal metadata.

### 3) Persist to Neo4j (structure)

* Insert `Trace`, `Step`, `NEXT`
* Add artifacts later; start minimal.

### 4) Persist embeddings to Qdrant (recall)

* Create collections: `steps`, `step_windows`, `patterns`
* Embed:

  * each step text → `steps`
  * sliding windows (k=5 default) → `step_windows`

Deliverable: **you can query similar steps/windows** and traverse sequences in Neo4j.

---

## Phase 2 — Add routing + guards (the control plane)

### 5) Implement the danger classifier (regex + probes)

* Start with regex-only to avoid costs.
* Add probes once the pipeline is stable.
* Store `Trace.initial_danger` and optionally `Step.danger`.

### 6) Implement FSM assignment (cheap v1)

* A simple router that picks a base FSM from the opening statement:

  * debugging vs design vs optimize vs verify vs transform…
* Don’t over-engineer; it’ll be improved later.

### 7) Implement transition guards

* Implement the 4 guards:

  * no execute while ambiguous
  * no irreversible without verification
  * adversarial requires monitoring to close
  * institutional requires stakeholder map to decide
* Store guard outcomes as step properties + edges (`BLOCKED_BY_GUARD` optional)

Deliverable: **the system can safely refuse premature actions and force clarifying gates**.

---

## Phase 3 — Extract artifacts (make the graph meaningful)

### 8) Artifact extraction (weak rules first)

From steps, extract and create `Artifact` nodes:

* Goal, Scope, Constraint, Assumption
* Metric, Test, Evidence
* Risk, Stakeholder, Veto
* Threat/Defense, Monitor/Runbook

Start with heuristics + regex + small “slot-filler” LLM call if needed.

### 9) Link steps ↔ artifacts

Create `MENTIONS`, `DEPENDS_ON`, `EVIDENCE_FOR`, `DECISION_FOR`.

Deliverable: graph queries like:

* “show constraints that drove this decision”
* “find traces where ambiguity was resolved by metric definition”
* “find verification artifacts used before irreversible decisions”

---

## Phase 4 — Mine “meta-thoughts” into patterns (your core value)

### 10) Pattern candidates (3 channels)

A) **FSM subpaths**: frequent sequences of `(fsm_state, role)`
B) **Graph motifs**: frequent edge structures (supports/refutes/revises)
C) **Semantic clusters**: cluster `step_windows` embeddings → prototypes

### 11) Create Pattern objects + instances

* Create `Pattern` nodes and push prototype embeddings to Qdrant `patterns`.
* Create `PatternInstance` and `Step-[:INSTANCE_OF]->Pattern` edges.

### 12) Score patterns (success proxies)

Compute per instance:

* revision loop count
* presence of verification
* ends cleanly
  Aggregate into `Pattern.quality`.

Deliverable: you now have a **pattern library** with retrieval + ranking.

---

## Phase 5 — Build the runtime recommender (“next-step engine”)

### 13) Runtime flow for a new problem statement

1. Create a new `Trace` + first `Step` (the statement)
2. Run danger classifier → set modifiers + autonomy
3. Choose base FSM (router)
4. Retrieve candidate patterns:

   * query Qdrant `patterns` (and/or `step_windows`) using current context embedding
   * filter by FSM/state/danger constraints in payload
5. Rerank (optional): LLM or cross-encoder on top-K
6. Emit:

   * clarifying questions (if ambiguity)
   * verification gates (if irreversibility)
   * stakeholder mapping steps (if institutional)
   * threat model + monitoring (if adversarial)
   * otherwise, a concrete plan step template from the best pattern

### 14) Log everything back into the stores

* selected pattern + rationale features
* whether guards blocked anything
* user feedback if available

Deliverable: **the system behaves like a procedural assistant, not a text search engine**.

---

## Phase 6 — Evaluation + continuous improvement

### 15) Build a benchmark

* 200–500 prompts across archetypes
* label:

  * base FSM
  * danger archetypes present
  * whether execute/decide should be blocked early

Measure:

* danger recall (high priority)
* guard correctness
* pattern suggestion usefulness (human or LLM judge)

### 16) Active learning loops

* sample borderline cases
* improve:

  * danger thresholds
  * FSM router
  * step role/state labeler
  * artifact extractor

### 17) Versioning

Version:

* schema
* embeddings model
* mining pipeline
* pattern library snapshot
* thresholds

---

## Minimal “MVP order” (fastest path)

1. Ingest → Neo4j + Qdrant steps/windows
2. Danger router + guards
3. Pattern mining from window clustering
4. Runtime recommender (retrieve pattern → propose next step)
5. Evaluation harness

If you want, next I can lay this out as a repo structure (`/ingest`, `/schema`, `/miners`, `/router`, `/api`) + a minimal API surface (FastAPI endpoints) that matches the flow.
