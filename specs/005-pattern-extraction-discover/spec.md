# Feature Spec: Pattern Extraction (005)

**Feature Branch**: `005-pattern-extraction-discover`  
**Phase**: 3.1 — Pattern Discovery  
**Status**: Specification Phase  
**Effort**: 8-12 days

---

## 📚 Reference Documentation

**Prerequisites**: [Feature 001: Canonical Schema](../001-canonical-schema-implementation/), [Feature 003: FSM Router](../003-fsm-router-classify/) — Reads ingested traces + FSM context

**See Also:**

- [Build Plan](../../docs/architecture/build-plan.md) — Phase 3 context (pattern discovery)
- [System Architecture](../../docs/architecture/system-architecture.md) — Pattern extraction in learn plane
- [Pattern Detection & Pipeline](../../docs/reference/pattern-detection-and-pipeline.md) — Algorithm, motif mining, corpus aggregation
- [Control Pattern Taxonomy](../../docs/domain/control-pattern-taxonomy.md) — Pattern primitives + algebra
- [FSM Catalogue](../../docs/domain/fsm-catalogue.md) — FSM context for patterns
- [Control Flow Specification](../../docs/operations/CONTROL_FLOW_SPECIFICATION.md) — Control flow patterns (Parts 5-8)
- **Feeds into**: Feature 006 (Pattern Ranking)

---

## Overview

Pattern Extraction discovers recurring solution patterns from historical reasoning traces. It identifies: which steps work well together, what problems they solve, how frequently they succeed.

**Goal**: Extract 50+ distinct patterns from Phase 1 data as foundation for ranking + optimization.

---

## User Stories

### Story 1 (P1): Extract Basic Patterns — Debugging Sequences

**As** an optimization engineer  
**I want** to identify common debugging sequences from historical traces  
**So that** I can recommend proven solutions for similar future problems

**Why P1**: Debugging is most common; MVP must handle this first.

**Independent Test**: Run extraction on 100 diagnose_fix traces; get 5+ patterns with >80% success rate.

**Acceptance Scenarios**:

1. **Given** 100 debugging traces, **When** extraction runs, **Then** patterns like "ROOT_CAUSE_ANALYSIS → FIX → VERIFY" extracted with success_rate ≥ 0.85
2. **Given** extracted pattern, **When** inspected, **Then** has avg_time_to_solution, cost, confidence metrics

---

### Story 2 (P1): Deduplicate Patterns — Merge Exact & Fuzzy

**As** a pattern curator  
**I want** duplicate patterns removed and similar ones merged  
**So that** recommendations are clean (no redundant suggestions)

**Why P1**: Prevents polluting pattern database with near-duplicates.

**Independent Test**: Given 20 patterns with >80% similarity, verify they merge into 1 canonical pattern.

**Acceptance Scenarios**:

1. **Given** two patterns with identical step sequences, **When** deduplication runs, **Then** merged into one with combined usage statistics
2. **Given** two patterns 85% similar (fuzzy match), **When** processed, **Then** merged with confidence=0.85

---

### Story 3 (P1): Pattern Metadata — FSM + Keywords + Danger

**As** a ranking engineer  
**I want** patterns tagged with metadata (FSM, keywords, danger profile)  
**So that** I can filter/rank patterns intelligently

**Why P1**: Metadata enables Phase 3.2 (ranking) to work. Core requirement.

**Independent Test**: Extract 10 patterns; verify each has FSM type, 3+ keywords, danger profile.

**Acceptance Scenarios**:

1. **Given** extracted pattern, **When** metadata extraction runs, **Then** pattern has fsm_type = "fsm_diagnose_fix", keywords ≥ 3, danger_profile populated
2. **Given** danger profile extracted, **Then** all 4 danger types (ambiguity, adversarial, irrev, institutional) have [min, max] ranges

---

### Story 4 (P1): Performance — <30ms Per Trace Extraction

**As** a devops engineer  
**I want** extraction to be fast enough to re-run daily or weekly  
**So that** I can keep patterns up-to-date with new incoming data

