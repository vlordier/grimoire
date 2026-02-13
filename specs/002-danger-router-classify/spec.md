# Feature Specification: Danger Router — Risk Classification & Transition Guards

**Feature Branch**: `002-danger-router-classify`  
**Created**: 12 Feb 2026  
**Status**: Planning  
**Input**: Classify 4 danger archetypes (ambiguity, adversarial, irreversibility, institutional) and enforce safety gates during FSM transitions
**Reference Implementation**: [Danger Classification Impl](../../docs/reference/danger-classification-impl.md)

---

## 📚 Reference Documentation

**Prerequisite**: [Feature 001: Canonical Schema](../001-canonical-schema-implementation/) — Data ingestion foundation

**See Also:**

- [Build Plan](../../docs/architecture/build-plan.md) — Phase 2 context (danger routing + guards)
- [System Architecture](../../docs/architecture/system-architecture.md) — Danger routing in control plane
- [Danger Classification](../../docs/domain/danger-classification.md) — 4 archetypes (ambiguity, adversarial, irreversibility, institutional)
- [Danger Classification Impl](../../docs/reference/danger-classification-impl.md) — Regex + probe classifier algorithm
- [FSM Catalogue](../../docs/domain/fsm-catalogue.md) — FSM routing context (002 complements 003)
- [Problem Archetypes](../../docs/domain/problem-archetypes.md) — Problem types to classify
- **Reinforces**: Feature 003 (FSM Router), Feature 004 (Transition Guards)

## User Scenarios & Testing

### User Story 1 - Classify Ambiguity in Problem Statements (Priority: P1) 🎯 MVP

A safety engineer wants to detect when a problem statement contains unclear requirements or missing constraints so the system can ask clarifying questions before proceeding into execution.

**Why this priority**: Ambiguity is the most common failure mode in reasoning. Without detecting it, the system will make unwarranted assumptions, leading to wasted effort and wrong solutions.

**Independent Test**: Can ingest a trace with an ambiguous problem (e.g., "make the system faster" without defining "faster" metric), and the classifier must detect it with score ≥ 0.7. Conversely, a well-specified problem (with clear metrics + constraints) should score ≤ 0.3.

**Acceptance Scenarios**:

1. **Given** a trace with ambiguous problem text ("Make this faster; it's too slow"), **When** classifier runs, **Then** `danger_ambiguity ≥ 0.7` and evidence spans "faster" + "too slow"
2. **Given** a well-specified problem ("Reduce query latency from 100ms to <50ms"), **When** classifier runs, **Then** `danger_ambiguity ≤ 0.3`
3. **Given** mixed signals (some ambiguous, some clear), **When** classifier runs, **Then** score reflects balance (e.g., 0.4–0.6)

---

### User Story 2 - Detect Adversarial Intent (Priority: P1)

A risk compliance officer wants to automatically flag problems that could have adversarial intent (deception, manipulation, harmful outcomes) so human operators can review them before proceeding.

**Why this priority**: Adversarial reasoning can cause harm. Early detection ensures human oversight on suspicious problems.

**Independent Test**: Can classify traces with adversarial keywords ("bypass", "circumvent", "exploit", "deceive", "attack") and flag them with score ≥ 0.6. Legitimate problem-solving (improvement, optimization, debugging) should score ≤ 0.4.

**Acceptance Scenarios**:

1. **Given** a trace with adversarial language ("how to bypass the security check"), **When** classifier runs, **Then** `danger_adversarial ≥ 0.6`
2. **Given** a legitimate debugging trace, **When** classifier runs, **Then** `danger_adversarial ≤ 0.4`
3. **Given** ambiguous language, **When** classifier runs, **Then** escalate for human review (flag as uncertain)

---

### User Story 3 - Flag Irreversible Actions (Priority: P1)

A developer wants the system to detect when a reasoning chain involves irreversible actions (delete, deploy, commit, fire, shutdown) so verification steps can be required before execution.

**Why this priority**: Irreversible actions are the highest-risk. Without detecting them, a single wrong step could cause unrecoverable damage.

**Independent Test**: Can classify traces containing irreversible verbs ("delete", "deploy production", "commit", "fire employee", "shut down") with score ≥ 0.7, and traces without them score ≤ 0.3.

**Acceptance Scenarios**:

1. **Given** a trace with irreversible actions ("deploy this to production"), **When** classifier runs, **Then** `danger_irreversibility ≥ 0.7` and evidence points to "deploy"
2. **Given** a hypothesis/design trace with no executables ("consider these options"), **When** classifier runs, **Then** `danger_irreversibility ≤ 0.3`
3. **Given** reversible actions only ("add log statement, run test, revert if fails"), **When** classifier runs, **Then** `danger_irreversibility ≤ 0.2`

---

### User Story 4 - Detect Institutional Risk Context (Priority: P2)

A compliance advisor wants to flag problems involving institutional decisions (hiring, firing, policy changes, resource allocation) so proper stakeholder approval flows are triggered.

**Why this priority**: Institutional decisions affect the organization and require governance. P2 because it's lower frequency but high impact.

**Independent Test**: Can classify traces with institutional keywords ("hire", "fire", "budget", "policy", "stakeholder approval", "legal") with score ≥ 0.6, and low-level technical problems without institutional context score ≤ 0.3.

**Acceptance Scenarios**:

1. **Given** a trace about hiring decisions, **When** classifier runs, **Then** `danger_institutional ≥ 0.6`
2. **Given** a technical debugging trace, **When** classifier runs, **Then** `danger_institutional ≤ 0.2`
3. **Given** mixed context (technical + institutional), **When** classifier runs, **Then** score reflects both (e.g., 0.4–0.5)

