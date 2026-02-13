# Data Model: Danger Router

**Feature**: 002-danger-router-classify  
**Date**: 12 Feb 2026  
**Pydantic Version**: v2

---

## Models

### DangerType Enum (From Canonical)

```python
from enum import Enum

class DangerType(str, Enum):
    """Four danger archetypes"""
    AMBIGUITY = "ambiguity"
    ADVERSARIAL = "adversarial"
    IRREVERSIBILITY = "irreversibility"
    INSTITUTIONAL = "institutional"
```

---

### DangerEvidence (Detailed Reasoning)

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class EvidenceSpan(BaseModel):
    """Single evidence point for a danger score"""

    text_span: str = Field(
        description="Quoted text supporting the danger classification"
    )
    start_char: int = Field(
        ge=0,
        description="Character offset in original text"
    )
    end_char: int = Field(
        ge=0,
        description="Character offset (exclusive)"
    )
    rule_name: str = Field(
        description="Which rule triggered this evidence (e.g., 'ambiguity_keywords')"
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        description="Contribution of this evidence to the final score"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "text_span": "Make this faster",
                "start_char": 5,
                "end_char": 20,
                "rule_name": "ambiguity_keywords",
                "weight": 0.3
            }
        }


class DangerEvidence(BaseModel):
    """Evidence supporting all 4 danger scores"""

    ambiguity_spans: List[EvidenceSpan] = Field(
        default_factory=list,
        description="Evidence for ambiguity danger"
    )
    adversarial_spans: List[EvidenceSpan] = Field(
        default_factory=list,
        description="Evidence for adversarial danger"
    )
    irreversibility_spans: List[EvidenceSpan] = Field(
        default_factory=list,
        description="Evidence for irreversibility danger"
    )
    institutional_spans: List[EvidenceSpan] = Field(
        default_factory=list,
        description="Evidence for institutional danger"
    )
```

---

### DangerClassifierRequest

```python
from typing import Literal, Optional

class DangerClassifierRequest(BaseModel):
    """Input to danger classifier"""

    trace_id: str = Field(
        description="Which trace to classify"
    )
    text_to_classify: str = Field(
        description="Text (problem statement or step text)"
    )
    context_role: Optional[Literal["goal", "question", "plan", "action", "observation", "decision", "other"]] = Field(
        default=None,
        description="What role is this text (affects weighting)"
    )
    prior_danger_scores: Optional[Dict[str, float]] = Field(
        default=None,
        description="Previous scores for context (ignored in v1)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "trace-001-abcd",
                "text_to_classify": "Make the system faster without breaking anything",
                "context_role": "goal",
                "prior_danger_scores": None
            }
        }
```

---

### DangerScores (Updated)

```python
class DangerScores(BaseModel):
    """All 4 danger scores + evidence"""

    trace_id: str = Field(
        description="Trace being classified"
    )
    danger_ambiguity: float = Field(
        ge=0.0,
        le=1.0,
        description="0=clear, 1=highly ambiguous"
    )
    danger_adversarial: float = Field(
        ge=0.0,
        le=1.0,
        description="0=benign, 1=adversarial"
    )
    danger_irreversibility: float = Field(
        ge=0.0,
        le=1.0,
        description="0=reversible, 1=highly irreversible"
    )
    danger_institutional: float = Field(
        ge=0.0,
        le=1.0,
        description="0=individual, 1=institutional"
    )

    evidence: DangerEvidence = Field(
        description="Detailed evidence for each score"
    )

    computed_at: datetime = Field(
        description="When scores were computed"
    )
    classifier_version: str = Field(
        default="0.1.0-alpha",
        description="Classifier version (for audit trail)"
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        default=1.0,
        description="Overall confidence in scores (1.0 for rules, <1 for LLM)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "trace_id": "trace-001-abcd",
                "danger_ambiguity": 0.6,
                "danger_adversarial": 0.1,
                "danger_irreversibility": 0.3,
                "danger_institutional": 0.0,
                "evidence": {...},
                "computed_at": "2026-02-12T10:30:00Z",
                "classifier_version": "0.1.0-alpha",
                "confidence": 1.0
            }
        }
```

---

### GuardDecision

```python
from typing import Literal

class GuardDecision(BaseModel):
    """Decision from a single guard"""

    allowed: bool = Field(
        description="Is the transition allowed?"
    )
    decision_type: Literal["ALLOW", "BLOCK", "WARN", "ESCALATE"] = Field(
        description="Type of decision"
    )
    reason: str = Field(
        description="Human-readable reason (e.g., 'Ambiguity ≥ 0.7; clarify first')"
    )
    guard_name: str = Field(
        description="Which guard made this decision"
    )
    escalation_path: Optional[str] = Field(
        default=None,
        description="If ESCALATE: who to escalate to (e.g., 'stakeholder_approval')"
    )
    evidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Supporting score (the danger value that triggered guard)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "allowed": False,
                "decision_type": "BLOCK",
                "reason": "Ambiguity ≥ 0.7; clarify requirements before executing",
                "guard_name": "NO_EXECUTE_AMBIGUOUS",
                "escalation_path": None,
                "evidence_score": 0.75
            }
        }


