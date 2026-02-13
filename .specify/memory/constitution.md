<!--
  Sync Impact Report
  ===================
  Version change: 1.2.0 → 1.2.1 (patch update - added Z3 SMT solver for formal verification and everyday reasoning)

  Added capabilities:
    - Z3 SMT Solver added to Technical Stack as verification tool
    - Principle II enhanced to include formal verification via Z3 for pattern correctness
    - Z3 can prove constraint satisfaction (FSM invariants, guard conditions, control flow safety)
    - **Vision**: Z3 enables verification of reasoning patterns covering ~80% of 80% of people's daily problem-solving needs
      (deduction, induction, constraint satisfaction across mathematics, programs, protocols, systems, invariants)

  Modified sections:
    - Principle II (Verification Before Learning): Added Z3 as formal verification mechanism + everyday reasoning rationale
    - Technical Stack: Added "Verification Tools: Z3 SMT Solver" with vision statement and capabilities

  Removed sections: None

  Previous version summary (v1.2.0):
    - Added Principles XI (Domain Knowledge Foundation) and XII (Operational Specifications)
    - Comprehensive docs/ integration (23 files referenced)
    - 40+ cross-references to domain knowledge, architecture, and operational specs

  Impact on templates: None (Z3 is optional verification tool, not a requirement)

  Follow-up TODOs:
    - Document Z3 verification patterns for FSM state invariants
    - Create Z3 proof templates for common guard conditions and everyday reasoning patterns
    - Integrate Z3 verification into pattern promotion pipeline (optional gate)
    - Add Z3 verification examples to pattern extraction spec (005)
    - Catalog common reasoning patterns (80/80 target) that Z3 can verify
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
  tests, mathematical substitution, output validation, formal
  verification (Z3 SMT solver), or equivalent evidence.
- Every outcome that feeds into recipe improvement MUST have a
  verification trace logged alongside it.
- Unverified outputs MUST NOT update recipe confidence scores,
  propose recipe amendments, or enter shared memory.
- Verification failures MUST be logged with sufficient context for
  post-mortem analysis.
- **For pattern correctness**: Z3 MAY be used to prove constraint
  satisfaction (e.g., FSM state invariants, guard conditions, control
  flow safety bounds). When Z3 provides a proof, the pattern is
  considered formally verified.
- **Z3 for Everyday Reasoning**: Z3's SMT capabilities (deduction,
  induction, constraint satisfaction) enable verification of reasoning
  patterns that address ~80% of 80% of daily problem-solving needs.
  This includes: mathematical proofs, program correctness, protocol
  verification, system invariants, and logical consistency checks.

**Rationale**: A system that learns from hallucinations compounds
errors exponentially. Verification is the only defense against
reasoning drift. Formal verification via Z3 provides mathematical
guarantees for critical patterns.

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

## XI. Domain Knowledge Foundation

The system MUST be grounded in explicit, documented domain knowledge. All reasoning patterns and FSMs are derived from permanent, authoritative domain specifications.

Non-negotiable rules:

- Domain knowledge is codified in `docs/domain/` and MUST be treated as canonical.
- All recipes MUST reference the problem archetypes they address.
- All routing decisions MUST align with the 10 universal FSMs.
- Danger classification MUST apply the 4 danger archetypes.
- Control patterns MUST conform to the control pattern taxonomy.
- Unknown problem types MUST escalate to human review; the system MUST NOT invent new FSMs.

**Domain Specifications** (authoritative sources):

- **15 Problem Archetypes** ([docs/domain/problem-archetypes.md](../../docs/domain/problem-archetypes.md)): Diagnosis, Design, Decision, Explanation, Allocation, Constraint Satisfaction, Search, Transformation, Integration, Analysis, Meta-Process, Ambiguity Resolution, Adversarial/Strategic, Failure Prevention, Failure Recovery
- **10 Universal FSMs** ([docs/domain/fsm-catalogue.md](../../docs/domain/fsm-catalogue.md)): Clarify-Frame, Diagnose-Fix, Design-Build, Decide-Execute, Optimize-Iterate (primary). Secondary/specialized: Perform-Verify, Harmonize, Recovery, Tradeoff, Strategic.
- **4 Danger Archetypes** ([docs/domain/danger-classification.md](../../docs/domain/danger-classification.md)): Ambiguity, Adversarial Intent, Irreversibility, Institutional Constraints
- **Control Pattern Taxonomy** ([docs/domain/control-pattern-taxonomy.md](../../docs/domain/control-pattern-taxonomy.md)): 10 pattern groups → 6 primitives with formal algebra (if/else, for/while, counter, percentage, switch, try/catch)

**Rationale**: Codified domain knowledge is the foundation for reproducible routing and pattern extraction. Without it, the system devolves into ad-hoc reasoning.

---

## XII. Operational Specifications

All Grimoire services MUST implement the following cross-cutting operational specifications. These are not optional and apply to all features (001-008).

**Operational Specifications** (authoritative sources):

