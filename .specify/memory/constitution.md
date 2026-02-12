<!--
  Sync Impact Report
  ===================
  Version change: 1.0.0 → 1.1.0 (minor update - new principles added)

  Added principles:
    - VI. Canonical Schema Contract (NON-NEGOTIABLE)
    - VII. Dual-Store Architecture
    - VIII. Provenance and Licensing
    - IX. Privacy and Safety
    - X. Continuous Evaluation and Improvement

  Modified sections:
    - Core Principles (expanded from 5 to 10 principles)
    - Technical Stack (new section)
    - Quality Gates (updated to reference new principles)

  Removed sections: None

  Templates requiring updates:
    ✅ .specify/templates/plan-template.md
       — Constitution Check section will now validate new principles
    ✅ .specify/templates/spec-template.md
       — Already compatible with expanded principles
    ✅ .specify/templates/tasks-template.md
       — Task phases align with all principles
    ✅ Technical architecture documents
       — Now formalized in constitution

  Follow-up TODOs:
    - Add schema version validation to ingestion pipeline
    - Implement PII scrubbing in trace processing
    - Create benchmark suite (200-500 prompts)
-->

# Grimoire Constitution

## Core Principles

### I. Recipe-First Architecture

Every feature MUST center on recipes—structured thinking patterns
that encode mid-level reasoning strategies. The core loop is:

**problem → lookup recipe → execute with verification → learn → improve**

Non-negotiable rules:
- Recipes MUST be self-contained and independently testable.
- Recipes MUST include: what to check first, what variables to
  define, what strategy to use, common mistakes to avoid, and when
  to switch approaches.
- No feature bypasses the recipe system; ad-hoc reasoning without a
  recipe is classified as technical debt and MUST be remediated.
- Each recipe MUST have a clear "problem signature" that enables
  retrieval matching.

**Rationale**: The entire value proposition of Grimoire is accumulated
structured reasoning. Without recipes as the atomic unit, the system
degenerates into unstructured prompt engineering.

### II. Verification Before Learning (NON-NEGOTIABLE)

Results MUST be verified before they feed back into the system.
Learning from unverified outputs is the worst failure mode.

Non-negotiable rules:
- Before declaring success, the system MUST check correctness via
  tests, mathematical substitution, output validation, or equivalent
  evidence.
- Every outcome that feeds into recipe improvement MUST have a
  verification trace logged alongside it.
- Unverified outputs MUST NOT update recipe confidence scores,
  propose recipe amendments, or enter shared memory.
- Verification failures MUST be logged with sufficient context for
  post-mortem analysis.

**Rationale**: A system that learns from hallucinations compounds
errors exponentially. Verification is the only defense against
reasoning drift.

### III. Federated Quality Control

Improvements are NOT shared immediately. Proposed recipe improvements
MUST pass quality gates before entering shared memory.

Non-negotiable rules:
- All proposed improvements MUST go through a filtering pipeline:
  noise filtering → testing on challenge cases → verification →
  promotion.
- The shared server MUST reject improvements that fail challenge-case
  validation.
- Each user's local improvements remain local until explicitly
  promoted.
- Promoted recipes MUST include provenance metadata: origin, test
  results, and confidence score.

**Rationale**: Uncontrolled sharing degrades collective quality. The
federated model ensures only battle-tested patterns propagate.

### IV. Exploitation Before Exploration

The system MUST bias toward reusing proven recipes. Exploration
(trying novel approaches) is permitted only when exploitation fails.

Non-negotiable rules:
- For every new problem, the system MUST first attempt the
  highest-confidence matching recipe.
- Exploration MUST be triggered only by verified failure of existing
  recipes, never by default.
- Successful exploration results MUST be captured as new or amended
  recipes (see Principle I).
- Failed exploration MUST be logged with the failure mode to prevent
  redundant future attempts.

**Rationale**: Random reasoning is expensive and unreliable. Structured
reuse is the mechanism by which the system improves over time.

### V. Test-First Development (NON-NEGOTIABLE)

All production code MUST follow Test-Driven Development. The project
MUST be strongly linted and well-tested at all times.