class TransitionGuardResponse(BaseModel):
    """Aggregated guard decisions for a transition"""

    step_id: str = Field(
        description="Step being evaluated"
    )
    proposed_role: str = Field(
        description="StepRole being proposed"
    )
    fsm_state: Optional[str] = Field(
        default=None,
        description="Current FSM state"
    )

    decisions: List[GuardDecision] = Field(
        description="All guard decisions that applied"
    )

    allowed: bool = Field(
        description="Transition allowed? (True if all guards allow)"
    )
    blocking_reason: Optional[str] = Field(
        default=None,
        description="If blocked, why"
    )
    escalations: List[str] = Field(
        default_factory=list,
        description="If any guard escalated, list them"
    )

    checked_at: datetime = Field(
        description="When guards were checked"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "step_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "proposed_role": "execute",
                "fsm_state": "S4_execute",
                "decisions": [
                    {
                        "allowed": False,
                        "decision_type": "BLOCK",
                        "reason": "Ambiguity ≥ 0.7",
                        "guard_name": "NO_EXECUTE_AMBIGUOUS",
                        "evidence_score": 0.8
                    }
                ],
                "allowed": False,
                "blocking_reason": "NO_EXECUTE_AMBIGUOUS: Ambiguity ≥ 0.7",
                "escalations": [],
                "checked_at": "2026-02-12T10:30:00Z"
            }
        }
```

---

### ClassifierConfig

```python
from typing import List, Dict

class ClassifierConfig(BaseModel):
    """Configuration for tuning classifier behavior"""

    # Keyword lists (expandable)
    ambiguity_keywords: List[str] = Field(
        default_factory=lambda: [
            "unclear", "unclear", "probably", "maybe", "assume", 
            "unsure", "unknown", "missing", "unclear requirements"
        ]
    )
    adversarial_keywords: List[str] = Field(
        default_factory=lambda: [
            "bypass", "exploit", "circumvent", "attack", "deceive",
            "hack", "steal", "manipulate", "adversary", "malicious"
        ]
    )
    irreversibility_keywords: List[str] = Field(
        default_factory=lambda: [
            "delete", "deploy", "commit", "fire", "shutdown",
            "destroy", "erase", "permanent", "irreversible"
        ]
    )
    institutional_keywords: List[str] = Field(
        default_factory=lambda: [
            "hire", "fire", "policy", "budget", "stakeholder",
            "approval", "governance", "audit", "compliance", "legal"
        ]
    )

    # Scoring thresholds
    block_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Score ≥ this → block dangerous operations"
    )
    warn_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Score in [warn, block) → warn but allow"
    )
    escalate_threshold: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Score ≥ this → escalate for governance"
    )

    # Scoring weights
    problem_statement_weight: float = Field(
        default=2.0,
        ge=0.0,
        description="Goal/problem text weighted 2x"
    )
    observation_weight: float = Field(
        default=1.0,
        ge=0.0,
        description="Observation text baseline"
    )
    step_based_weight: float = Field(
        default=1.5,
        ge=0.0,
        description="Execution/decision text weighted 1.5x"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "ambiguity_keywords": ["unclear", "maybe", "assume", ...],
                "block_threshold": 0.7,
                "warn_threshold": 0.5,
                "problem_statement_weight": 2.0
            }
        }
```

---

## Validators

### DangerScores Validator

```python
from pydantic import field_validator, model_validator

class DangerScores(BaseModel):
    # ... fields ...

    @field_validator("danger_ambiguity", "danger_adversarial", 
                     "danger_irreversibility", "danger_institutional")
    @classmethod
    def danger_bounds(cls, v):
        """Ensure all scores in [0, 1]"""
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Danger score must be in [0.0, 1.0], got {v}")
        return v

    @model_validator(mode="after")
    def evidence_not_empty(self):
        """Ensure at least one evidence span if score > 0"""
        total_spans = (
            len(self.evidence.ambiguity_spans) +
            len(self.evidence.adversarial_spans) +
            len(self.evidence.irreversibility_spans) +
            len(self.evidence.institutional_spans)
        )
        total_score = (
            self.danger_ambiguity +
            self.danger_adversarial +
            self.danger_irreversibility +
            self.danger_institutional
        )

        if total_score > 0.5 and total_spans == 0:
            raise ValueError(
                f"Scores suggest danger, but no evidence spans provided"
            )
        return self
```

---

## JSON Schema Export

```python
if __name__ == "__main__":
    from json import dumps

    schemas = {
        "DangerScores": DangerScores.model_json_schema(),
        "TransitionGuardResponse": TransitionGuardResponse.model_json_schema(),
        "ClassifierConfig": ClassifierConfig.model_json_schema(),
    }

    for name, schema in schemas.items():
        with open(f"schemas/{name}.json", "w") as f:
            f.write(dumps(schema, indent=2))
```

---

## Compatibility

- **Pydantic v2**: All models use BaseModel + field_validator
- **JSON Serialization**: All models support `.model_dump_json()` and `.model_validate_json()`
- **Neo4j Storage**: Scores stored as node properties; evidence stored as JSON
- **Qdrant Storage**: Scores + evidence stored in step_windows payload
