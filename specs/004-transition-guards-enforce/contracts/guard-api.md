# Guard API Contract

**Service**: Phase 2.3 Transition Guards  
**Version**: 1.0  
**Status**: Specification  
**Base URL**: `https://api.grimoire.local/v1`

---

## Overview

REST API for checking transition safety across all 4 guard types. Aggregates individual guard decisions into a single response.

**Authentication**: Service-to-service (API key or mutual TLS)  
**Rate Limit**: 1000 requests/min  
**Timeout**: 100ms (p99)

---

## Endpoints

### 1. Check Transition

Evaluate all guards for a proposed step transition.

```
POST /guards/check
```

#### Request

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum

class StepRole(str, Enum):
    """Role of the step in the reasoning chain."""
    GOAL = "goal"
    PROBLEM = "problem"
    OBSERVATION = "observation"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    QUESTION = "question"

class GuardCheckRequest(BaseModel):
    """Request to check if a transition is allowed."""
    
    trace_id: str = Field(
        description="Trace identifier"
    )
    
    current_step_id: str = Field(
        description="Current step being evaluated"
    )
    
    proposed_role: StepRole = Field(
        description="Proposed role for the next step"
    )
    
    # Phase 2.1 inputs
    danger_scores: Optional[dict] = Field(
        default=None,
        description="Danger scores from Phase 2.1 (if pre-computed)"
    )
    
    # Phase 2.2 inputs
    fsm_classification: Optional[dict] = Field(
        default=None,
        description="FSM classification from Phase 2.2"
    )
    
    # Trace context for multi-step guards
    trace_history: Optional[List[dict]] = Field(
        default=None,
        description="Previous steps in trace (for context-aware guards)"
    )
    
    # User context
    user_id: Optional[str] = Field(
        default=None,
        description="User requesting the transition"
    )
    
    execution_context: Optional[dict] = Field(
        default=None,
        description="Additional context (domain, environment, etc.)"
    )

# Example request
{
  "trace_id": "trace-001-abcd",
  "current_step_id": "step-042",
  "proposed_role": "execute",
  "danger_scores": {
    "ambiguity": 0.75,
    "adversarial": 0.1,
    "irreversibility": 0.85,
    "institutional": 0.2
  },
  "trace_history": [
    {"step_id": "step-041", "role": "plan", "content": "Deploy to production"},
    {"step_id": "step-040", "role": "verify", "content": "All tests passed"}
  ],
  "user_id": "user-123"
}
```

#### Response

**Success (200)**

```python
class GuardDecisionDetail(BaseModel):
    """Individual guard decision."""
    
    guard_name: str = Field(
        description="Name of the guard"
    )
    allowed: bool = Field(
        description="Whether this guard allows"
    )
    reason: str = Field(
        description="Explanation for decision"
    )
    evidence_score: float = Field(
        description="Score that triggered this decision"
    )
    escalation_path: Optional[str] = Field(
        default=None,
        description="Where to escalate if needed"
    )

class GuardCheckResponse(BaseModel):
    """Aggregated guard check response."""
    
    trace_id: str = Field(
        description="Trace being evaluated"
    )
    
    current_step_id: str = Field(
        description="Step being evaluated"
    )
    
    proposed_role: str = Field(
        description="Proposed role"
    )
    
    # Aggregated decision
    decision: str = Field(
        description="Final decision: ALLOW, BLOCK, WARN, or ESCALATE"
    )
    
    allowed: bool = Field(
        description="Whether transition is allowed"
    )
    
    reason: str = Field(
        description="Primary reason for decision"
    )
    
    required_approvers: Optional[List[str]] = Field(
        default=None,
        description="Approvers required (if ESCALATE)"
    )
    
    monitoring_flags: Optional[List[str]] = Field(
        default=None,
        description="Flags for monitoring (if WARN/ESCALATE)"
    )
    
    # Individual guard decisions
    guard_decisions: List[GuardDecisionDetail] = Field(
        description="Decisions from each guard"
    )
    
    # Metadata
    computed_at: str = Field(
        description="ISO8601 timestamp"
    )
    
    processing_ms: int = Field(
        description="Processing time in milliseconds"
    )

