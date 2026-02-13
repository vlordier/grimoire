# Data Model: FSM Router (003)

**Phase**: 2.2  
**Status**: Design Complete  
**Framework**: Pydantic v2  
**Purpose**: Define request/response models for FSM routing

---

## Core Models

### FSMType (Enum)

Represents all 10 universal FSM types.

```python
from enum import Enum

class FSMType(str, Enum):
    """10 universal FSM types from reference implementation."""

    CLARIFY_FRAME = "fsm_clarify_frame"
    """Narrow scope, define success criteria."""

    DIAGNOSE_FIX = "fsm_diagnose_fix"
    """Find root cause, apply fix, verify."""

    DESIGN_DECIDE = "fsm_design_decide"
    """Explore options, evaluate trade-offs, decide."""

    OPTIMIZE = "fsm_optimize"
    """Tune parameters, measure, iterate."""

    VERIFY = "fsm_verify"
    """Test hypothesis, check all cases."""

    TRANSFORM = "fsm_transform"
    """Reshape problem structure."""

    OPERATE_HARDEN = "fsm_operate_harden"
    """Stabilize system, prepare for production."""

    POSTMORTEM = "fsm_postmortem"
    """Analyze failure, extract lessons."""

    RESOLVE_CONFLICT = "fsm_resolve_conflict"
    """Negotiate constraints, find consensus."""

    ADVERSARIAL_LOOP = "fsm_adversarial_loop"
    """Anticipate attacks, strengthen defense."""


# All 10 types
assert len(FSMType) == 10
```

---

### FSMRouterRequest

Input to the routing engine.

```python
from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field

class FSMRouterRequest(BaseModel):
    """Request to route a problem to an appropriate FSM."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "trace_id": "trace-001-abcd",
            "problem_text": "Why do database queries timeout under load?",
            "context": {
                "domain": "backend",
                "user_level": "architect"
            }
        }
    })

    trace_id: str = Field(
        ...,
        description="Unique trace identifier",
        pattern=r"^trace-[\d]{3}-[a-z]{4}$|^[a-f0-9-]{36}$"
    )

    problem_text: str = Field(
        ...,
        description="Problem or goal statement to classify",
        min_length=10,
        max_length=5000
    )

    context: Optional[Dict[str, str]] = Field(
        default=None,
        description="Optional context (domain, user_level, language, etc.)"
    )

    optional_fsm_hints: Optional[List[FSMType]] = Field(
        default=None,
        description="User hints for FSM selection (e.g., ['fsm_diagnose_fix', 'fsm_optimize'])"
    )


# Validation example
try:
    req = FSMRouterRequest(
        trace_id="trace-001-abcd",
        problem_text="Why do queries timeout?"
    )
except ValidationError as e:
    print(e.json())
```

---

### FSMRoute

Core routing decision.

```python
class FSMRoute(BaseModel):
    """A single FSM routing decision with confidence and alternatives."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "selected_fsm_id": "fsm_diagnose_fix",
            "selected_fsm_name": "Diagnose & Fix",
            "confidence": 0.85,
            "reasoning": "Keywords matched: debug, timeout, root cause, why → fsm_diagnose_fix (7/7 keywords)",
            "alternative_fsms": [
                {
                    "fsm_id": "fsm_optimize",
                    "fsm_name": "Optimize",
                    "confidence": 0.45,
                    "keywords_matched": ["timeout"]
                }
            ]
        }
    })

    selected_fsm_id: FSMType = Field(
        ...,
        description="Primary FSM type selected"
    )

    selected_fsm_name: str = Field(
        ...,
        description="Human-readable FSM name",
        examples=["Diagnose & Fix", "Design & Decide", "Optimize"]
    )

    confidence: float = Field(
        ...,
        description="Confidence in selection [0, 1]",
        ge=0.0,
        le=1.0
    )

    reasoning: str = Field(
        ...,
        description="Explanation for why this FSM was selected"
    )

    alternative_fsms: List[Dict[str, any]] = Field(
        default_factory=list,
        description="Top 2-3 alternative FSMs with confidences"
    )

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v):
        """Confidence must be in [0, 1]."""
        if not (0.0 <= v <= 1.0):
            raise ValueError("Confidence must be between 0.0 and 1.0")
        return v

    @field_validator("selected_fsm_name")
    @classmethod
    def validate_fsm_name_not_empty(cls, v):
        """FSM name must not be empty."""
        if not v or not v.strip():
            raise ValueError("FSM name cannot be empty")
        return v
```

