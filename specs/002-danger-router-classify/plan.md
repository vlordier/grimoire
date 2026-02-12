# Implementation Plan: Danger Router

**Feature**: 002-danger-router-classify  
**Branch**: 002-danger-router-classify  
**Date**: 12 Feb 2026  
**Status**: Design Phase

---

## Phase 0: Research & Clarification

### Key Decisions

| Decision | Resolution | Rationale |
|----------|-----------|-----------|
| **v1 Algorithm** | Rule-based (regex + scoring) | No LLM calls needed; lower cost; deterministic; reference impl exists |
| **Thresholds** | Conservative (0.7 for block) | Prefer false positives over false negatives (better to ask than to harm) |
| **Evidence Format** | Text spans + rule names | Enables debugging, audit trail, user explanation |
| **Integration Point** | At Step creation | Classify as traces are ingested, attach scores to Step metadata |
| **Guard Persistence** | Neo4j properties + edges | Store blocked transitions as Step.guard_blocked + BLOCKED_BY_GUARD edges |

### Dependencies

- ✅ Phase 1 (schemas, ingestion, storage) — required
- ✅ Canonical Schemas (DangerType, DangerScores) — already defined
- ✅ Reference Implementation — [danger-classification-impl.md](../../docs/reference/danger-classification-impl.md)

---

## Phase 1: Data Model & Contracts

### 1.1 Data Models (Pydantic v2)

**Existing Models** (from Canonical Schemas):
- `DangerType` enum: ambiguity, adversarial, irreversibility, institutional
- `DangerScores` (BaseModel): scores dict + evidence

**New Models** (for this feature):
- `DangerClassifierRequest`: trace_text, step_role, context
- `DangerClassifierResponse`: 4 scores + evidence spans
- `GuardDecision`: allowed (bool), reason, escalation_path
- `ClassifierConfig`: keyword lists, thresholds, weights (for tuning)

### 1.2 API Contract

**Core Functions**:
```python
def classify_trace(trace: Trace) -> DangerScores
def classify_step(step: Step, trace_context: Trace) -> DangerScores
def check_transition(
    current_state: FSMState,
    proposed_step_role: StepRole,
    danger_scores: DangerScores
) -> GuardDecision
```

---

## Phase 2: Implementation

### 2.1 Danger Classifier Module

**Components**:
1. **Keyword Detector** (regex-based)
   - ambiguity keywords: "unclear", "maybe", "probably", "assume"
   - adversarial keywords: "bypass", "exploit", "circumvent", "attack"
   - irreversibility keywords: "delete", "deploy", "commit", "fire", "shutdown"  
   - institutional keywords: "hire", "fire", "policy", "budget", "stakeholder"

2. **Scoring Engine**
   - Keyword frequency + presence scoring
   - Context weighting (problem statement = 2x weight vs observation)
   - Score aggregation: min(1.0, sum(weights) / total_weight)

3. **Evidence Extractor**
   - Identify text spans matching keywords
   - Extract supporting rules

### 2.2 Guard Enforcement Module

**4 Guard Implementations**:

1. **NO_EXECUTE_AMBIGUOUS**
   - If `danger_ambiguity ≥ 0.7` and `step_role == EXECUTE`: **BLOCK**
   - Threshold: 0.7 (tunable)

2. **NO_IRREVERSIBLE_UNVERIFIED**
   - If `danger_irreversibility ≥ 0.7` and `step_role == EXECUTE`:
     - Check if prior step has `role == VERIFICATION`
     - If yes: **ALLOW**
     - If no: **BLOCK**

3. **ADVERSARIAL_REQUIRES_MONITORING**
   - If `danger_adversarial ≥ 0.6` and trace is marked COMPLETE:
     - Check if last steps contain `role == MONITORING` or `role == CLOSE`
     - If yes: **ALLOW**
     - If no: **ESCALATE** (flag for human review)