---

### User Story 5 - Enforce "No Execute While Ambiguous" Guard (Priority: P1)

A safety engineer wants to prevent execution steps when ambiguity is high, forcing clarification first.

**Why this priority**: Executing on ambiguous requirements wastes effort and creates wrong solutions. This is the primary safety gate.

**Independent Test**: When a trace has high ambiguity (≥0.7), system blocks **EXECUTE** steps and suggests QUESTION or PLAN steps instead. When ambiguity is low (≤0.3), EXECUTE is allowed.

**Acceptance Scenarios**:

1. **Given** a trace with `danger_ambiguity = 0.8` and proposed step `role=EXECUTE`, **When** guard checks, **Then** block with reason "Ambiguity too high; clarify requirements first"
2. **Given** `danger_ambiguity = 0.2` and proposed step `role=EXECUTE`, **When** guard checks, **Then** allow execution
3. **Given** `danger_ambiguity = 0.5`, **When** guard checks, **Then** warn but allow with escalation logged

---

### User Story 6 - Enforce "No Irreversible Without Verification" Guard (Priority: P1)

A developer wants to prevent irreversible actions without prior verification steps, ensuring all consequences are understood.

**Why this priority**: Prevents point-of-no-return mistakes. Critical safety gate.

**Independent Test**: When a trace has `danger_irreversibility ≥ 0.7`, system blocks final EXECUTE and requires a VERIFICATION step in the trace immediately before it.

**Acceptance Scenarios**:

1. **Given** `danger_irreversibility = 0.9` and proposed step is `role=EXECUTE` (delete production data), **When** guard checks, **Then** block with reason "Irreversible action requires verification step first"
2. **Given** same trace but with prior `role=VERIFICATION` step ("verified safety checks pass"), **When** guard checks, **Then** allow subsequent EXECUTE
3. **Given** `danger_irreversibility = 0.2`, **When** guard checks, **Then** allow EXECUTE without verification requirement

---

### User Story 7 - Require Monitoring for Adversarial Contexts (Priority: P2)

A risk officer wants adversarial problems to require monitoring/closure steps, ensuring the system doesn't silently succeed in a malicious context.

**Why this priority**: Prevents long-term harm from adversarial reasoning. P2 because it's lower frequency.

**Independent Test**: When `danger_adversarial ≥ 0.6`, system requires a MONITORING or CLOSE step at end of trace.

**Acceptance Scenarios**:

1. **Given** `danger_adversarial = 0.7`, **When** trace is marked as complete, **Then** require evidence of monitoring logs or closure confirmation
2. **Given** `danger_adversarial = 0.2`, **When** trace is complete, **Then** no monitoring requirement

---

### User Story 8 - Flag Institutional Decisions for Stakeholder Approval (Priority: P2)

A compliance officer wants institutional decisions to require stakeholder sign-off before proceeding.

**Why this priority**: Governance requirement. P2 as it's organizational/meta rather than technical.

**Independent Test**: When `danger_institutional ≥ 0.6`, system creates escalation path requiring stakeholder input (logged as Step property).

**Acceptance Scenarios**:

1. **Given** `danger_institutional = 0.8` for a hiring decision, **When** DECISION step proposed, **Then** escalate with stakeholder contact metadata
2. **Given** `danger_institutional = 0.1` for technical debug, **When** DECISION step proposed, **Then** no escalation required

---

## Functional Requirements

- **FR-001**: Classifier must identify 4 danger types independently and return scores [0, 1] for each
- **FR-002**: Classifier must provide evidence spans (text location) supporting each score
- **FR-003**: Danger scores must be monotonic: if more ambiguous keywords added, score increases (never decreases)
- **FR-004**: Guards must read danger scores + FSM state to make allow/block/escalate decisions
- **FR-005**: Blocked transitions must be logged with guard name + reason
- **FR-006**: System must handle missing/empty input gracefully (no crash, return neutral scores)
- **FR-007**: All danger scores must be Pydantic-validated (0 ≤ score ≤ 1.0)

---

## NFRs (Non-Functional Requirements)

- **Performance**: Classifier must complete in < 500ms per trace (single-threaded)
- **Accuracy**: Classifier must agree with human judgment in ≥ 75% of cases (test set TBD)
- **Maintainability**: All keyword lists, thresholds, weights stored in config (not hardcoded)
- **Debuggability**: Classifier must output reasoning trace (which rules fired, which weights applied)
- **Scalability**: Can classify 1000 traces/min on standard hardware

---

## Integration Points

| Component | Direction | Details |
|-----------|-----------|---------|
| **Phase 1: Ingestion** | ← Consumes | TraceBundle (Trace + Steps), normalized traces from Neo4j |
| **Phase 2: FSM Router** | ↔ Bidirectional | FSM state influences guard decisions; guards may suggest FSM change |
| **Phase 2: Guards** | → Produces | Danger scores fed to guard logic; blocked transitions created |
| **Phase 3: Pattern Mining** | → Produces | Danger scores attached to Step embeddings in Qdrant |
| **Phase 3: Recommender** | ← Consumes | Next-step recommendation filters by guard outcomes |

---

## Success Criteria

- [ ] Classifier correctly identifies all 4 danger archetypes in 10+ example traces
- [ ] Danger scores correlate with human risk judgment (Spearman ≥ 0.6)
- [ ] All 4 guards work as specified in reference implementation
- [ ] Classifier integrates with Phase 1 ingestion pipeline (can classify stored traces)
- [ ] System handles edge cases (empty text, mixed language, adversarial examples)
- [ ] Error cases logged cleanly (no exceptions bubble to caller)
- [ ] Documentation includes keyword tuning guide for future maintainers

---

---

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
