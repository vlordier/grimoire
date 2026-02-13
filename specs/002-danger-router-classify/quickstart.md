# Quickstart: Danger Router

**For**: Developers implementing or integrating the Danger Router  
**Time**: 5 min read

---

## Quick Links

| Resource | Purpose |
|----------|---------|
| [spec.md](spec.md) | User stories + requirements |
| [plan.md](plan.md) | Implementation design |
| [data-model.md](data-model.md) | Pydantic v2 models |
| [contracts/danger-classifier-api.md](contracts/danger-classifier-api.md) | API contract + examples |
| [Reference Impl](../../docs/reference/danger-classification-impl.md) | Working code skeleton |

---

## 30-Second Summary

**What**: Classify 4 danger types (ambiguity, adversarial, irreversibility, institutional) in reasoning traces  
**Why**: Prevent dangerous/wasteful decisions (execute on ambiguous problems, irreversibles without verification)  
**How**: Regex keyword detection + scoring + guards on FSM transitions  
**Where**: Called during Step creation; blocks/allows transitions based on danger scores

---

## Core API

### 1. Classify a Trace

```python
from grimoire.danger_router import DangerClassifier, DangerClassifierRequest

classifier = DangerClassifier(config_path="config/classifier_config.yaml")

request = DangerClassifierRequest(
    trace_id="trace-001-abcd",
    text_to_classify="Delete this table to make queries faster",
    context_role="plan"
)

scores = classifier.classify(request)
# scores.danger_ambiguity = 0.2 (mostly clear)
# scores.danger_irreversibility = 0.9 (delete = irreversible)
```

### 2. Check a Guard

```python
from grimoire.danger_router import GuardOrchestrator, TransitionGuardRequest

orchestrator = GuardOrchestrator(config_path="...")

request = TransitionGuardRequest(
    step_id="step-001-xyz",
    proposed_role="execute",
    fsm_state="S4_execute",
    danger_scores=scores  # from classifier
)

decision = orchestrator.check_transition(request)
# decision.allowed = False
# decision.reason = "Irreversibility ≥ 0.7; requires verification step first"
```

### 3. Store Results

```python
# Neo4j
neo4j_driver.session().run(
    """
    MATCH (s:Step {step_id: $step_id})
    SET s.danger_ambiguity = $ambiguity,
        s.danger_adversarial = $adversarial,
        s.danger_irreversibility = $irrev,
        s.danger_institutional = $inst
    """,
    step_id=scores.step_id,
    ambiguity=scores.danger_ambiguity,
    adversarial=scores.danger_adversarial,
    irrev=scores.danger_irreversibility,
    inst=scores.danger_institutional
)

# Qdrant (in step_windows payload)
qdrant_client.upsert(
    collection_name="step_windows",
    points=[
        PointStruct(
            id=window.id,
            vector=embedding,
            payload={
                "danger_ambiguity": scores.danger_ambiguity,
                "danger_adversarial": scores.danger_adversarial,
                ...
            }
        )
    ]
)
```

---

## Enums & Constants

### DangerType (from canonical)

```python
from grimoire.canonical_schema import DangerType, DangerScores

# All 4 types
DangerType.AMBIGUITY
DangerType.ADVERSARIAL
DangerType.IRREVERSIBILITY
DangerType.INSTITUTIONAL

# Scores are [0, 1] for each
scores.danger_ambiguity: float  # [0, 1]
scores.danger_adversarial: float  # [0, 1]
scores.danger_irreversibility: float  # [0, 1]
scores.danger_institutional: float  # [0, 1]
```

### Guard Names

```python
# 4 guards implemented in orchestrator
"NO_EXECUTE_AMBIGUOUS"           # block execute if ambiguity ≥ 0.7
"NO_IRREVERSIBLE_UNVERIFIED"     # block execute if irrev ≥ 0.7 without VERIFICATION step
"ADVERSARIAL_REQUIRES_MONITORING"  # escalate if adversarial ≥ 0.6
"INSTITUTIONAL_REQUIRES_STAKEHOLDERS"  # escalate if institutional ≥ 0.6
```

---

## Configuration

### Default Config (classifier_config.yaml)

```yaml
# Keyword lists (edit to tune)
ambiguity_keywords:
  - unclear
  - maybe
  - probably
  - assume

adversarial_keywords:
  - bypass
  - exploit
  - attack

irreversibility_keywords:
  - delete
  - deploy
  - commit

institutional_keywords:
  - hire
  - fire
  - policy

# Thresholds (higher = stricter)
block_threshold: 0.7      # ≥ 0.7 → block
warn_threshold: 0.5       # [0.5, 0.7) → warn  
escalate_threshold: 0.6   # ≥ 0.6 → escalate (governance decisions)

# Weights (how much text context multiplies score)
problem_statement_weight: 2.0   # Problem/goal = 2x
observation_weight: 1.0         # Observation = 1x baseline
step_based_weight: 1.5          # Execute/decision = 1.5x
```