Non-negotiable rules:
- TDD cycle: write tests → confirm tests fail → implement → confirm
  tests pass → refactor. This order is mandatory.
- All source code MUST pass configured linting checks before merge.
- Test coverage MUST reflect the importance and risk level of the
  code under test.
- Integration tests MUST validate agent workflows and script output
  formats.
- Bash scripts MUST pass shellcheck.
- No merge is permitted without passing the full test suite and
  linting.

**Rationale**: A system that learns and evolves its own reasoning
patterns MUST have strong correctness guarantees. Untested code in
Grimoire is a liability that compounds across every recipe it touches.

### VI. Canonical Schema Contract (NON-NEGOTIABLE)

All data MUST conform to the canonical Pydantic schema. No subsystem
may define its own incompatible data model.

Non-negotiable rules:
- The canonical schema (Trace, Step, Artifact, Edge, Pattern) is the
  single contract across ingestion, storage, retrieval, and
  evaluation.
- All ingested data MUST be normalized to canonical form before
  storage.
- Schema versioning MUST be tracked; migrations MUST be explicit and
  tested.
- Breaking schema changes require MAJOR version bump (see Governance).
- No subsystem may bypass the canonical schema or create parallel
  data models.

**Rationale**: Schema drift causes silent bugs in retrieval, mining,
and pattern matching. A single canonical contract ensures all
components interoperate correctly.

### VII. Dual-Store Architecture

Structure and semantics MUST be stored separately: graph database for
relationships, vector database for retrieval.

Non-negotiable rules:
- Neo4j (or compatible graph DB) stores: Steps, Edges, Artifacts,
  Patterns, and all relationships.
- Qdrant (or compatible vector DB) stores: embeddings for Steps,
  Windows, and Patterns with filterable metadata payloads.
- Both stores MUST use the same canonical IDs (no parallel ID
  schemes).
- Vectors MUST include metadata sufficient for FSM/danger/domain
  filtering without Neo4j roundtrip.
- Graph queries validate structure; vector queries provide recall.

**Rationale**: Hybrid storage enables both procedural constraints
(graph) and semantic similarity (vectors) without compromising either.

### VIII. Provenance and Licensing

All ingested data MUST carry provenance metadata and license
information. Unlicensed or improperly attributed data MUST NOT enter
the system.

Non-negotiable rules:
- Every Trace MUST record: source type, source ID, license,
  sensitivity level, ingestion timestamp, pipeline version.
- Datasets with incompatible licenses (e.g., proprietary, no
  redistribution) MUST NOT be ingested without explicit approval.
- Attribution MUST be preserved through all transformations.
- Promoted patterns MUST carry provenance from all contributing
  traces.
- License violations MUST trigger automatic rejection at ingestion.

**Rationale**: Legal compliance and ethical AI require transparent
provenance. Missing attribution creates liability and undermines
trust.

### IX. Privacy and Safety

All traces MUST be screened for PII and unsafe content. Sensitive
data MUST NOT leak into shared memory.

Non-negotiable rules:
- PII detection MUST run on all ingested text before storage.
- Detected PII MUST be scrubbed or the trace rejected (depending on
  sensitivity policy).
- Sensitivity labels (PUBLIC/INTERNAL/CONFIDENTIAL/PII) MUST be
  enforced in pattern promotion.
- Only PUBLIC sensitivity traces may contribute to federated shared
  memory.
- Content safety gating MUST refuse generation of harmful, illegal,
  or policy-violating patterns.

**Rationale**: Privacy violations and unsafe content are
non-negotiable failures. Local-only and federated modes have
different privacy boundaries.

### X. Continuous Evaluation and Improvement

The system MUST measure its own performance and prune low-quality
patterns. Evaluation is not optional.

Non-negotiable rules:
- A benchmark suite (minimum 200 prompts spanning archetypes) MUST
  exist for routing and pattern quality evaluation.
- Pattern quality metrics MUST include: support count, success proxy,
  revision loop count, verification presence.
- Patterns below quality thresholds MUST be demoted or pruned.
- Threshold updates and router changes MUST be validated on the
  benchmark before deployment.
- Schema version, embedding model, and miner version MUST be tracked
  for reproducibility.