# Example response (BLOCKED)
{
  "trace_id": "trace-001-abcd",
  "current_step_id": "step-042",
  "proposed_role": "execute",
  "decision": "BLOCK",
  "allowed": false,
  "reason": "Multiple guards triggered: ambiguity (0.75) and irreversibility (0.85)",
  "required_approvers": null,
  "monitoring_flags": ["HIGH_AMBIGUITY", "IRREVERSIBLE_ACTION"],
  "guard_decisions": [
    {
      "guard_name": "NO_EXECUTE_AMBIGUOUS",
      "allowed": false,
      "reason": "Ambiguity score 0.75 ≥ threshold (0.7); clarify problem first",
      "evidence_score": 0.75,
      "escalation_path": null
    },
    {
      "guard_name": "NO_IRREVERSIBLE_UNVERIFIED",
      "allowed": false,
      "reason": "Irreversibility score 0.85 ≥ threshold (0.7) and no prior VERIFICATION step",
      "evidence_score": 0.85,
      "escalation_path": null
    },
    {
      "guard_name": "ADVERSARIAL_REQUIRES_MONITORING",
      "allowed": true,
      "reason": "Adversarial score 0.1 < threshold (0.6)",
      "evidence_score": 0.1,
      "escalation_path": null
    },
    {
      "guard_name": "INSTITUTIONAL_REQUIRES_STAKEHOLDERS",
      "allowed": true,
      "reason": "Institutional score 0.2 < threshold (0.6)",
      "evidence_score": 0.2,
      "escalation_path": null
    }
  ],
  "computed_at": "2026-02-12T15:30:00Z",
  "processing_ms": 12
}

# Example response (ESCALATE)
{
  "trace_id": "trace-002-efgh",
  "current_step_id": "step-015",
  "proposed_role": "execute",
  "decision": "ESCALATE",
  "allowed": true,
  "reason": "Adversarial score 0.75 ≥ threshold (0.6); requires monitoring",
  "required_approvers": ["security-team", "manager"],
  "monitoring_flags": ["ADVERSARIAL_INTENT"],
  "guard_decisions": [
    {
      "guard_name": "ADVERSARIAL_REQUIRES_MONITORING",
      "allowed": true,
      "reason": "Adversarial score 0.75 ≥ threshold (0.6); monitoring required",
      "evidence_score": 0.75,
      "escalation_path": "security-review-queue"
    }
    // ... other guards ALLOW
  ],
  "computed_at": "2026-02-12T15:30:00Z",
  "processing_ms": 8
}
```

**Error Responses**

| Status | Code | Description |
|--------|------|-------------|
| 400 | INVALID_REQUEST | Missing required fields |
| 404 | TRACE_NOT_FOUND | trace_id not found |
| 422 | INVALID_DANGER_SCORES | Danger scores out of range |
| 500 | INTERNAL_ERROR | Guard evaluation failed |

---

### 2. Batch Check

Check multiple transitions in a single request.

```
POST /guards/check/batch
```

#### Request

```python
class GuardCheckBatchRequest(BaseModel):
    """Batch request for guard checks."""
    
    checks: List[GuardCheckRequest] = Field(
        max_length=100,
        description="Up to 100 checks per batch"
    )
    
    parallel: bool = Field(
        default=True,
        description="Whether to process in parallel"
    )

# Example
{
  "checks": [
    {
      "trace_id": "trace-001",
      "current_step_id": "step-001",
      "proposed_role": "execute",
      "danger_scores": {"ambiguity": 0.8}
    },
    {
      "trace_id": "trace-002",
      "current_step_id": "step-001",
      "proposed_role": "execute",
      "danger_scores": {"ambiguity": 0.3}
    }
  ],
  "parallel": true
}
```

#### Response

```python
class GuardCheckBatchResponse(BaseModel):
    """Batch response."""
    
    results: List[GuardCheckResponse] = Field(
        description="Results for each check"
    )
    
    failed: List[dict] = Field(
        description="Failed checks with error details"
    )
    
    total_ms: int = Field(
        description="Total processing time"
    )