---

## Common Patterns

### Pattern 1: Classify During Ingestion

```python
# In ingestion pipeline (Phase 1)
for record in hf_dataset:
    trace = normalize_record_to_trace(record)

    # NEW: Classify immediately
    danger_scores = classifier.classify(
        text=trace.problem,
        context_role="goal"
    )
    trace.initial_danger = danger_scores

    # Store
    persist_to_neo4j(trace)
    persist_to_qdrant(trace, danger_scores)
```

### Pattern 2: Guard on Transition

```python
# In FSM engine (Phase 2.3)
def can_transition(current_step: Step, proposed_step: Step, fsm_state: FSMState) -> bool:
    if not proposed_step.danger_scores:
        return True  # Not classified, allow

    decision = orchestrator.check_transition(
        step_id=proposed_step.step_id,
        proposed_role=proposed_step.role,
        fsm_state=fsm_state,
        danger_scores=proposed_step.danger_scores
    )

    if decision.allowed:
        return True
    else:
        logger.warning(f"Guard blocked: {decision.blocking_reason}")
        raise TransitionBlockedError(decision.reason)
```

### Pattern 3: Filter Dangerous Patterns

```python
# In retrieval/recommendation (Phase 3)
def filter_safe_patterns(patterns: List[Pattern], current_danger: DangerScores):
    """Only recommend patterns that don't amplify danger"""
    safe = []
    for pattern in patterns:
        if current_danger.danger_ambiguity < 0.3:
            # Only if we're below ambiguity threshold
            safe.append(pattern)
    return safe
```

---

## Debugging

### Check Evidence

```python
scores = classifier.classify(request)
print(scores.evidence.ambiguity_spans)
# Output:
# [
#   EvidenceSpan(
#     text_span="faster",
#     start_char=15,
#     end_char=21,
#     rule_name="ambiguity_keywords",
#     weight=0.3
#   )
# ]
```

### Test Thresholds

```python
# Manually check if a score should block
score = 0.75
config = ClassifierConfig()
if score >= config.block_threshold:
    print("Would be BLOCKED")
elif score >= config.warn_threshold:
    print("Would be WARNED")
```

### Log Guard Decisions

```python
decision = orchestrator.check_transition(...)
for guard_decision in decision.decisions:
    print(f"{guard_decision.guard_name}: {guard_decision.reason}")
    if guard_decision.escalation_path:
        print(f"  → Escalate to: {guard_decision.escalation_path}")
```

---

## Testing

### Unit Test Example

```python
def test_ambiguity_high_score():
    classifier = DangerClassifier()
    scores = classifier.classify(
        text="Make this faster",
        context_role="goal"
    )
    assert scores.danger_ambiguity >= 0.7, "Should detect ambiguous requirement"

def test_execute_without_verification_blocked():
    orchestrator = GuardOrchestrator()
    decision = orchestrator.check_transition(
        step_id="step-1",
        proposed_role="execute",
        fsm_state="S4_execute",
        danger_scores=DangerScores(
            trace_id="trace-1",
            danger_irreversibility=0.9
        )
    )
    assert decision.allowed == False, "Should block without verification"
```

---

## FAQ

**Q: Can I override the block threshold?**  
A: Yes, edit `classifier_config.yaml` or pass config at init time.

**Q: What if classifier crashes?**  
A: Returns neutral scores (all 0), logs error. System keeps running (graceful degradation).

**Q: How accurate is v1?**  
A: ~75% F1 on test set. v2 (with LLM) planned for higher accuracy.

**Q: Can I add new keywords?**  
A: Yes, edit keyword lists in config YAML.

**Q: How do I trace why a transition was blocked?**  
A: Check `decision.blocking_reason` + `decision.decisions[].reason`. Check evidence spans in scores.

---

## Next Steps

1. **Understand the spec**: Read [spec.md](spec.md) (10 min)
2. **Review design**: Read [plan.md](plan.md) (15 min)
3. **Learn data model**: Read [data-model.md](data-model.md) (10 min)
4. **Check API contract**: Read [contracts/danger-classifier-api.md](contracts/danger-classifier-api.md) (20 min)
5. **Review reference**: Read [danger-classification-impl.md](../../docs/reference/danger-classification-impl.md) (30 min)
6. **Start coding**: Use reference impl as base

---

## Support

- **Questions**: Check [research.md](research.md) for design decisions
- **Reference Code**: [danger-classification-impl.md](../../docs/reference/danger-classification-impl.md)
- **Domain Context**: [Danger Classification](../../docs/domain/danger-classification.md)
- **FSM Context**: [FSM Catalogue](../../docs/domain/fsm-catalogue.md)