---

### FSMRouterResponse

Output from the routing engine.

```python
from datetime import datetime

class FSMRouterResponse(BaseModel):
    """Response from FSM Router with routing decision."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "trace_id": "trace-001-abcd",
            "route": {
                "selected_fsm_id": "fsm_diagnose_fix",
                "selected_fsm_name": "Diagnose & Fix",
                "confidence": 0.85,
                "reasoning": "Keywords: debug, timeout, root cause → fsm_diagnose_fix"
            },
            "routing_ms": 45,
            "router_version": "1.0.0",
            "computed_at": "2024-01-15T10:30:45.123456Z"
        }
    })

    trace_id: str = Field(
        ...,
        description="Echo of input trace_id"
    )

    route: FSMRoute = Field(
        ...,
        description="Primary routing decision"
    )

    routing_ms: int = Field(
        ...,
        description="Time to compute routing (milliseconds)",
        ge=0
    )

    router_version: str = Field(
        default="1.0.0",
        description="Router implementation version"
    )

    computed_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="ISO 8601 timestamp when routing was computed"
    )

    @field_validator("routing_ms")
    @classmethod
    def validate_latency(cls, v):
        """Latency should reasonable."""
        if v < 0:
            raise ValueError("Latency cannot be negative")
        if v > 1000:
            # Warning only, don't fail
            import logging
            logging.warning(f"High routing latency: {v}ms")
        return v
```

---

### RoutingConfig

Configuration for keyword-based routing.

```python
from typing import Dict, List

class RoutingConfig(BaseModel):
    """Configuration for FSM routing (keyword-based, v1)."""

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "fsm_keywords": {
                "fsm_diagnose_fix": ["debug", "bug", "error", "root cause"],
                "fsm_design_decide": ["design", "architect", "choose", "option"]
            },
            "confidence_threshold": 0.5,
            "default_fsm": "fsm_clarify_frame",
            "keyword_weights": {}
        }
    })

    fsm_keywords: Dict[str, List[str]] = Field(
        ...,
        description="Mapping from FSM type to keyword list"
    )

    confidence_threshold: float = Field(
        default=0.5,
        description="Threshold below which to fallback to default FSM",
        ge=0.0,
        le=1.0
    )

    default_fsm: FSMType = Field(
        default=FSMType.CLARIFY_FRAME,
        description="Default FSM if confidence too low"
    )

    keyword_weights: Dict[str, float] = Field(
        default_factory=dict,
        description="Optional weights per keyword (if keywords vary in importance)"
    )

    @model_validator(mode="after")
    def validate_config(self):
        """Validate that default FSM is in the FSM types."""
        fsm_ids = set(FSMType)
        if str(self.default_fsm.value) not in [str(t.value) for t in fsm_ids]:
            raise ValueError(f"Default FSM {self.default_fsm} not in known FSM types")
        return self

    @field_validator("confidence_threshold")
    @classmethod
    def validate_threshold(cls, v):
        """Threshold should be reasonable."""
        if v < 0.3 or v > 0.9:
            import logging
            logging.warning(f"Unusual confidence threshold: {v}")
        return v


# Example config from YAML
example_config = RoutingConfig(
    fsm_keywords={
        "fsm_diagnose_fix": [
            "bug", "debug", "error", "fix", "root cause",
            "why", "not working", "broken", "fail"
        ],
        "fsm_design_decide": [
            "design", "architect", "build", "choose", "option",
            "alternative", "compare", "decision", "which"
        ],
        "fsm_optimize": [
            "performance", "speed", "optimize", "faster", "slow",
            "latency", "throughput", "tune", "improve", "efficient"
        ],
        "fsm_verify": [
            "test", "verify", "validate", "check", "hypothesis",
            "confirm", "assertion"
        ],
        # ... remaining 6 FSM types
    },
    confidence_threshold=0.5,
    default_fsm=FSMType.CLARIFY_FRAME
)
```

