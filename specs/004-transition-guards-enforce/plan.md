# Implementation Plan: Transition Guards

**Phase**: 2.3  
**Feature Branch**: `004-transition-guards-enforce`  
**Status**: Planning Phase Complete  
**Effort Estimate**: 3-4 days (~1 week with Phase 2.1 & 2.2 complete)  
**Dependencies**: Phase 2.1 (Danger Classifier) + Phase 2.2 (FSM Router) must be complete first

---

## Overview

Transition Guards enforce 4 safety rules on FSM state transitions using danger scores from Phase 2.1 + optional FSM context from Phase 2.2:

```text
Step Creation Request
    ↓
Extract: danger_scores, fsm_type
    ↓
Check 4 Guards:
  1. NO_EXECUTE_AMBIGUOUS (ambiguity ≥ 0.7 → block execute)
  2. NO_IRREVERSIBLE_UNVERIFIED (irreversibility ≥ 0.7 & no prior verification → block execute)
  3. ADVERSARIAL_REQUIRES_MONITORING (adversarial ≥ 0.6 → escalate for monitoring)
  4. INSTITUTIONAL_REQUIRES_STAKEHOLDERS (institutional ≥ 0.6 → escalate for approval)
    ↓
Aggregated Decision: allowed (bool), reason (str), escalations (list)
    ↓
Proceed or Block
```

---

## Phase 0: Design

### Design Decisions

| Decision | Chosen | Rationale |
|----------|--------|-----------|
| **Guard Implementation** | Separate Guard module (Protocol/interface-based) | Clean separation; can be mocked for testing |
| **Aggregation** | One primary block reason + all escalations | Simple for clients; clear priority |
| **Threshold Tuning** | Config-driven thresholds | Easy tuning without redeployment |
| **Graceful Degradation** | Missing danger scores → skip guard (allow) | Safe fallback; system keeps running |
| **Audit Logging** | All decisions logged (Neo4j Edge annotation) | Compliance + debugging |

---

## Phase 1: Data Models

Core models (Pydantic v2):

- **GuardDecision**: Result of 1 guard check
  - guard_name: str
  - allowed: bool
  - reason: str
  - escalation_path: Optional[str]
  - evidence_score: float

- **TransitionGuardResponse**: Aggregated result
  - allowed: bool
  - decision_type: ALLOW | BLOCK | ESCALATE
  - blocking_reason: Optional[str]
  - escalations: List[GuardDecision]
  - checked_at: datetime

- **GuardConfig**: Thresholds + weights
  - block_ambiguity_threshold: 0.7
  - block_irreversibility_threshold: 0.7
  - escalate_adversarial_threshold: 0.6
  - escalate_institutional_threshold: 0.6

---

## Phase 2: Implementation

### Core Guard Logic

```python
class TransitionGuard:
    def check_no_execute_ambiguous(self, step: Step) -> GuardDecision:
        """Block execute if ambiguity ≥ threshold."""
        if step.danger_scores.danger_ambiguity >= self.config.block_ambiguity_threshold:
            return GuardDecision(
                guard_name="NO_EXECUTE_AMBIGUOUS",
                allowed=False,
                reason=f"Ambiguity score {step.danger_scores.danger_ambiguity:.2f} ≥ threshold (0.7); clarify problem first"
            )
        return GuardDecision(guard_name="NO_EXECUTE_AMBIGUOUS", allowed=True)

    def check_no_irreversible_unverified(self, step: Step) -> GuardDecision:
        """Block execute if irreversible & no prior verification step."""
        if step.danger_scores.danger_irreversibility >= self.config.block_irreversibility_threshold:
            # Check if trace has prior VERIFICATION step
            prior_verification = self.trace_has_verification_step(step.trace_id)
            if not prior_verification:
                return GuardDecision(
                    guard_name="NO_IRREVERSIBLE_UNVERIFIED",
                    allowed=False,
                    reason="Irreversible action without verification; add verification step first"
                )
        return GuardDecision(guard_name="NO_IRREVERSIBLE_UNVERIFIED", allowed=True)

    def check_adversarial_requires_monitoring(self, step: Step) -> GuardDecision:
        """Escalate if adversarial ≥ threshold."""
        if step.danger_scores.danger_adversarial >= self.config.escalate_adversarial_threshold:
            return GuardDecision(
                guard_name="ADVERSARIAL_REQUIRES_MONITORING",
                allowed=True,  # Don't block, but escalate
                escalation_path="monitoring_queue"
            )
        return GuardDecision(guard_name="ADVERSARIAL_REQUIRES_MONITORING", allowed=True)

    def check_institutional_requires_stakeholders(self, step: Step) -> GuardDecision:
        """Escalate if institutional ≥ threshold."""
        if step.danger_scores.danger_institutional >= self.config.escalate_institutional_threshold:
            return GuardDecision(
                guard_name="INSTITUTIONAL_REQUIRES_STAKEHOLDERS",
                allowed=True,
                escalation_path="stakeholder_approval_queue"
            )
        return GuardDecision(guard_name="INSTITUTIONAL_REQUIRES_STAKEHOLDERS", allowed=True)
```

### Orchestration

```python
def check_transition(self, step: Step) -> TransitionGuardResponse:
    """Aggregate all guard decisions."""
    decisions = [
        self.check_no_execute_ambiguous(step),
        self.check_no_irreversible_unverified(step),
        self.check_adversarial_requires_monitoring(step),
        self.check_institutional_requires_stakeholders(step),
    ]

    # Find blocking decision
    blocking = [d for d in decisions if not d.allowed and d.decision_type == "BLOCK"]
    escalations = [d for d in decisions if d.escalation_path]

    if blocking:
        return TransitionGuardResponse(
            allowed=False,
            decision_type="BLOCK",
            blocking_reason=blocking[0].reason,
            escalations=escalations
        )

    if escalations:
        return TransitionGuardResponse(
            allowed=True,
            decision_type="ESCALATE",
            escalations=escalations
        )

    return TransitionGuardResponse(
        allowed=True,
        decision_type="ALLOW",
        escalations=[]
    )
```

---

## Phase 3: Testing

### Unit Tests

```python
def test_no_execute_ambiguous_blocks():
    step = Step(danger_scores=DangerScores(danger_ambiguity=0.8))
    guard = TransitionGuard()
    decision = guard.check_no_execute_ambiguous(step)
    assert decision.allowed == False

def test_no_irreversible_with_prior_verification():
    step = Step(danger_scores=DangerScores(danger_irreversibility=0.9))
    # Mock: prior verification exists
    guard = TransitionGuard()
    decision = guard.check_no_irreversible_unverified(step)
    assert decision.allowed == True
```

### Integration Tests

- Load Phase 1 ingested traces
- Create steps with danger scores
- Verify guards block appropriately
- Verify escalations routed to correct queues
- Check audit log populated

---

## Phase 4: Deployment

### Steps

1. **Days 1-2**: Implement 4 guards + aggregation logic
2. **Day 2-3**: Unit tests + integration tests
3. **Day 3-4**: Performance tuning, audit logging, integration with Phase 1 real data
4. **Day 4+**: Deployment, rollout to staging, Phase 3 readiness

### Success Metrics

- All 6 user stories testable
- 100% of dangerous transitions blocked
- < 50ms guard check latency
- All decisions logged + auditable
- Phase 1 integration: guards work with real traces

---

## See Also

- [spec.md](spec.md) — User stories
- [data-model.md](data-model.md) — Pydantic v2 models
- [docs/reference/danger-classification-impl.md](../../docs/reference/danger-classification-impl.md) — Reference guard logic