- **Multi-Tenancy** ([docs/operations/MULTI_TENANCY_SPECIFICATION.md](../../docs/operations/MULTI_TENANCY_SPECIFICATION.md)): Tenant isolation, schema/collection-prefix strategies, rate limiting (Principle VII extended)
- **API Versioning** ([docs/operations/API_VERSIONING_SPECIFICATION.md](../../docs/operations/API_VERSIONING_SPECIFICATION.md)): URL versioning, deprecation policy (6-month minimum), backward compatibility rules
- **Authentication & Authorization** ([docs/operations/AUTHENTICATION_SPECIFICATION.md](../../docs/operations/AUTHENTICATION_SPECIFICATION.md)): API key + JWT hybrid (MVP); OAuth2 + mTLS (production); service-to-service auth
- **Data Export/Import** ([docs/operations/DATA_EXPORT_IMPORT_SPECIFICATION.md](../../docs/operations/DATA_EXPORT_IMPORT_SPECIFICATION.md)): JSON/CSV/RDF formats, bulk import with validation, GDPR right-to-be-forgotten (Principle VIII extended)
- **Control Flow** ([docs/operations/CONTROL_FLOW_SPECIFICATION.md](../../docs/operations/CONTROL_FLOW_SPECIFICATION.md)): Primitives (if/else, loops, counters), pattern detection, loop enforcement with safety bounds
- **Disaster Recovery** ([docs/operations/DISASTER_RECOVERY_SPECIFICATION.md](../../docs/operations/DISASTER_RECOVERY_SPECIFICATION.md)): RTO/RPO targets, backup/restore procedures, failure scenarios
- **Neo4j Migration** ([docs/operations/NEO4J_MIGRATION_GUIDE.md](../../docs/operations/NEO4J_MIGRATION_GUIDE.md)): Schema migration path, backward compatibility, version pinning
- **Integration Test Strategy** ([docs/operations/INTEGRATION_TEST_STRATEGY.md](../../docs/operations/INTEGRATION_TEST_STRATEGY.md)): Comprehensive testing framework for all 001-008 features

Non-negotiable rules:

- All services MUST implement multi-tenancy isolation per spec.
- All APIs MUST version endpoints and maintain backward compatibility per spec.
- All authentication MUST follow the hybrid model (API key + JWT).
- All data exports MUST support the three required formats (JSON/CSV/RDF).
- All control flows MUST use the 6 primitives and include loop safety bounds.
- Disaster recovery procedures MUST be tested quarterly.
- Schema migrations MUST be versioned and tested before deployment.
- Integration tests MUST validate all feature interactions per strategy.

**Rationale**: Distributed systems require consistent operational discipline. Codified specifications ensure all features cooperate without edge cases.

---

## Technical Stack

The following technical decisions are architectural constraints:

- **Primary Language**: Python 3.11+
- **Schema Framework**: Pydantic >= 2 (NON-NEGOTIABLE; see Principle VI)
- **Graph Database**: Neo4j 5.x (or compatible property graph DB per migration guide)
- **Vector Database**: Qdrant >= 1.7 (or compatible with payload filtering)
- **Embedding Models**: Configurable; version tracking REQUIRED; reproducibility MUST be ensured across model updates
- **Verification Tools**: Z3 SMT Solver (for formal verification of pattern correctness and constraint satisfaction)
  - **Z3 Vision**: SMT solving enables deductive, inductive, and constraint-based reasoning that addresses ~80% of 80% of people's daily problem-solving needs (mathematics, programs, protocols, systems, invariants)
  - Z3 provides guarantees: proves whether constraints are consistent, produces concrete models when satisfiable, proves unsatisfiability when no solution exists
  - Theories supported: integers, reals, bit-vectors, arrays, sets, algebraic data types, uninterpreted functions, quantifiers (∀, ∃)
- **ID Strategy**: ULID or ULID-like (composite: deterministic base + UUID suffix for dedup)
- **Text Storage**: S3/GCS for externalized markdown with versioning
- **FSM Architecture**: 10 universal FSMs (see Principle XI)
- **Pattern Taxonomy**: 6 control flow primitives + 10 pattern groups (see Principle XI)
- **Problem Classification**: 15 archetypes → 10 FSMs (see Principle XI)
- **Danger Classification**: 4 archetypes with scoring (see Principle XI)
- **Canonical Data Model** ([docs/reference/canonical-schemas.md](../../docs/reference/canonical-schemas.md)): Trace, Step, Edge, Artifact, Pattern, Goal, Recipe with full Pydantic v2 validation
- **Storage Mapping** ([docs/reference/storage-mapping.md](../../docs/reference/storage-mapping.md)): 1:1 mapping between canonical schema and Neo4j/Qdrant formats

Changes to these require architectural review and MAJOR version bump if incompatible.

## Quality Gates

All contributions MUST satisfy the following gates before merge:

