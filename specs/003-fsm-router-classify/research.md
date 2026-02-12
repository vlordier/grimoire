# Research & Clarification: FSM Router

**Phase**: 2.2 Planning  
**Questions Addressed**: 10 key clarifications for FSM Router design  
**Date**: 12 February 2026

---

## Key Questions & Decisions

### Q1: Rules-Based vs LLM-Based Classification?

**Question**: Should router use keyword matching (rules) or LLM classifier?

**Decision**: **Rules-based (keyword matching) for v1; LLM in v2+**

**Rationale**:
- Keywords are deterministic, fast (<50ms), no API calls
- Reference implementation (FSM Router) has working keyword patterns
- Extensible: config file allows team to add/tune keywords
- v2 can add LLM for higher accuracy without breaking v1 API

**Trade-offs**:
- ✅ Pro: Fast, cheap, no external dependency
- ❌ Con: Lower accuracy on edge cases; needs tuning
- ✅ Mitigation: Fallback to clarify_frame when confidence low

---

### Q2: What Confidence Threshold for Auto-Routing?

**Question**: At what confidence level should router commit to an FSM? Below that threshold, what happens?

**Decision**: **Threshold = 0.5 (50% keyword match); below = fallback to `fsm_clarify_frame`**

**Rationale**:
- 50% means keywords found in multiple categories
- Clarify_frame is safe default (narrows scope first before committing to strategy)
- Conservative: better to ask clarifying questions than guess wrong FSM

**Examples**:
- "Debug the timeout bug" → confidence 0.8 (fsm_diagnose_fix) ✅
- "Improve performance" → confidence 0.4 (below threshold → fsm_clarify_frame) ⚠️
- "Do something good" → confidence 0.0 (fsm_clarify_frame) ⚠️

---

### Q3: Multi-FSM Problems — Return Multiple Suggestions?

**Question**: Some problems fit multiple FSMs equally well (e.g., "optimize by redesigning schema"). How to handle?

**Decision**: **Return 1 primary FSM; include top 2-3 alternatives in response metadata**

**Rationale**:
- Simplifies FSM transitions (one path forward)
- Alternatives provide transparency for manual override
- User can switch to alternative if primary doesn't feel right

**Example**:
```
Problem: "Performance tuning requires schema redesign"

Primary: fsm_optimize (confidence 0.65)
  → "Performance tuning, optimize → fsm_optimize"

Alternatives:
  - fsm_design_decide (0.60, "redesign schema → design_decide")
  - fsm_transform (0.55, "reshape → transform")
```

---

### Q4: Should FSM Selection Depend on Danger Scores (002)?

**Question**: Should router use danger classifier output to refine FSM selection?

**Decision**: **No hard dependency in v1; optional refinement in Phase 3**

**Rationale**:
- Decouples Phase 2.2 from Phase 2.1 (can develop in parallel)
- Danger scores improve confidence but not strictly required
- Phase 3 optimization: "adversarial problem → fsm_adversarial_loop"

**v1 Approach**: FSM selection independent; danger scores optional input  
**v2 Approach**: Danger context can boost FSM confidence

---

### Q5: How to Extend Keywords — Config-Driven or Code?

**Question**: Should new keywords require code deploy or config update?

**Decision**: **Config-driven (routing_config.yaml) — no code change needed**

**Rationale**:
- Domain experts can add keywords without eng involvement
- Easy A/B testing of keyword sets
- Fast feedback loop for tuning

**Example**:
```yaml
fsm_adversarial_loop:
  keywords:
    - adversarial
    - attack
    - defense
    - anticipate  # ADD THIS
    - strengthen  # ADD THIS
```

Restart → new keywords take effect. Zero code change.

---

### Q6: Performance Target — How Fast Should Routing Be?

**Question**: What's acceptable latency for FSM routing?

**Decision**: **P50 < 50ms, P99 < 100ms per route**

**Rationale**:
- Keyword matching can be optimized to sub-50ms (regex compiled at startup)
- 100ms on P99 allows some overhead
- Batch 1000 traces in < 100 seconds (1000 × 50ms baseline + overhead)

**Performance Breakdown** (estimated):
- Regex compilation (startup): 5ms
- Text preprocessing: 5ms
- Keyword matching: 30ms
- Scoring + selection: 5ms
- **Total**: ~45ms per route

---

### Q7: Fallback Behavior — What If Routing Crashes?

