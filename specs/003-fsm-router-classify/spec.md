# Feature Spec: FSM Router (003)

**Feature Branch**: `003-fsm-router-classify`  
**Status**: Specification Phase  
**Reference Implementation**: [docs/reference/fsm-router-impl.md](../../docs/reference/fsm-router-impl.md)

## User Stories

### Story 1 - Classify Problem Type: Debugging Task (P1)

**As** a developer working on a defect resolution task  
**I want** the system to recognize that I'm diagnosing a bug  
**So that** the reasoning process applies debugging-specific steps (root cause analysis, fix verification)

**Why this priority**: Debugging is the most common reasoning task (30%+ of traces); must work correctly first.

**Independent Test**: Route 10 debugging-related problems; verify 90%+ route to fsm_diagnose_fix with confidence ≥ 0.7.

**Acceptance Scenarios**:

1. **Given** problem: "Why do database queries timeout under load?", **When** submitted to FSM Router, **Then** selected_fsm_id is `fsm_diagnose_fix` with confidence ≥ 0.7
2. **Given** problem: "Fix the cache invalidation bug", **When** submitted, **Then** selected_fsm_id is `fsm_diagnose_fix` with confidence ≥ 0.8
3. **Given** problem: "Why does role-based access fail on first login?", **When** submitted, **Then** selected_fsm_id is `fsm_diagnose_fix` with confidence ≥ 0.75

**Evidence Reasoning**: Keywords "why", "timeout", "bug", "root cause" → fsm_diagnose_fix

---

### Story 2 - Classify Problem Type: Design Task (P1)

**As** an architect designing a new system component  
**I want** the system to identify design/decision-making problems  
**So that** the reasoning explores alternatives and evaluates trade-offs

**Why this priority**: Design decisions are high-impact and require structured exploration; must route correctly.

**Independent Test**: Route 10 design-related problems; verify 85%+ route to fsm_design_decide with confidence ≥ 0.7.

**Acceptance Scenarios**:

1. **Given** problem: "How should we architect the real-time event bus — Kafka vs RabbitMQ?", **When** submitted, **Then** selected_fsm_id is `fsm_design_decide` with confidence ≥ 0.7
2. **Given** problem: "Design a caching strategy for user sessions", **When** submitted, **Then** selected_fsm_id is `fsm_design_decide` with confidence ≥ 0.8
3. **Given** problem: "Should we migrate to a new framework?", **When** submitted, **Then** selected_fsm_id is `fsm_design_decide` with confidence ≥ 0.75

**Evidence Reasoning**: Keywords "architect", "design", "choose", "compare", "alternatives" → fsm_design_decide

---

### Story 3 - Classify Problem Type: Optimization Task (P1)

**As** a performance engineer  
**I want** the system to identify optimization problems  
**So that** the reasoning applies iterative tuning (measure, adjust, re-measure) to improve KPIs

**Why this priority**: Optimization has specific methodology; misrouting wastes effort.

**Independent Test**: Route 10 optimization-related problems; verify 85%+ route to fsm_optimize with confidence ≥ 0.7.

**Acceptance Scenarios**:

1. **Given** problem: "Reduce API response latency from 500ms to 100ms", **When** submitted, **Then** selected_fsm_id is `fsm_optimize` with confidence ≥ 0.7
2. **Given** problem: "Improve throughput of the batch processor", **When** submitted, **Then** selected_fsm_id is `fsm_optimize` with confidence ≥ 0.8

---

### Story 4 - Classify Problem Type: Verification Task (P1)

**As** a QA engineer  
**I want** the system to identify verification/testing problems  
**So that** the reasoning applies testing strategies (hypothesis, test, confirm)

**Why this priority**: Verification has distinct approach; needs correct FSM routing to be effective.

**Independent Test**: Route 8 verification-related problems; verify 80%+ route to fsm_verify with confidence ≥ 0.6.

**Acceptance Scenarios**:

1. **Given** problem: "Verify that the new auth flow works across all browsers", **When** submitted, **Then** selected_fsm_id is `fsm_verify` with confidence ≥ 0.6
2. **Given** problem: "Test all edge cases of the new payment processor", **When** submitted, **Then** selected_fsm_id is `fsm_verify` with confidence ≥ 0.7

---

### Story 5 - Ambiguous Problem → Default to Clarification (P1)

**As** a project manager with a vague problem statement  
**I want** ambiguous problems to default to clarification FSM  
**So that** the system helps me narrow scope before committing to a strategy

**Why this priority**: Graceful handling of ambiguity prevents wrong strategies; must block clearly.

**Independent Test**: Route 5 vague problems ("improve", "do better", "optimize", etc.); verify all default to fsm_clarify_frame with confidence < 0.5.

**Acceptance Scenarios**:

1. **Given** problem: "Improve the system", **When** submitted, **Then** selected_fsm_id is `fsm_clarify_frame` and confidence < 0.5
2. **Given** problem: "Make things faster", **When** submitted, **Then** selected_fsm_id is `fsm_clarify_frame` and confidence < 0.5 and confidence equals 0.0 (fallback indicator)

