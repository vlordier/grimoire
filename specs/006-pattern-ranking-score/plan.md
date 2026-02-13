# Implementation Plan: 006-Pattern-Ranking

---

## 📚 Reference Documentation

**Prerequisites**: [Feature 005: Pattern Extraction](../005-pattern-extraction-discover/plan.md)

**See Also:**
- [Build Plan](../../docs/architecture/build-plan.md) — Phase 3 context
- [Pattern Detection & Pipeline](../../docs/reference/pattern-detection-and-pipeline.md) — Ranking algorithms

---

## Overview

Build a pattern-scoring and ranking system that integrates danger/FSM context to prioritize high-value, low-risk reasoning patterns.

## Architecture

```text
┌─────────────────────────────────────────────┐
│ Extracted Patterns (Phase 3.1)              │
│ - pattern_id, targets, cost, effectiveness │
└────────────────┬────────────────────────────┘
                 │
        ┌────────┴─────────┐
        │                  │
┌───────▼──────┐    ┌──────▼────────┐
│ DangerScore  │    │ FSMClassify   │
│ (Phase 2.1)  │    │ (Phase 2.2)   │
└───────┬──────┘    └──────┬────────┘
        │                  │
        └────────┬─────────┘
                 │
        ┌────────▼──────────────┐
        │ Ranking Engine        │
        │ - effectiveness_score │
        │ - safety_flag         │
        │ - relevance_score     │
        │ - cost_score          │
        │ - final_rank          │
        └────────┬──────────────┘
                 │
        ┌────────▼──────────────┐
        │ Neo4j Store           │
        │ - Pattern→RankScore   │
        │ - Pattern→FSMType     │
        │ - Score History       │
        └───────────────────────┘
```

## Phases

### Phase 1: Design & Contracts (Days 1-2)

**Deliverables**: Data models, API contracts, integration plan

**Tasks**:

1. Define RankedPattern Pydantic v2 model with all scoring fields
2. Define RankingContext (fsm_type, domain, danger_scores)
3. Define RankingOutput (ranked_patterns with explanations)
4. Create contracts/pattern-ranking-api.md (batch rank endpoint)
5. Define Phase 2.1/2.2 consumption patterns (DangerScore, FSMClassify contracts)
6. Design Neo4j schema extensions (Pattern→RankScore, score history)

**Risk**: Circular dependencies between scoring components → **Mitigation**: Rank by effectiveness first, inject context sequentially

### Phase 2: Scoring Engine (Days 2-5)

**Deliverables**: All scoring functions, aggregation logic, Neo4j persistence

**Tasks**:

1. Implement effectiveness_score(feedback_events) → (0-1)
   - Filter events with min 5 for significance
   - Time-decay weighting (recent feedback 2x weight)
   - Handle missing feedback types (default to 0.5)

2. Implement safety_flag(danger_scores) → ("CRITICAL" | "MEDIUM" | "LOW" | "SAFE")
   - ANY CRITICAL → CRITICAL
   - ALL MEDIUM or some → MEDIUM
   - Only LOW → LOW
   - No danger info → SAFE

3. Implement relevance_score(pattern_targets, current_fsm) → (0-1)
   - Jaccard similarity: intersection / union
   - Handle empty FSM context (default to 1.0)

4. Implement cost_score(latency_ms, memory_mb, error_rate) → (0-1)
   - Inverse sigmoid transformation
   - Clamp to avoid div/0

5. Implement multi_rank_formula(e, s, r, c) → final_score
   - effectiveness × 0.4 + safety × 0.3 + cost × 0.3
   - Clamp all inputs to [0, 1]

6. Implement Neo4j persist_ranking_scores(pattern_id, scores, timestamp)
   - Store RankScore node with relationships
   - Keep score history immutable (append-only)
   - Index by effectiveness_score, created_date

### Phase 3: API & Integration (Days 5-7)

**Deliverables**: Batch ranking API, integration tests, Phase 2.1/2.2 consumption

**Tasks**:

1. Implement batch_rank_patterns(patterns, context) → RankingOutput
   - Input: 1000-1M patterns (with metadata)
   - Output: Sorted list with score breakdown
   - Target latency: <30ms for 1000, <100ms for 1M