# Example
{
  "results": [
    {
      "trace_id": "trace-001",
      "decision": "BLOCK",
      "allowed": false,
      // ...
    },
    {
      "trace_id": "trace-002",
      "decision": "ALLOW",
      "allowed": true,
      // ...
    }
  ],
  "failed": [],
  "total_ms": 45
}
```

---

### 3. Get Guard Configuration

Retrieve current guard thresholds and rules.

```
GET /guards/config
```

#### Response

```json
{
  "thresholds": {
    "ambiguity": 0.7,
    "irreversibility": 0.7,
    "adversarial": 0.6,
    "institutional": 0.6
  },
  "rules": {
    "NO_EXECUTE_AMBIGUOUS": {
      "description": "Block EXECUTE when ambiguity ≥ threshold",
      "applies_to_roles": ["execute"],
      "escalation_path": null
    },
    "NO_IRREVERSIBLE_UNVERIFIED": {
      "description": "Block EXECUTE when irreversibility ≥ threshold without prior VERIFICATION",
      "applies_to_roles": ["execute"],
      "requires_prior": ["verify"],
      "escalation_path": null
    },
    "ADVERSARIAL_REQUIRES_MONITORING": {
      "description": "ESCALATE when adversarial ≥ threshold",
      "applies_to_roles": ["execute", "plan"],
      "escalation_path": "security-review-queue",
      "required_approvers": ["security-team"]
    },
    "INSTITUTIONAL_REQUIRES_STAKEHOLDERS": {
      "description": "ESCALATE when institutional ≥ threshold",
      "applies_to_roles": ["execute", "plan"],
      "escalation_path": "stakeholder-approval-queue",
      "required_approvers": ["manager", "stakeholder-rep"]
    }
  },
  "version": "1.0.0",
  "updated_at": "2026-02-12T10:00:00Z"
}
```

---

### 4. Update Guard Configuration (Admin)

Update thresholds (requires admin role).

```
PUT /guards/config
```

#### Request

```json
{
  "thresholds": {
    "ambiguity": 0.65,
    "irreversibility": 0.75
  }
}
```

#### Response

```json
{
  "status": "updated",
  "previous_thresholds": {
    "ambiguity": 0.7,
    "irreversibility": 0.7
  },
  "new_thresholds": {
    "ambiguity": 0.65,
    "irreversibility": 0.75
  },
  "updated_at": "2026-02-12T15:30:00Z"
}
```

---

## Aggregation Logic

Guard decisions are aggregated using priority order:

```python
PRIORITY_ORDER = {
    "BLOCK": 4,      # Highest priority
    "ESCALATE": 3,
    "WARN": 2,
    "ALLOW": 1       # Lowest priority
}

def aggregate_decisions(guard_decisions: List[GuardDecision]) -> str:
    """Aggregate individual guard decisions."""
    
    # Collect all decisions
    decisions = [gd.decision for gd in guard_decisions]
    
    # Return highest priority decision
    highest = max(decisions, key=lambda d: PRIORITY_ORDER[d])
    return highest
```

**Rules**:
- If ANY guard returns BLOCK → final decision is BLOCK
- If ANY guard returns ESCALATE (and none BLOCK) → ESCALATE
- If ANY guard returns WARN (and none BLOCK/ESCALATE) → WARN
- Only if ALL guards ALLOW → ALLOW

---

## Storage Integration

Guard decisions are persisted to Neo4j:

```cypher
// Store guard decision on trace
MATCH (t:Trace {trace_id: $trace_id})
CREATE (g:GuardDecision {
  decision_id: $decision_id,
  decision: $decision,
  allowed: $allowed,
  reason: $reason,
  computed_at: datetime(),
  processing_ms: $processing_ms
})
CREATE (t)-[:HAS_GUARD_DECISION]->(g)

// Store individual guard results
WITH g
UNWIND $guard_decisions as gd
CREATE (gd_node:IndividualGuardDecision {
  guard_name: gd.guard_name,
  allowed: gd.allowed,
  reason: gd.reason,
  evidence_score: gd.evidence_score
})
CREATE (g)-[:HAS_INDIVIDUAL_DECISION]->(gd_node)
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Danger scores missing | Re-compute on-the-fly or return 422 |
| Trace not found | Return 404 |
| Guard evaluation fails | Return 500 with partial results |
| Timeout (>100ms) | Return 503 with retry-after header |

---

## Testing Examples

```bash
# Test 1: Block high ambiguity
curl -X POST http://localhost:8000/v1/guards/check \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "test-001",
    "current_step_id": "step-001",
    "proposed_role": "execute",
    "danger_scores": {"ambiguity": 0.8}
  }'
# Expected: BLOCK

# Test 2: Allow low danger
curl -X POST http://localhost:8000/v1/guards/check \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "test-002",
    "current_step_id": "step-001",
    "proposed_role": "execute",
    "danger_scores": {"ambiguity": 0.2, "irreversibility": 0.3}
  }'
# Expected: ALLOW

# Test 3: Escalate adversarial
curl -X POST http://localhost:8000/v1/guards/check \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "test-003",
    "current_step_id": "step-001",
    "proposed_role": "execute",
    "danger_scores": {"adversarial": 0.75}
  }'
# Expected: ESCALATE
```
