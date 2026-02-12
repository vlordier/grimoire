# Capability Requirements

> What the system needs to do to reach ~95% coverage. For the phased build order, see [Build Plan](build-plan.md).
>
> **See also:** [System Architecture](system-architecture.md) · [Build Plan](build-plan.md) · [Canonical Schemas](../reference/canonical-schemas.md) · [FSM Catalogue](../domain/fsm-catalogue.md) · [Danger Classification](../domain/danger-classification.md)

---

## 1. Canonical trace schema

One normalized event model so every dataset / conversation becomes the same shape:

* `Trace` metadata: domain, source, license, timestamps, success proxy
* `Step` fields: `role/state`, text, tool-call, inputs/outputs, citations
* `Edges`: `NEXT`, `SUPPORTS`, `REFUTES`, `REVISES`, `DEPENDS_ON`, `USES_TOOL`, `MENTIONS`, `EVIDENCE_FOR`, `DECISION_FOR`, `INSTANCE_OF`, `CREATES`, `USES`, `OTHER`
* `Artifacts`: `Goal`, `Scope`, `Constraint`, `Assumption`, `Option`, `Risk`, `Metric`, `Test`, `Evidence`, `Decision`, `Monitor`, `Stakeholder`, `Veto_point`, `Threat`, `Defense`, `Runbook`, `Other`

> See [Canonical Schemas — `EdgeType` and `ArtifactType`](../reference/canonical-schemas.md) for the authoritative enums.

Without this, the system cannot generalize meta-thoughts across datasets.

## 2. Step labeling + state assignment

To run FSM logic and mine patterns, each step needs:

* `FSM_ID` (one of the 10)
* `STATE` (S0..S9)
* `STEP_ROLE` (goal/plan/action/observe/critique/verify/decide/etc.)

Start with weak rules + a small classifier; then iterate with active learning.

## 3. Pattern mining into "meta-thought" objects

Convert traces into reusable patterns:

* **FSM subpaths** (e.g., "hypothesis→test→update" micro-loops)
* **Graph motifs** (common dependency structures)
* **Semantic clusters** (window embeddings → clusters → prototypes)

Each `Pattern` stores:

* a normalized template (steps + slots)
* when it applies (domain/tool/constraint/danger tags)
* success proxies (convergence speed, revision count, verification presence)

## 4. Retrieval + reranking that respects structure

A hybrid retrieval stack:

* Vector search over steps/windows/pattern prototypes
* Graph constraints for "procedural fit" (FSM/state/danger compatibility)
* Reranker (optional) using cheap cross-encoder or LLM scoring

Key: retrieval must answer **"what should I do next?"**, not only "similar docs".

## 5. Next-step recommender policy

Given current context:

1. Run danger router
2. Choose base FSM
3. Retrieve top-K candidate patterns for current state
4. Pick pattern by:
   * FSM compatibility
   * Danger modifiers
   * Success proxy score
   * Minimal required assumptions
5. Emit either:
   * Clarification questions
   * A plan template
   * A verification checklist
   * An execution step (if allowed)

This is what turns the library into an agent.

## 6. Success proxies + evaluation harness

To avoid garbage patterns:

* Success labels when available (correctness, acceptance)
* Otherwise proxies:
  * Revision loops count
  * Presence of verification steps
  * Tool outputs consistent with claims
  * "Ended cleanly" vs "abandoned"
* A benchmark suite:
  * 200–500 prompts spanning archetypes
  * Measure: correct routing, prevented bad transitions, time-to-clarify, and "quality of next step" (human or LLM judge)

## 7. Safety + policy layer

Separate from the four "danger archetypes":

* Content safety gating (refuse/redirect)
* Legal/compliance constraints where relevant
* Privacy handling for stored traces (PII scrubbing, licensing)
* Provenance and audit trail (why a pattern was suggested)

## 8. Online learning loop

* Log: which pattern was selected, outcome proxy, user feedback
* Periodically:
  * Prune low-performing patterns
  * Split overly broad clusters
  * Retrain step labeler + danger thresholds
  * Refresh embeddings/versioning

## 9. Versioning and reproducibility

* Embedding model version + parameters
* Schema version
* Pattern mining version
* Dataset source + license snapshot
* Deterministic IDs for steps/patterns

Otherwise retrieval quality will drift and be un-debuggable.

---

## Minimal "95% capable" checklist

If you do only these, the system achieves ~95% coverage:

1. Canonical schema + step/state labeler
2. Danger router + FSM guards
3. Pattern objects + hybrid retrieval (vector + graph constraints)
4. Next-step recommender policy
5. Evaluation harness + pruning loop

Everything else is scale and polish.
