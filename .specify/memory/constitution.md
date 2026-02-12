<!--
  Sync Impact Report
  ===================
  Version change: N/A → 1.0.0 (initial creation)

  Added principles:
    - I. Recipe-First Architecture
    - II. Verification Before Learning (NON-NEGOTIABLE)
    - III. Federated Quality Control
    - IV. Exploitation Before Exploration
    - V. Test-First Development (NON-NEGOTIABLE)

  Added sections:
    - Core Principles (5 principles)
    - Quality Gates
    - Development Workflow
    - Governance

  Removed sections: N/A (initial creation)

  Templates requiring updates:
    ✅ .specify/templates/plan-template.md
       — No changes needed; Constitution Check section dynamically
         reads gates from this file at plan time
    ✅ .specify/templates/spec-template.md
       — No changes needed; scope/requirements sections compatible
    ✅ .specify/templates/tasks-template.md
       — No changes needed; task phases align with test-first and
         quality gate principles
    ✅ .specify/templates/checklist-template.md
       — No changes needed; generic template compatible
    ✅ .specify/templates/commands/*.md
       — Directory does not exist; N/A

  Follow-up TODOs: None
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

**Version**: 1.0.0 | **Ratified**: 2026-02-11 | **Last Amended**: 2026-02-11
