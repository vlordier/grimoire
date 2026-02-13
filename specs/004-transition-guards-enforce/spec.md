# Feature Spec: Transition Guards (004)

**Feature Branch**: `004-transition-guards-enforce`  
**Status**: Specification Phase

---

## 📚 Reference Documentation

**Prerequisites**: [Feature 001: Canonical Schema](../001-canonical-schema-implementation/), [Feature 003: FSM Router](../003-fsm-router-classify/) — Reads FSM state + enforces transitions

**See Also:**

- [Build Plan](../../docs/architecture/build-plan.md) — Phase 2 context (guards enforcement)
- [System Architecture](../../docs/architecture/system-architecture.md) — Guards in control plane
- [FSM Catalogue](../../docs/domain/fsm-catalogue.md) — FSM transition rules + guards
- [Danger Classification](../../docs/domain/danger-classification.md) — Danger signals influencing guard decisions
- [Problem Archetypes](../../docs/domain/problem-archetypes.md) — Problem context for guard logic
- **Related**: Feature 002 (Danger Router), Feature 003 (FSM Router)  
**Reference Implementation**: [docs/reference/danger-classification-impl.md](../../docs/reference/danger-classification-impl.md)

---

## User Stories

### Story 1 - Guard: NO_EXECUTE_AMBIGUOUS (P1)

**As** a problem owner  
**I want** the system to block execution when a problem is ambiguous (high ambiguity score)  
**So that** I don't waste effort solving the wrong problem

**Why this priority**: Prevents highest-risk failure mode (solving problem that wasn't clearly defined).

**Independent Test**: Create step with ambiguity_score ≥ 0.7 and role="execute"; verify guard blocks transition.

**Acceptance Scenarios**:

1. **Given** step with ambiguity_score = 0.75, **When** transition to role="execute", **Then** guard blocks with reason "Ambiguity ≥ 0.7; clarify first"
2. **Given** step with ambiguity_score = 0.4, **When** transition to role="execute", **Then** guard allows

---

### Story 2 - Guard: NO_IRREVERSIBLE_UNVERIFIED (P1)

**As** a tech lead  
**I want** the system to block irreversible actions (deploy, delete) without verification  
**So that** destructive changes don't slip through unverified

**Why this priority**: Prevents data loss and production incidents; critical safety barrier.

**Independent Test**: Create step with irreversibility_score ≥ 0.7 and role="execute"; verify requires preceding VERIFICATION step.

**Acceptance Scenarios**:

1. **Given** step with irreversibility_score = 0.9 without prior VERIFICATION, **When** transition to role="execute", **Then** guard blocks
2. **Given** step with irreversibility_score = 0.9 WITH prior verified step, **When** transition to role="execute", **Then** guard allows

---

### Story 3 - Guard: ADVERSARIAL_REQUIRES_MONITORING (P2)

**As** a security manager  
**I want** adversarial/attacking problems (security-focused) to require monitoring closure  
**So that** defensive decisions are tracked and validated

**Why this priority**: Tracking + transparency for security decisions; improves audit trail.

**Independent Test**: Create adversarial problem (score ≥ 0.6); verify escalation flag set for monitoring team.

**Acceptance Scenarios**:

1. **Given** step with adversarial_score = 0.75, **When** transition to role="execute", **Then** decision type is ESCALATE with monitoring path

---

### Story 4 - Guard: INSTITUTIONAL_REQUIRES_STAKEHOLDERS (P2)

**As** a governance officer  
**I want** institutional risk decisions (hiring, firing, policy changes) to require stakeholder approval  
**So that** organizational decisions undergo proper review

**Why this priority**: Governance compliance; prevents unilateral high-impact decisions.

**Independent Test**: Create institutional problem (score ≥ 0.6); verify escalation to stakeholder approval workflow.

**Acceptance Scenarios**:

1. **Given** step with institutional_score = 0.8, **When** transition to role="execute", **Then** decision type is ESCALATE with stakeholder_path

---

### Story 5 - Aggregated Guard Decision (P1)

**As** a developer integrating guards  
**I want** to get a single aggregated guard decision per transition  
**So that** I don't have to implement guard logic myself

**Why this priority**: Simplifies downstream integration; single decision point.

**Independent Test**: Call guard orchestrator with multiple danger scores; verify single aggregated decision returned.

**Acceptance Scenarios**:

1. **Given** 2 guards would block (ambiguity & irreversibility), **When** check_transition called, **Then** response.allowed = False and reason lists all blockers

---

### Story 6 - Guard Logging & Audit Trail (P2)

**As** a compliance officer  
**I want** all guard decisions logged for audit  
**So that** decisions can be reviewed and justified when needed

**Why this priority**: Compliance + debugging; should happen after core guards work.

**Independent Test**: Create blocked transition; verify audit log entry with timestamp, step_id, guard_name, reason, user_id.

**Acceptance Scenarios**:

1. **Given** step blocked by guard, **When** guard check completes, **Then** audit log contains entry with: step_id, guard_name, decision, reason, blocked_reason if applicable

---

## Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| FR-001 | 4 Guards Implemented | NO_EXECUTE_AMBIGUOUS, NO_IRREVERSIBLE_UNVERIFIED, ADVERSARIAL_REQUIRES_MONITORING, INSTITUTIONAL_REQUIRES_STAKEHOLDERS |
| FR-002 | Read Danger Scores | Consume DangerScores from Phase 2.1 |
| FR-003 | Aggregated Decision | Single response per transition (allowed: bool, reason: str, escalations: list) |
| FR-004 | Blocking Decision | blocked step can be retried after condition cleared (e.g., ambiguity lowered) |
| FR-005 | Escalation Path | Escalated steps routed to monitoring/stakeholder systems |
| FR-006 | FSM Context Optional | Guards work with or without FSM type from Phase 2.2 |
| FR-007 | Graceful Degradation | If danger scores missing, skip guard (allow transition) |

---

## Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Performance | < 50ms per guard check |
| NFR-002 | Availability | 99.9% uptime during business hours |
| NFR-003 | Auditability | All decisions logged with reason + timestamp |
| NFR-004 | Clarity | Guard reason messages human-readable + actionable |

---

## Integration Points

- **Input (Phase 2.1)**: DangerScores from classifier
- **Input (Phase 2.2)**: FSM type selection (optional enhancement)
- **Output**: GuardDecision (allowed/blocked/escalated) → Step creation proceeds or is blocked
- **Logging**: All decisions to audit trail for compliance

---

## Success Criteria

- [ ] All 4 guards implemented and testable
- [ ] Aggregated decision logic correct (multiple blocking guards handled)
- [ ] 100% of dangerous transitions blocked when scores exceed thresholds
- [ ] Zero false positives (legitimate transitions allowed)
- [ ] Performance < 50ms per check
- [ ] Audit log contains 100% of decisions
- [ ] Phase 1 integration: guards work with real ingested traces

---

## See Also

- [plan.md](plan.md) — Implementation design
- [data-model.md](data-model.md) — Pydantic v2 schemas
- [docs/reference/danger-classification-impl.md](../../docs/reference/danger-classification-impl.md) — Reference guards implementation

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