4. **INSTITUTIONAL_REQUIRES_STAKEHOLDERS**
   - If `danger_institutional ≥ 0.6` and `step_role == DECISION`:
     - Escalate with stakeholder metadata
     - **ESCALATE** (require sign-off)

### 2.3 Storage Integration

#### Neo4j Cypher Templates

**Store Danger Scores on Step**
```cypher
// Attach danger scores to Step node
MATCH (s:Step {step_id: $step_id})
SET s.danger_ambiguity = $ambiguity,
    s.danger_adversarial = $adversarial,
    s.danger_irreversibility = $irreversibility,
    s.danger_institutional = $institutional,
    s.danger_computed_at = datetime(),
    s.danger_classifier_version = $version
RETURN s.step_id, s.danger_ambiguity, s.danger_adversarial
```

**Query Steps by Danger Level**
```cypher
// Find high-risk steps for review
MATCH (s:Step)
WHERE s.danger_ambiguity >= 0.7
   OR s.danger_adversarial >= 0.6
   OR s.danger_irreversibility >= 0.7
   OR s.danger_institutional >= 0.6
RETURN s.step_id, 
       s.danger_ambiguity, 
       s.danger_adversarial,
       s.danger_irreversibility,
       s.danger_institutional,
       s.content[0..100] as preview
ORDER BY (s.danger_ambiguity + s.danger_adversarial + 
          s.danger_irreversibility + s.danger_institutional) DESC
LIMIT 100
```

**Store Guard Block Decision**
```cypher
// Record when guard blocks a transition
MATCH (s:Step {step_id: $step_id})
CREATE (g:GuardDecision {
  decision_id: $decision_id,
  decision: 'BLOCK',
  reason: $reason,
  guard_name: $guard_name,
  evidence_score: $evidence_score,
  computed_at: datetime()
})
CREATE (s)-[:BLOCKED_BY_GUARD]->(g)
RETURN g.decision_id
```

**Query Blocked Steps with Context**
```cypher
// Get blocked steps with trace context
MATCH (t:Trace)-[:CONTAINS]->(s:Step)-[:BLOCKED_BY_GUARD]->(g:GuardDecision)
WHERE g.computed_at > datetime() - duration('P7D')
RETURN t.trace_id,
       s.step_id,
       s.step_type,
       g.guard_name,
       g.reason,
       g.computed_at
ORDER BY g.computed_at DESC
```

**Aggregate Danger Statistics**
```cypher
// Daily danger score distribution
MATCH (s:Step)
WHERE s.danger_computed_at > datetime() - duration('P1D')
RETURN 
  CASE 
    WHEN s.danger_ambiguity >= 0.7 THEN 'high_ambiguity'
    WHEN s.danger_adversarial >= 0.6 THEN 'high_adversarial'
    WHEN s.danger_irreversibility >= 0.7 THEN 'high_irreversible'
    WHEN s.danger_institutional >= 0.6 THEN 'high_institutional'
    ELSE 'low_risk'
  END as risk_category,
  count(*) as count
ORDER BY count DESC
```

#### Qdrant Payload Updates

```python
# Update step_windows collection with danger scores
qdrant_client.set_payload(
    collection_name="step_windows",
    points=[step_id],
    payload={
        "danger_ambiguity": scores.ambiguity,
        "danger_adversarial": scores.adversarial,
        "danger_irreversibility": scores.irreversibility,
        "danger_institutional": scores.institutional,
        "danger_level": calculate_overall_level(scores)
    }
)
```

### 2.4 Configuration

**Configurable Parameters** (in `classifier_config.yaml`):
```yaml
# Keyword lists (can be extended)
ambiguity_keywords: [unclear, maybe, probably, ...]
adversarial_keywords: [bypass, exploit, ...]
irreversibility_keywords: [delete, deploy, ...]
institutional_keywords: [hire, fire, ...]

# Thresholds
block_threshold: 0.7
warn_threshold: 0.5
escalate_threshold: 0.6

# Weights
problem_statement_weight: 2.0
observation_weight: 1.0
step_based_weight: 1.5

# Context multipliers
execute_multiplier: 1.5
decision_multiplier: 1.2
```