---

## Batch Models

### FSMRouterBatchRequest

Route multiple problems in a batch.

```python
class FSMRouterBatchRequest(BaseModel):
    """Batch request for routing multiple problems."""

    traces: List[FSMRouterRequest] = Field(
        ...,
        description="Problems to route",
        min_items=1,
        max_items=1000
    )

    parallel: bool = Field(
        default=True,
        description="Whether to process traces in parallel"
    )


class FSMRouterBatchResponse(BaseModel):
    """Batch response with routing results."""

    results: List[FSMRouterResponse] = Field(
        ...,
        description="Routing results for each input"
    )

    failed: List[Dict[str, any]] = Field(
        default_factory=list,
        description="Failed requests (trace_id, error)"
    )

    total_ms: int = Field(
        ...,
        description="Total batch processing time"
    )
```

---

## Enums & Constants

### Default FSM Names

```python
FSM_NAMES = {
    FSMType.CLARIFY_FRAME: "Clarify & Frame",
    FSMType.DIAGNOSE_FIX: "Diagnose & Fix",
    FSMType.DESIGN_DECIDE: "Design & Decide",
    FSMType.OPTIMIZE: "Optimize",
    FSMType.VERIFY: "Verify",
    FSMType.TRANSFORM: "Transform",
    FSMType.OPERATE_HARDEN: "Operate & Harden",
    FSMType.POSTMORTEM: "Postmortem",
    FSMType.RESOLVE_CONFLICT: "Resolve Conflict",
    FSMType.ADVERSARIAL_LOOP: "Adversarial Loop",
}
```

---

## Validation Rules

```python
# Constraint: confidence in alternatives must be ≤ primary confidence
@model_validator(mode="after")
def validate_alternatives_confidence(self):
    """Alternatives should have lower confidence than primary."""
    primary_conf = self.route.confidence
    for alt in self.route.alternative_fsms:
        if alt.get("confidence", 0) > primary_conf:
            raise ValueError(
                f"Alternative confidence ({alt['confidence']}) > primary ({primary_conf})"
            )
    return self


# Constraint: reasoning must mention confidence or keywords
@field_validator("reasoning")
@classmethod
def validate_reasoning_informative(cls, v):
    """Reasoning should explain the decision."""
    if len(v) < 20:
        raise ValueError("Reasoning must be informative (≥20 chars)")
    return v
```

---

## JSON Schema Export

```python
# Generate JSON Schema for API docs
from pydantic.json_schema import models_json_schema

schema = models_json_schema(
    [(FSMRouterRequest, 'validation'), (FSMRouterResponse, 'serialization')],
    title="FSM Router API Schema"
)

print(schema)
```

---

## Integration with Phase 1

**Input Source**:

- `TraceBundle.problem` → `FSMRouterRequest.problem_text`
- `Trace.trace_id` → `FSMRouterRequest.trace_id`

**Output Target**:

- `FSMRouterResponse.route.selected_fsm_id` → saved to `Step.fsm_type` (Neo4j)
- `FSMRouterResponse.route.confidence` → saved to `Step.fsm_confidence`

---

## See Also

- [spec.md](spec.md) — User stories
- [plan.md](plan.md) — Implementation roadmap
- [data-model.md](../001-canonical-schema-implementation/data-model.md) — Phase 1 canonical models