1. **Linting**: All source code passes configured linters (Python: ruff/mypy; Bash: shellcheck; Markdown: markdownlint).
2. **Test Suite**: Full test suite passes per integration test strategy (see Principle XII).
3. **Consistency Analysis**: `speckit.analyze` MUST be run on any modified specs/plans and report no blocking issues.
4. **Constitution Compliance**: All PRs and reviews MUST verify the change does not violate any Core Principle (I–XII).
5. **Domain Knowledge Alignment**: All routing and pattern logic MUST reference appropriate problem archetype, FSM, and danger classification (Principle XI).
6. **Operational Spec Compliance**: Features MUST implement required operational specs: multi-tenancy, API versioning, auth, export/import, control flow bounds (Principle XII).
7. **Documentation**: Code changes MUST include corresponding documentation updates where behavior changes.
8. **Recipe Verification**: Any new or modified recipe MUST include at least one challenge-case test demonstrating correctness.
9. **Schema Validation**: Changes to canonical schema MUST include migration path, version bump, and backward compatibility analysis (Principle VI).
10. **Provenance Check**: All new data sources MUST include license information and attribution (Principle VIII).
11. **Privacy Review**: Traces containing PII MUST be flagged and handled according to sensitivity policy (Principle IX).
12. **Performance Regression**: Pattern retrieval and routing MUST maintain sub-200ms latency excluding embedding generation (per SC-004).
13. **Benchmark Validation**: Changes to routing, FSM, or danger classification MUST be validated on benchmark suite before merge (Principle X).
14. **Integration Test Coverage**: All feature interactions validated per campaign strategy ([docs/operations/INTEGRATION_TEST_STRATEGY.md](../../docs/operations/INTEGRATION_TEST_STRATEGY.md)).

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
7. **Documentation Integration**: All specs MUST cross-reference applicable docs/ files (see Reference Documentation below).

---

## Reference Documentation

This constitution is grounded in the following authoritative specifications and domain knowledge documents. All feature teams MUST familiarize themselves with these before design work.

### Vision & Strategy

- [System Specification](../../docs/vision/spec.md) — High-level system overview
- [System Architecture](../../docs/architecture/system-architecture.md) — Component diagram and data flows
- [Build Plan](../../docs/architecture/build-plan.md) — Phased implementation roadmap (Phase 0–6)
- [Capability Requirements](../../docs/architecture/capability-requirements.md) — 9 capability areas, 95% checklist

### Domain Knowledge (Principle XI)

- [Problem Archetypes](../../docs/domain/problem-archetypes.md) — 15 problem types + canonical steps
- [FSM Catalogue](../../docs/domain/fsm-catalogue.md) — 10 universal FSMs with state vocabulary
- [Danger Classification](../../docs/domain/danger-classification.md) — 4 danger archetypes + scoring model
- [Control Pattern Taxonomy](../../docs/domain/control-pattern-taxonomy.md) — 10 pattern groups → 6 primitives + algebra

### Data & Storage (Principles VI, VII)

- [Canonical Schemas](../../docs/reference/canonical-schemas.md) — Pydantic v2 models (Trace, Step, Edge, Pattern, Artifact)
- [Storage Mapping](../../docs/reference/storage-mapping.md) — Neo4j property graph + Qdrant payload mapping
- [Qdrant Setup](../../docs/reference/qdrant-setup.md) — Collection schemas and payload indexes

### Implementation Reference

- [Pattern Detection & Pipeline](../../docs/reference/pattern-detection-and-pipeline.md) — Pattern mining algorithms + corpus aggregation
- [Danger Classification Impl](../../docs/reference/danger-classification-impl.md) — Regex + probe classifier with FSM guards

### Operational Specifications (Principle XII)

- [Multi-Tenancy Specification](../../docs/operations/MULTI_TENANCY_SPECIFICATION.md) — Tenant isolation, rate limiting
- [API Versioning Specification](../../docs/operations/API_VERSIONING_SPECIFICATION.md) — URL versioning, deprecation policy
- [Authentication & Authorization](../../docs/operations/AUTHENTICATION_SPECIFICATION.md) — JWT/OAuth2, RBAC, audit trail
- [Data Export/Import Specification](../../docs/operations/DATA_EXPORT_IMPORT_SPECIFICATION.md) — JSON/CSV/RDF formats, GDPR compliance
- [Control Flow Specification](../../docs/operations/CONTROL_FLOW_SPECIFICATION.md) — Primitives, detection, loop enforcement
- [Integration Test Strategy](../../docs/operations/INTEGRATION_TEST_STRATEGY.md) — Test framework for all 001-008 features
- [Disaster Recovery Specification](../../docs/operations/DISASTER_RECOVERY_SPECIFICATION.md) — RTO/RPO, backup/restore
- [Neo4j Migration Guide](../../docs/operations/NEO4J_MIGRATION_GUIDE.md) — Schema migration + version pinning

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

**Version**: 1.2.0 | **Ratified**: 2026-02-11 | **Last Amended**: 2026-02-13

**Changelog (1.1.0 → 1.2.0)**:

- Added Principle XI: Domain Knowledge Foundation
- Added Principle XII: Operational Specifications
- Expanded Technical Stack with explicit data model and storage references
- Added Quality Gate 5-6 for domain and operational spec compliance
- Added comprehensive Reference Documentation section as constitution hub
- All 23 docs/ files now codified as authoritative specifications