---

## Phase 3: Testing

### 3.1 Unit Tests

**Test Coverage**:
- Keyword detection (each keyword triggers correctly)
- Scoring logic (monotonic, bounded [0, 1])
- Guard logic (each guard blocks/allows correctly)
- Edge cases (empty text, null context, mixed signals)

**Example Test Cases**:
```python
def test_ambiguity_high_score():
    text = "Make this faster somehow"
    score = classify(text).danger_ambiguity
    assert score >= 0.7

def test_irreversibility_requires_verification():
    steps = [
        Step(role=PLAN, text="..."),
        Step(role=EXECUTE, text="delete database"),  # No verification
    ]
    decision = check_transition(..., EXECUTE, danger_irreversibility=0.9)
    assert decision.allowed == False and "verification" in decision.reason

def test_institutional_escalation():
    decision = check_transition(..., DECISION, danger_institutional=0.8)
    assert decision.escalation_path is not None
```

### 3.2 Integration Tests

- Ingest Phase 1 traces, classify them, verify scores attached
- Store guards in Neo4j, retrieve via query
- End-to-end: trace → classification → guard check → stored result

### 3.3 Evaluation Metrics

- **Precision**: Of traces classified as "high danger", what % were evaluated correctly by humans?
- **Recall**: Of actual high-danger traces, what % did classifier find?
- **F1**: Balanced metric combining precision + recall
- **Threshold**: Aim for F1 ≥ 0.75 on test set

---

## Phase 4: Rollout & Integration

### 4.1 Deployment Steps

1. **Unit tests pass** (100% coverage on classifier logic)
2. **Integration tests pass** (Phase 1 data flows through successfully)
3. **Human evaluation** (10-20 sample traces classified + reviewed)
4. **Threshold tuning** (adjust weights based on evaluation feedback)
5. **Documentation** (update README, quickstart, keyword tuning guide)

### 4.2 Phase 3 Handoff

Pass to Phase 3 (Pattern Mining) with:
- ✅ Danger scores for all historical traces
- ✅ Guard evidence logs  
- ✅ Tuned thresholds (production-ready)
- ✅ Maintenance guide

---

## Files to Create

```
specs/002-danger-router-classify/
├── spec.md ✅
├── plan.md ✅ (this file)
├── research.md (Q&A from planning)
├── data-model.md (Pydantic models)
├── quickstart.md (dev reference)
└── contracts/
    └── danger-classifier-api.md (API contract)
```

---

## Effort Estimate

| Task | Days | Notes |
|------|------|-------|
| Planning + research | 1-2 | Mostly done; clarifications TBD |
| Data model + enums | 0.5 | Reuse from canonical |
| Classifier implementation | 2-3 | Regex patterns, scoring, evidence |
| Guard enforcement | 1-2 | Logic composition, Neo4j storage |
| Unit tests | 1-2 | Test matrix coverage |
| Integration tests | 1 | Phase 1 → classifier → Phase 2 |
| Documentation | 1 | README, quickstart, config guide |
| **Total** | **7-11 days** | ~2 weeks with buffers |

---

## Success Metrics

- ✅ All 8 user stories testable independently
- ✅ F1 ≥ 0.75 on evaluation set
- ✅ Classifier < 500ms per trace
- ✅ Integrated with Phase 1 (can classify stored traces)
- ✅ Guards working as specified
- ✅ Zero unhandled exceptions
- ✅ Full test coverage on critical paths (>80%)

---

## Related Documents

- **Reference**: [Danger Classification Impl](../../docs/reference/danger-classification-impl.md)
- **Domain**: [Danger Classification](../../docs/domain/danger-classification.md)
- **FSM**: [FSM Catalogue](../../docs/domain/fsm-catalogue.md) (needed for guard state checks)
- **Canonical**: [Canonical Schemas — DangerType, DangerScores](../../docs/reference/canonical-schemas.md)
