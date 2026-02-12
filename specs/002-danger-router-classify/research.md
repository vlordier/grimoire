# Research & Clarification: Danger Router

**Feature**: 002-danger-router-classify  
**Date**: 12 Feb 2026

---

## Clarification Questions

### Q1: Should we use LLM or regex-only classifier for v1?

**Decision**: **Regex-only** (rules + keyword scoring)

**Rationale**:
- Reference implementation in [danger-classification-impl.md](../../docs/reference/danger-classification-impl.md) is fully rules-based
- Deterministic: same input always produces same score (easier debugging)
- Lower latency: < 500ms vs LLM calls (seconds)
- Lower cost: no API calls
- v1 goal is fast deployment; LLM enhancement can come in Phase 2.1 or later

**Trade-off**: May miss novel danger patterns that LLM would catch, but reference impl covers ~80% of cases with keywords alone.

---

### Q2: What thresholds should we use for blocking vs warning vs escalating?

**Decision**: 
- **Block**: ≥ 0.7 (high confidence danger)
- **Warn**: 0.5–0.7 (medium confidence, log but allow)
- **Escalate**: ≥ 0.6 for institutional (requires sign-off)

**Rationale**:
- 0.7 is conservative enough to avoid false positives in critical paths (like execute)
- 0.5–0.7 allows operation but logs for audit
- Thresholds tunable via config (see plan.md)
- Will adjust based on evaluation data

---

### Q3: How do we handle multi-danger scenarios?

**Example**: A problem is both ambiguous AND irreversible ("Delete this table faster")

**Decision**: Score each independently, apply guards separately

- Ambiguity guard: ambiguity ≥ 0.7 → block EXECUTE
- Irreversibility guard: irreversibility ≥ 0.7 → require VERIFICATION before EXECUTE
- **Both apply**: User must first clarify, then add verification step, THEN execute

**Rationale**: Each danger archetype has different mitigation (clarification vs verification). Keeps logic modular.

---

### Q4: Should guards live in Danger Classifier or separate Guard module?

**Decision**: **Separate Guard module** (orchestrates classifier input + FSM state)

**Rationale**:
- Classifier is pure: text → scores (no state dependencies)
- Guards are stateful: need FSM state + trace history
- Easier to test, debug, and extend separately
- Aligns with Phase 2.3 feature (transition guards)

**Architecture**:
```
Trace Input
  ↓
[Classifier] → DangerScores
  ↓
[Guard Orchestrator] + [FSM State] → GuardDecision (ALLOW/BLOCK/ESCALATE)
```

---

### Q5: Where do danger scores live in the data model?

**Decision**: Attached to Steps, optional on Trace

- `Step.danger_ambiguity`, `.danger_adversarial`, etc. (required, [0, 1])
- `Trace.initial_danger` (optional, computed from first K steps)
- Stored in Neo4j as node properties
- Stored in Qdrant as payload fields (for filtering)

**Rationale**:
- Steps evolve, so danger may change through trace
- Trace-level danger gives quick overview
- Stored in both stores for fast retrieval (Neo4j for graph queries, Qdrant for vector filtering)

---

### Q6: How do we handle language/multilingual issues?

**Decision**: v1 **English-only**, with placeholders for future localization

**Rationale**:
- Reference implementation is English-based
- MVP on HuggingFace datasets (mostly English)
- Keyword expansion to other languages in Phase 3+
- Log non-English as uncertainty (neutral scores)

---

### Q7: What happens if input is empty or malformed?

**Decision**: **Return neutral scores** (all scores = 0), log warning

```python
def classify(trace: Trace) -> DangerScores:
    if not trace or not trace.text:
        logger.warning(f"Empty trace {trace.id}; returning neutral scores")
        return DangerScores(scores={
            DangerType.AMBIGUITY: 0.0,
            DangerType.ADVERSARIAL: 0.0,
            DangerType.IRREVERSIBILITY: 0.0,
            DangerType.INSTITUTIONAL: 0.0,
        })
```

**Rationale**: 
- No crash (robust)
- Neutral is safe (won't block legitimate work)
- Logged for investigation

---

### Q8: Should guards block or just flag/escalate?

**Decision**: **Mixed**:
- AMBIGUITY guard: **BLOCK** EXECUTE (too risky)
- IRREVERSIBILITY guard: **BLOCK** EXECUTE without verification (too risky)
- ADVERSARIAL guard: **ESCALATE** (flag for human, allow to proceed if user confirms)
- INSTITUTIONAL guard: **ESCALATE** (require stakeholder metadata, proceed after approval)

**Rationale**:
- Ambiguity + Irreversibility are operational risks → block
- Adversarial + Institutional are governance risks → escalate (human-in-loop)

---

### Q9: How do we know if the classifier is accurate?

**Decision**: Evaluate on curated test set with human judgments

**Method**:
1. Create 20-30 manually-labeled traces (human rated each as high/low danger)
2. Run classifier on them
3. Compute precision, recall, F1
4. Target: F1 ≥ 0.75

**Timeline**: End of Phase 2.1 (Week 2)

---

### Q10: What's the upgrade path from v1 (rules) to v2 (LLM)?

**Decision**: **Pluggable scorer interface**

```python
class DangerScorer(Protocol):
    def score(self, trace: Trace) -> DangerScores: ...

# v1: RuleBasedScorer
# v2 (future): LLMScorer
# v3 (future): EnsembleScorer(rules + LLM)  
```

**Rationale**:
- Same API, different implementations
- Can A/B test v1 vs v2
- No API breakage when upgrading

---

## Design Decisions Summary

| Decision | Chosen | Alternative | Trade-off |
|----------|--------|-----------|-----------|
| Algorithm | Rules-based | LLM | Simpler, faster, cheaper vs more coverage |
| Thresholds | 0.7 block, 0.5 warn | 0.5 block, 0.3 warn | Conservative (more false positives) vs aggressive |
| Storage | Neo4j + Qdrant | Neo4j only | Queryable + filterable vs simpler |
| Language | English-only | Multilingual | Faster v1 vs broader audience |
| Guard Action | Block + Escalate | Block only | Human oversight vs strict automation |
| Scorer Interface | Pluggable | Hardcoded | Easier upgrades vs simpler code |

---

## Open Questions (For Planning Phase)

- [ ] **Human evaluation dataset**: Can we get labeled traces from security/compliance team?
- [ ] **Threshold tuning**: After evaluation, do we adjust thresholds?
- [ ] **Keyword expansion**: Should we crowd-source new keywords from users?
- [ ] **Integration timeline**: When do Phase 3 features need danger scores?
- [ ] **Monitoring**: How do we track true positives/false positives in production?

---

## Related Reading

- [Danger Classification Reference Impl](../../docs/reference/danger-classification-impl.md)
- [Danger Classification Domain](../../docs/domain/danger-classification.md)
- [Phase 2 Analysis](../../PHASE_2_ANALYSIS.md)
- [FSM Catalogue](../../docs/domain/fsm-catalogue.md)