- Online learning loops MUST log: pattern usage, outcome proxies,
  user feedback (when available).

**Rationale**: Without continuous evaluation, pattern libraries
degrade over time. Quality gates ensure only proven patterns survive.

## Technical Stack

The following technical decisions are architectural constraints:

- **Primary Language**: Python 3.11+
- **Schema Framework**: Pydantic >= 2
- **Graph Database**: Neo4j (or compatible property graph DB)
- **Vector Database**: Qdrant (or compatible with payload filtering)
- **Embedding Models**: Version tracking REQUIRED; reproducibility MUST
  be ensured across model updates
- **ID Strategy**: ULID or UUID for all canonical entities
- **FSMs**: 10 universal finite-state machines (see [docs/domain/fsm-catalogue.md](../../docs/domain/fsm-catalogue.md))
- **Danger Archetypes**: 4 categories (Ambiguity, Adversarial,
  Irreversibility, Institutional)

Changes to these require architectural review and MAJOR version bump
if incompatible.

## Quality Gates

All contributions MUST satisfy the following gates before merge:

1. **Linting**: All source code passes configured linters (Python:
   ruff/mypy; Bash: shellcheck; Markdown: markdownlint or
   equivalent).
2. **Test Suite**: Full test suite passes with no regressions.
3. **Consistency Analysis**: `speckit.analyze` MUST be run on any
   modified specs/plans and report no blocking issues.
4. **Constitution Compliance**: All PRs and reviews MUST verify the
   change does not violate any Core Principle.
5. **Documentation**: Code changes MUST include corresponding
   documentation updates where behavior changes.
6. **Recipe Verification**: Any new or modified recipe MUST include
   at least one challenge-case test demonstrating correctness.
7. **Schema Validation**: Changes to canonical schema MUST include
   migration path, version bump, and backward compatibility analysis.
8. **Provenance Check**: All new data sources MUST include license
   information and attribution.
9. **Privacy Review**: Traces containing PII MUST be flagged and
   handled according to sensitivity policy.
10. **Performance Regression**: Pattern retrieval and routing MUST
    maintain sub-200ms latency (excluding embedding generation).
11. **Benchmark Validation**: Changes to routing, FSM, or danger
    classification MUST be validated on benchmark suite before merge.

## Development Workflow

All feature development follows the Speckit workflow:

1. **Branch Naming**: Feature branches MUST follow `###-feature-name`
   pattern (e.g., `001-build-recipe-engine`).
2. **Spec-First**: Every feature MUST begin with a specification
   (`speckit.specify`) before any implementation.
3. **Phase Discipline**: The workflow phases—specify → clarify →
   plan → tasks → implement → analyze—MUST NOT be skipped. Each
   phase produces artifacts that the next phase depends on.
4. **Artifact Immutability**: Feature spec directories (`specs/###-*`)
   are the source of truth for feature history and MUST NOT be
   deleted.
5. **Primary Language**: Python 3.11+ is the primary implementation
   language for all Grimoire components.
6. **Simplicity**: Start with the simplest viable implementation.
   Complexity MUST be justified via the Complexity Tracking section
   in plan.md. YAGNI applies by default.

## Governance

This constitution is the supreme governance document for the Grimoire
project. It supersedes all other practices, conventions, and ad-hoc
decisions.

**Amendment Procedure**:
1. Propose amendment via `speckit.constitution` with rationale.
2. Run `speckit.analyze` to verify impact on existing specs/plans.
3. Version bump follows semantic versioning (see below).
4. All existing features MUST be checked for compliance with amended
   principles within one release cycle.

**Versioning Policy**:
- MAJOR: Backward-incompatible principle removals or redefinitions.
- MINOR: New principle or section added, or material expansion of
  existing guidance.
- PATCH: Clarifications, wording fixes, non-semantic refinements.

**Compliance Review**:
- Every PR review MUST include a constitution compliance check.
- `speckit.analyze` validates spec/plan alignment with this document.
- Violations MUST be resolved before merge; no exceptions.

**Version**: 1.1.0 | **Ratified**: 2026-02-11 | **Last Amended**: 2026-02-12