---

### Story 6 - Extend FSM Routing: Add Custom Keywords (P2)

**As** a domain expert (security team)  
**I want** to add custom keywords for my domain  
**So that** security-specific problems route to appropriate FSMs without code changes

**Why this priority**: Extensibility enables domain specialists to improve routing; can be done post-MVP.

**Independent Test**: Add keyword "adversarial" to fsm_adversarial_loop in config; restart; route "Defend against adversarial attacks" → verify fsm_adversarial_loop selected.

**Acceptance Scenarios**:

1. **Given** routing_config.yaml with custom keyword "adversarial" added to fsm_adversarial_loop, **When** config reloaded, **Then** problems mentioning "adversarial" route to fsm_adversarial_loop
2. **Given** keyword list updated without code change, **When** system restarted, **Then** new keywords take effect

---

### Story 7 - Multi-FSM Problems: Return Alternatives (P2)

**As** an analyst with a complex problem  
**I want** to see alternative FSM suggestions  
**So that** I understand the system's reasoning and can override if needed

**Why this priority**: Provides transparency & manual override capability; useful for edge cases.

**Independent Test**: Route "Optimize database performance by redesigning schema"; verify primary is fsm_optimize ≥ 0.65, alternative includes fsm_design_decide ≥ 0.60.

**Acceptance Scenarios**:

1. **Given** problem matching multiple FSMs equally well, **When** submitted, **Then** alternative_fsms list includes top 2 alternatives with confidence scores
2. **Given** user sees alternatives, **When** user chooses alternative FSM, **Then** system can override selected_fsm_id to user choice

---

### Story 8 - FSM Routing Performance (P2)

**As** a system operator  
**I want** FSM routing to be fast  
**So that** it doesn't create pipeline bottlenecks

**Why this priority**: Performance enables real-time routing; can be optimized post-MVP if needed.

**Independent Test**: Route 1000 problems in batch; measure P50 and P99 latency.

**Acceptance Scenarios**:

1. **Given** batch of 1000 problem texts, **When** each routed, **Then** P50 latency < 50ms and P99 latency < 100ms
2. **Given** batch of 100 traces, **When** routed, **Then** total batch time < 10 seconds

---

## Functional Requirements

| ID | Requirement | Description |
|----|-------------|-------------|
| FR-001 | Support all 10 FSM types | Must handle CLARIFY_FRAME, DIAGNOSE_FIX, DESIGN_DECIDE, OPTIMIZE, VERIFY, TRANSFORM, OPERATE_HARDEN, POSTMORTEM, RESOLVE_CONFLICT, ADVERSARIAL_LOOP |
| FR-002 | Keyword-based classification | Regex + keyword matching (v1, rules-based) |
| FR-003 | Confidence scoring | Return [0, 1] confidence per routing decision |
| FR-004 | Fallback mechanism | Default to clarify_frame if confidence < 0.5 |
| FR-005 | Alternative suggestions | Return top 2-3 alternative FSMs with confidences |
| FR-006 | Config-driven keywords | Load keywords from routing_config.yaml; no code change needed |
| FR-007 | Return reasoning | Explain why this FSM was selected (keywords matched) |
| FR-008 | Graceful degradation | Handle empty/null input without crash; return neutral default |

---

## Non-Functional Requirements

| ID | Requirement | Target |
|----|-------------|--------|
| NFR-001 | Performance | P99 latency < 100ms per route |
| NFR-002 | Accuracy | 80%+ human agreement on test set |
| NFR-003 | Coverage | 90%+ non-default routing on real problems |
| NFR-004 | Error Resilience | Crash → graceful degradation (return default FSM) |
| NFR-005 | Configurability | Hot-load config without restart; updates take effect immediately |
| NFR-006 | Code Coverage | 90%+ test coverage |
| NFR-007 | Observability | Log each routing decision + keywords matched + confidence |

---

## Integration Points

- **Input (Phase 1)**: Consumes `TraceBundle.problem` text
- **Output (Phase 2.3)**: FSM type consumed by `TransitionGuards` for context-appropriate safety gates
- **Parallel**: Independent from Danger Classifier; can work in parallel
- **Future (Phase 3)**: Danger scores can refine confidence in advanced routing (Phase 3 optimization)

---

## Success Criteria

- [ ] All 8 user stories independently testable and passing
- [ ] 90%+ of common problem types routed without defaulting (confidence ≥ 0.5)
- [ ] 80%+ human agreement on evaluation set (20 representative problems reviewed by domain experts)
- [ ] P99 latency < 100ms on 1000-trace batch
- [ ] Keyword patterns cover all problem domains in Phase 1 data
- [ ] Config-driven keywords easy to update (no code recompilation)
- [ ] Zero unhandled exceptions (100% graceful degradation)

---

## See Also

- [plan.md](plan.md) — Implementation design
- [data-model.md](data-model.md) — Pydantic v2 schemas
- [contracts/fsm-router-api.md](contracts/fsm-router-api.md) — API contract
- [docs/domain/fsm-catalogue.md](../../docs/domain/fsm-catalogue.md) — FSM documentation

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