**Why P1**: Scalability + maintainability. Can't run nightly if too slow.

**Independent Test**: Extract 1000 traces batch; P99 latency <30ms per trace.

**Acceptance Scenarios**:

1. **Given** 1000 traces queued, **When** batch extraction runs in parallel, **Then** P50 <20ms, P99 <30ms per trace
2. **Given** extraction profile, **Then** memory usage <5GB (scalable to millions)

---

### Story 5 (P2): Pattern Clustering — Semantic Grouping

**As** a data scientist  
**I want** patterns automatically clustered by similarity  
**So that** duplicate work is minimized

**Why P2**: Nice-to-have; deduplication may be sufficient for MVP.

**Independent Test**: Extract 100 patterns; cluster into 15-25 groups (reduce from 100 to canonical patterns).

**Acceptance Scenarios**:

1. **Given** 100 patterns extracted, **When** clustering runs, **Then** reduce to 20-30 canonical patterns per FSM type

---

## Functional Requirements

| ID | Requirement |
|----|-------------|
| FR-001 | Extract step sequences from traces (subgraph matching neo4j) |
| FR-002 | Compute effectiveness (success_rate = successes / total_uses) |
| FR-003 | Identify exact duplicates (identical step sequences) |
| FR-004 | Fuzzy-match duplicates (>80% similarity between sequences) |
| FR-005 | Extract metadata (FSM + keywords + danger profile) |
| FR-006 | Store patterns in Neo4j nodes + metadata |
| FR-007 | Create PatternMatch edges (trace → pattern link) |

---

## Success Criteria

- [ ] Extract 50+ distinct patterns from Phase 1 data
- [ ] Deduplication accuracy: 90%+ (near-identical patterns merged)
- [ ] All patterns have metadata (FSM, keywords, danger profile)
- [ ] P99 latency <30ms per trace (scalable to 1M+)
- [ ] Patterns cover all 10 FSM types
- [ ] 0 false positives (pattern actually solves problem)

### User Story 3 - [Brief Title] (Priority: P3)

[Describe this user journey in plain language]

**Why this priority**: [Explain the value and why it has this priority level]

**Independent Test**: [Describe how this can be tested independently]

**Acceptance Scenarios**:

1. **Given** [initial state], **When** [action], **Then** [expected outcome]

---

[Add more user stories as needed, each with an assigned priority]

### Edge Cases

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right edge cases.
-->

- What happens when [boundary condition]?
- How does system handle [error scenario]?

## Requirements *(mandatory)*

<!--
  ACTION REQUIRED: The content in this section represents placeholders.
  Fill them out with the right functional requirements.
-->

### Functional Requirements

- **FR-001**: System MUST [specific capability, e.g., "allow users to create accounts"]
- **FR-002**: System MUST [specific capability, e.g., "validate email addresses"]  
- **FR-003**: Users MUST be able to [key interaction, e.g., "reset their password"]
- **FR-004**: System MUST [data requirement, e.g., "persist user preferences"]
- **FR-005**: System MUST [behavior, e.g., "log all security events"]

*Example of marking unclear requirements:*

- **FR-006**: System MUST authenticate users via [NEEDS CLARIFICATION: auth method not specified - email/password, SSO, OAuth?]
- **FR-007**: System MUST retain user data for [NEEDS CLARIFICATION: retention period not specified]

### Key Entities *(include if feature involves data)*

- **[Entity 1]**: [What it represents, key attributes without implementation]
- **[Entity 2]**: [What it represents, relationships to other entities]

## Success Criteria *(mandatory)*

<!--
  ACTION REQUIRED: Define measurable success criteria.
  These must be technology-agnostic and measurable.
-->

### Measurable Outcomes

- **SC-001**: [Measurable metric, e.g., "Users can complete account creation in under 2 minutes"]
- **SC-002**: [Measurable metric, e.g., "System handles 1000 concurrent users without degradation"]
- **SC-003**: [User satisfaction metric, e.g., "90% of users successfully complete primary task on first attempt"]
- **SC-004**: [Business metric, e.g., "Reduce support tickets related to [X] by 50%"]
