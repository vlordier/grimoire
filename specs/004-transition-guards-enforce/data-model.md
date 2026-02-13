# Data Model: Transition Guards (004)

**Phase**: 2.3  
**Status**: Design Complete  
**Framework**: Pydantic v2  
**Purpose**: Define guard decision models

---

## Core Models

### GuardName (Enum)

```python
from enum import Enum

class GuardName(str, Enum):
    """Names of the 4 transition guards."""

    NO_EXECUTE_AMBIGUOUS = "NO_EXECUTE_AMBIGUOUS"
    NO_IRREVERSIBLE_UNVERIFIED = "NO_IRREVERSIBLE_UNVERIFIED"
    ADVERSARIAL_REQUIRES_MONITORING = "ADVERSARIAL_REQUIRES_MONITORING"
    INSTITUTIONAL_REQUIRES_STAKEHOLDERS = "INSTITUTIONAL_REQUIRES_STAKEHOLDERS"
```

### DecisionType (Enum)

```python
class DecisionType(str, Enum):
    """Types of guard decisions."""

    ALLOW = "ALLOW"              # Proceed normally
    BLOCK = "BLOCK"              # Blocked by guard
    ESCALATE = "ESCALATE"        # Proceed but route to monitoring/approval
    WARN = "WARN"                # Allowed but log warning
```

---

### GuardDecision

Individual guard's decision.

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class GuardDecision(BaseModel):
    """Decision from a single guard."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "guard_name": "NO_EXECUTE_AMBIGUOUS",
            "allowed": False,
            "reason": "Ambiguity score 0.85 ≥ threshold (0.7); clarify problem first",
            "escalation_path": None,
            "evidence_score": 0.85
        }
    })

    guard_name: GuardName = Field(
        ...,
        description="Name of this guard"
    )

    allowed: bool = Field(
        ...,
        description="Whether this guard allows the transition"
    )

    reason: str = Field(
        ...,
        description="Human-readable reason for this decision"
    )

    escalation_path: Optional[str] = Field(
        default=None,
        description="Queue/path for escalation (if applicable)"
    )

    evidence_score: float = Field(
        ...,
        description="The danger score that triggered this decision",
        ge=0.0,
        le=1.0
    )
```

---

### TransitionGuardResponse

Aggregated guard decision.

```python
from typing import List

class TransitionGuardResponse(BaseModel):
    """Aggregated result of all guard checks for a transition."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "step_id": "step-001-xyz",
            "allowed": False,
            "decision_type": "BLOCK",
            "blocking_reason": "Ambiguity score 0.85 ≥ threshold (0.7); clarify problem first",
            "decisions": [
                {
                    "guard_name": "NO_EXECUTE_AMBIGUOUS",
                    "allowed": False,
                    "reason": "Ambiguity score 0.85 ≥ threshold; clarify first",
                    "evidence_score": 0.85
                },
                {
                    "guard_name": "NO_IRREVERSIBLE_UNVERIFIED",
                    "allowed": True
                }
            ],
            "escalations": [],
            "checked_at": "2024-01-15T10:30:45.123456Z"
        }
    })

    step_id: str = Field(
        ...,
        description="ID of step being checked"
    )

    allowed: bool = Field(
        ...,
        description="Final decision: can transition proceed?"
    )

    decision_type: DecisionType = Field(
        ...,
        description="Type of decision: ALLOW, BLOCK, ESCALATE"
    )

    blocking_reason: Optional[str] = Field(
        default=None,
        description="Why transition was blocked (if blocked)"
    )

    decisions: List[GuardDecision] = Field(
        default_factory=list,
        description="Individual decisions from all guards"
    )

    escalations: List[GuardDecision] = Field(
        default_factory=list,
        description="Guards requesting escalation"
    )

    checked_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="When guard checking occurred"
    )

    @model_validator(mode="after")
    def validate_consistency(self):
        """Ensure consistency between allowed and decision_type."""
        if self.decision_type == "BLOCK" and self.allowed:
            raise ValueError("BLOCK decision must have allowed=False")
        if self.decision_type == "ALLOW" and not self.allowed:
            raise ValueError("ALLOW decision must have allowed=True")
        return self
```

---

### GuardConfig

Configuration for guard thresholds.

```python
class GuardConfig(BaseModel):
    """Configuration for danger thresholds."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "block_ambiguity_threshold": 0.7,
            "block_irreversibility_threshold": 0.7,
            "escalate_adversarial_threshold": 0.6,
            "escalate_institutional_threshold": 0.6
        }
    })

    block_ambiguity_threshold: float = Field(
        default=0.7,
        description="Ambiguity ≥ this → block execute",
        ge=0.0,
        le=1.0
    )

    block_irreversibility_threshold: float = Field(
        default=0.7,
        description="Irreversibility ≥ this → require verification",
        ge=0.0,
        le=1.0
    )

    escalate_adversarial_threshold: float = Field(
        default=0.6,
        description="Adversarial ≥ this → escalate to monitoring",
        ge=0.0,
        le=1.0
    )

    escalate_institutional_threshold: float = Field(
        default=0.6,
        description="Institutional ≥ this → escalate to stakeholders",
        ge=0.0,
        le=1.0
    )
```

---

## Input Models

### TransitionGuardRequest

```python
from typing import Optional

class TransitionGuardRequest(BaseModel):
    """Request to check guards on a transition."""

    step_id: str = Field(
        ...,
        description="ID of the step being created/transitioned"
    )

    trace_id: str = Field(
        ...,
        description="ID of the trace containing this step"
    )

    proposed_role: str = Field(
        ...,
        description="Role the step is transitioning to (execute, observe, etc.)"
    )

    danger_scores: Optional[Dict] = Field(
        default=None,
        description="DangerScores from Phase 2.1 classifier"
    )

    fsm_state: Optional[str] = Field(
        default=None,
        description="Current FSM state (from Phase 2.2)"
    )
```

---

## Validators

```python
from pydantic import field_validator

@model_validator(mode="after")
def at_most_one_blocker(self):
    """At most one guard can block."""
    blockers = [d for d in self.decisions if not d.allowed and d.decision_type == "BLOCK"]
    if len(blockers) > 1:
        raise ValueError("Multiple guards blocking simultaneously (shouldn't happen)")
    return self
```

---

## See Also

- [spec.md](spec.md) — User stories
- [plan.md](plan.md) — Implementation roadmap
- [docs/reference/danger-classification-impl.md](../../docs/reference/danger-classification-impl.md) — Reference guard logic