**Question**: If keyword matching crashes/fails, what happens?

**Decision**: **Graceful degradation: return default FSM (clarify_frame, confidence 0.0)**

**Rationale**:
- System stays operational (no data loss)
- Safety-first: clarify_frame is appropriate default
- Log error for debugging

**Example**:
```
ERROR: Regex compilation failed for FSM patterns
FALLBACK: Routing to fsm_clarify_frame (confidence=0.0, classifier_version="1.0.0-degraded")
```

---

### Q8: How to Evaluate Accuracy — What's "Good Enough"?

**Question**: How do we measure if router is routing correctly?

**Decision**: **80%+ human agreement on evaluation set (20 representative problems)**

**Rationale**:
- Human reviewers provide ground truth
- 80% is reasonable bar (catches obvious errors, allows noise)
- Representative set captures domain diversity

**Evaluation Process**:
1. Select 20 diverse problems (from Phase 1 historical data)
2. Route each via router
3. Have 2 domain experts review each; score correctness
4. Calculate agreement %
5. Target: 80%+ agreement = production-ready

---

### Q9: Upgrade Path — How to Evolve from v1 (Rules) to v2 (LLM)?

**Question**: How do we add LLM-based routing in v2 without breaking v1 clients?

**Decision**: **Pluggable scorer interface (abstract base); v2 implements LLM scorer**

**Rationale**:
- API stays same (FSMRouterRequest → FSMRouterResponse)
- Backend swapped out (rules scorer → LLM scorer)
- Clients don't notice the change

**Architecture**:
```python
class FSMScorer(Protocol):
    def score(text: str) -> FSMRoute: ...

class KeywordScorer(FSMScorer):  # v1
    def score(text: str) -> FSMRoute: ...

class LLMScorer(FSMScorer):  # v2 (Phase 3)
    def score(text: str) -> FSMRoute: ...

router = FSMRouter(scorer=KeywordScorer())  # v1
router = FSMRouter(scorer=LLMScorer())      # v2 (drop-in replacement)
```

---

### Q10: Language Support — English-Only or Multilingual?

**Question**: Should router support non-English problems?

**Decision**: **English-only in v1; multilingual Phase 3+**

**Rationale**:
- Keyword lists optimized for English
- Reference data (Phase 1 traces) mostly English
- Faster MVP; multilingual adds complexity
- Phase 3: Translate keywords or use multilingual LLM (v2)

**v1 Behavior**: Non-English input → low confidence → default to clarify_frame (safe fallback)

---

## Design Decisions Summary

| # | Decision | Alternative | Trade-Off |
|---|----------|-------------|-----------|
| 1 | Rules-based v1 | LLM-based | Fast/cheap vs accurate |
| 2 | Threshold 0.5 | Threshold 0.7 | Conservative/safe vs optimistic |
| 3 | Primary + alternatives | Single primary | Transparent vs simple |
| 4 | Independent from danger | Depend on danger scores | Parallel dev vs optimized |
| 5 | Config-driven keywords | Code-driven | Easy extension vs type-safe |
| 6 | P99 < 100ms | P99 < 50ms | Practical vs ambitious |
| 7 | Graceful degradation | Fail hard | Robustness vs transparency |
| 8 | 80% human agreement | 90% agreement | Practical vs strict |
| 9 | Pluggable scorer interface | Fixed implementation | Flexible vs simple |
| 10 | English-only v1 | Multilingual v1 | Fast vs comprehensive |

---

## Open Questions for Planning Phase

These will be resolved during Phase 2.2 implementation:

1. **Keyword Expansion**: How many keywords per FSM? (Target: 5-10 per type)
2. **Keyword Weights**: Do all keywords contribute equally, or should some be boosted?
3. **Distance-Based Scoring**: Should "debug" (exact match) score higher than "problem" (fuzzy)?
4. **Caching**: Should we cache keyword extraction results? (Probably not; text varies)
5. **Monitoring**: What metrics to track? (Routing success rate, misrouting rate, confidence distribution)

---

## See Also

- [plan.md](plan.md) — Implementation phases
- [data-model.md](data-model.md) — Pydantic v2 schemas
- [docs/domain/fsm-catalogue.md](../../docs/domain/fsm-catalogue.md) — FSM definitions
- [docs/reference/fsm-router-impl.md](../../docs/reference/fsm-router-impl.md) — Reference code