2. Implement graceful degradation
   - If DangerScore unavailable: safety_score = 1.0
   - If FSMClassify unavailable: relevance_score = 1.0
   - Never block on missing context

3. Create integration endpoints
   - POST /v1/rank (batch rank patterns)
   - GET /v1/rank/{pattern_id}/scores (historical scores)
   - GET /v1/rank/dashboard (effectiveness stats)

4. Integrate Phase 2.1 DangerScore consumption (via Neo4j relationships or API)
5. Integrate Phase 2.2 FSMClassify consumption (via Neo4j relationships or API)

6. Add feedback event consumption
   - Listen for pattern execution feedback events
   - Re-rank top N patterns on each batch of K events

### Phase 4: Testing & Optimization (Days 7-8)

**Deliverables**: 95% coverage, performance benchmarks, safety tests

**Tasks**:

1. Unit tests: All scoring functions (deterministic, edge cases)
   - effectiveness_score: min/max values, time decay
   - safety_flag: all danger combinations
   - relevance_score: jaccard edge cases
   - cost_score: division by zero

2. Integration tests: batch_rank_patterns
   - 10 patterns, 100 patterns, 1000 patterns
   - Context combinations (all, partial, none)
   - Latency assertions

3. Safety tests: CRITICAL danger patterns
   - Verify 100% catch rate
   - Verify CRITICAL always escalated
   - Audit trail logged

4. Performance benchmarks
   - Rank 100K patterns: target <50ms
   - Rank 1M patterns: target <100ms
   - Memory allocation: <5GB for 1M patterns

5. Integration with Phase 3.1 patterns
   - Test ranking extracted patterns from Phase 3.1
   - Verify feedback loop (execute pattern → feedback → re-rank)

## Dependencies

### Internal Dependencies

- **Phase 1 (Canonical Schema)**: Pattern model (already implemented ✅)
- **Phase 2.1 (Danger Classifier)**: DangerScore contract + output consumption
- **Phase 2.2 (FSM Router)**: FSMClassification contract + output consumption
- **Phase 3.1 (Pattern Extraction)**: Pattern extraction output (to be implemented)

### External Dependencies

- **Neo4j 5.x**: Graph persistence, relationships
- **Feedback Event Bus**: Pattern execution feedback (from Phase 3.3)
- **Pydantic v2**: Data validation

## Success Metrics

1. **Correctness**
   - 95%+ accuracy of effectiveness scores vs. human raters
   - 100% catch rate for CRITICAL danger patterns
   - Zero circular ranking dependencies

2. **Performance**
   - Rank 1000 patterns in <30ms
   - Rank 1M patterns in <100ms
   - Batch API response p95 <50ms

3. **Reliability**
   - Graceful degradation: system continues without danger/FSM data
   - 99.9% uptime SLA for ranking API
   - No loss of score history

4. **Integration**
   - Consume Phase 2.1 DangerScore successfully in 100% of requests
   - Consume Phase 2.2 FSMClassify successfully in 100% of requests
   - Produce ranked output consumable by Phase 3.3 (optimization loop)

## Timeline

- **Days 1-2**: Design & contracts (PM check-in EOD Day 2)
- **Days 2-5**: Scoring engine + Neo4j integration (Functional demo Day 5)
- **Days 5-7**: API & integration (Integration test Day 7)
- **Days 7-8**: Testing & optimization (Performance benchmark Day 8)

**Estimated Effort**: 6-8 days

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|---------|----|
| Circular dependencies (pattern→danger→FSM→rank) | Medium | High | Design rank-first approach, inject context sequentially |
| Expensive Neo4j queries for 1M patterns | Medium | High | Pre-compute top-K rankings, cache scores, add index |
| Feedback event lag (stale scores) | Low | Medium | Buffer events, batch rank async, TTL cache |
| Safety filtering misconfiguration | Medium | High | Thorough unit tests, CRITICAL pattern audit log |

## Handoff to Phase 3.3

**Outputs to Phase 3.3**:

- RankedPattern model (pattern_id, effectiveness_score, safety_flag, relevance_score, final_rank)
- Ranking history (for trend analysis, concept drift detection)
- Feedback consumption API (for optimization loop to update scores)

**Inputs from Phase 3.3**:

- Feedback events (success, outcome_quality, user_satisfaction, latency, memory)
- Re-ranking triggers (every K events or T seconds)
