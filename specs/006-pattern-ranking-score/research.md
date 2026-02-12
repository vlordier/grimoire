# Research: Pattern Ranking Algorithms

## Problem Statement

Given a list of extracted patterns, how do we prioritize them for recommendation? Patterns have competing objectives:

- **Effectiveness**: High success rate (does it work?)
- **Safety**: Low danger scores (is it safe?)
- **Relevance**: Matches current context (is it applicable?)
- **Efficiency**: Fast execution (is it affordable?)

Multi-objective optimization: can't maximize all simultaneously.

---

## Ranking Approaches

### Option A: Weighted Sum (Recommended for MVP)

**Formula**:

```text
final_rank = w1 × effectiveness + w2 × safety + w3 × relevance + w4 × cost
where w1 + w2 + w3 + w4 = 1.0
```

**Default Weights**:

- `w1` = 0.4 (effectiveness is most important)
- `w2` = 0.3 (safety is critical but less flexible)
- `w3` = 0.2 (relevance helps but not essential)
- `w4` = 0.1 (efficiency is nice-to-have)

**Pros**:

- Simple, deterministic, explainable
- Fast computation (single pass)
- Easy to tune weights (interpretable)

**Cons**:

- Weights are arbitrary (requires domain expertise)
- Linear model misses non-linear trade-offs
- Doesn't handle conflicting objectives well

**Decision**: Use for MVP ✓

---

### Option B: Pareto Frontier (Advanced)

**Approach**: Find patterns where no other pattern dominates on all objectives

**Definition**: Pattern A dominates B if:

- `effectiveness(A) ≥ effectiveness(B)` AND
- `safety(A) ≥ safety(B)` AND
- `relevance(A) ≥ relevance(B)` AND
- `cost(A) ≥ cost(B)` (lower cost is better)

AND at least one is strictly greater.

**Algorithm**:

```python
pareto_frontier = []
for pattern in patterns:
    dominated = False
    for other in patterns:
        if other dominates pattern:
            dominated = True
            break
    if not dominated:
        pareto_frontier.append(pattern)

# Rank within frontier by effectiveness or context
return sorted(pareto_frontier, key=lambda p: p.effectiveness, reverse=True)
```

**Pros**:

- No arbitrary weights
- Optimal (no better solution exists)
- Handles conflicting objectives naturally

**Cons**:

- Frontier may be large (100+ patterns)
- Still need tie-breaking rule (within frontier)
- More complex to implement + explain

**Decision**: Phase 3.2+ (future enhancement)

---

### Option C: Learning-to-Rank (ML-based)

**Approach**: Train regression model to predict "goodness" score

**Data**:

- Features: `[effectiveness, safety, relevance, cost, domain_match, user_context]`
- Label: `human_rating` (1-5) or `observed_outcome_quality`

**Algorithm**:

- LambdaMART or LightGBM with ranking objective
- Learn patterns in feature interactions (non-linear)

**Pros**:

- Automatic weight learning
- Captures non-linear interactions
- Empirically validated

**Cons**:

- Requires labeled training data
- Black box (hard to explain ranking)
- Requires retraining as data changes

**Decision**: Phase 3.4+ (advanced, requires data)

---

## Effectiveness Scoring

**Components**:

1. Success rate: Proportion of executions that succeeded
2. Outcome quality: User-rated outcome (1-10)
3. User satisfaction: Subjective feedback (1-5)

**Formula**:

```text
effectiveness = 
  0.4 × min(success_count / min_samples, 1.0) +
  0.35 × (avg_quality / 10) +
  0.25 × (avg_satisfaction / 5)
```

**Edge Cases**:

- If `success_count < min_samples` (default 5): Assign default score 0.5 (unknown)
- If no feedback: default 0.5
- If all failures: score = 0
- If 100% success + quality 10 + satisfaction 5: score = 1.0

**Time Decay** (optional):

```text
# Weight recent feedback higher
weight = exp(-age_days / 30)  # Decays to 0.37 after 30 days
effectiveness_updated = weighted_average(effectiveness, new_feedback, weight)
```

**Validation**:

- Range: 0-1 ✓
- Deterministic (same input → same output) ✓
- Explainable (transparent formula) ✓

---

## Safety Scoring

**Integration with Phase 2.1 (Danger Classifier)**

**Danger Types Mapping**:

| Danger Type | Safety Score | Recommendation |
|-------------|--------------|-----------------|
| CRITICAL | 0 | ❌ Never recommend, escalate |
| HIGH | 0.25 | ⚠️ Recommend with caution alert |
| MEDIUM | 0.5 | ⚠️ Recommend with warning |
| LOW | 0.8 | ✓ Recommend with note |
| SAFE (no danger) | 1.0 | ✓ Recommend freely |

**Logic**:

```python
def safety_score(pattern, danger_scores):
    # Take worst (minimum) danger type
    if any(d.type == "CRITICAL" for d in danger_scores):
        return 0.0, "CRITICAL"
    elif any(d.type == "HIGH" for d in danger_scores):
        return 0.25, "HIGH"
    elif any(d.type == "MEDIUM" for d in danger_scores):
        return 0.5, "MEDIUM"
    elif any(d.type == "LOW" for d in danger_scores):
        return 0.8, "LOW"
    else:
        return 1.0, "SAFE"
```

**Escalation**:

- CRITICAL patterns: logged, operator alert, blocked from auto-execution
- HIGH patterns: logged, available but flagged in UI
- MEDIUM patterns: logged, recommended with warning
- LOW/SAFE: recommended freely

---

## Relevance Scoring

**Integration with Phase 2.2 (FSM Router)**

**Concept**: How well does pattern match current execution context?

**Formula**:

```text
relevance = pattern_fsm_types ∩ current_fsm_types / |current_fsm_types|
```

Example:

- Pattern applies to: `[DECISION, ITERATION]` (2 types)
- Current FSM type: `[DECISION, CONDITIONAL, BRANCHING]` (3 types)
- Overlap: `[DECISION]` (1 type)
- Relevance: 1 / 3 = 0.33

**Edge Cases**:

- No current FSM context: relevance = 1.0 (always relevant)
- Pattern not tagged with FSM: relevance = 1.0 (assume universal)
- Exact FSM match: relevance = 1.0 (perfect)

**Domain Matching** (secondary):

```text
domain_relevance = pattern_domains ∩ current_domains / |pattern_domains|
# Add to ranking if domain provided
adjusted_relevance = 0.7 × fsm_relevance + 0.3 × domain_relevance
```

---

## Cost Scoring

**Components**:

- Latency: Execution time (ms)
- Memory: Peak memory (MB)
- Error rate: Failure rate (0-1)

**Normalization**:

```text
normalized_latency = min(latency_ms / 1000, 1.0)     # 1000ms = score 1.0
normalized_memory = min(memory_mb / 100, 1.0)        # 100MB = score 1.0
normalized_error = error_rate                         # 0-1 already

cost_metric = 
  0.5 × normalized_latency +
  0.3 × normalized_memory +
  0.2 × normalized_error

cost_score = 1 / (1 + cost_metric)  # Inverse sigmoid [0, 1)
```

**Example**:

- Pattern A: 50ms, 10MB, 1% error
  - Metrics: (0.05, 0.1, 0.01)
  - cost_metric = 0.5×0.05 + 0.3×0.1 + 0.2×0.01 = 0.052
  - cost_score = 1 / (1 + 0.052) = 0.95 (excellent)

- Pattern B: 500ms, 200MB, 5% error
  - Metrics: (0.5, 1.0, 0.05)
  - cost_metric = 0.5×0.5 + 0.3×1.0 + 0.2×0.05 = 0.56
  - cost_score = 1 / (1 + 0.56) = 0.64 (acceptable)

---

## Multi-Objective Formula

**Final Ranking**:

```text
rank_score = 
  0.4 × effectiveness_score +
  0.3 × safety_score +
  0.2 × relevance_score +
  0.1 × cost_score
```

**All components normalized to [0, 1]**:

- effectiveness_score: 0-1 ✓
- safety_score: 0-1 ✓
- relevance_score: 0-1 ✓
- cost_score: 0-1 ✓

**Result**: rank_score ∈ [0, 1]

---

## Handling Phase 2.1-2.2 Dependencies

### Dependency Resolution

**Scenario 1: DangerScore available**

- Use Phase 2.1 output directly: `safety_score = map_danger_to_safety(danger_scores)`
- If unavailable, gracefully degrade: `safety_score = 1.0`

**Scenario 2: FSMClassification available**

- Use Phase 2.2 output directly: `relevance_score = jaccard(pattern_fsm, current_fsm)`
- If unavailable, degrade: `relevance_score = 1.0`

**No Circular Dependency**:

- Ranking doesn't call back to Phase 2 (one-way dependency)
- Phase 2 can evolve independently

### Contract Inputs

From Phase 2.1:

```python
DangerScore(
    pattern_id: str,
    danger_types: List[DangerType],  # CRITICAL, HIGH, MEDIUM, LOW
    severity: float,                  # 0-1
    reason: str
)
```

From Phase 2.2:

```python
FSMClassification(
    trace_id: str,
    fsm_type: str,                    # DECISION, ITERATION, etc.
    confidence: float                 # 0-1
)
```

---

## Performance Considerations

### Latency Targets

| Operation | Input Size | Target Latency |
|-----------|-----------|-----------------|
| Rank patterns | 100 patterns | <5ms |
| Rank patterns | 1,000 patterns | <30ms |
| Rank patterns | 100K patterns | <1s |
| Rank patterns | 1M patterns | <100ms (pre-computed) |

### Optimization Strategies

1. **Pre-compute Component Scores**
   - Calculate effectiveness, safety, relevance offline
   - Store in Neo4j with index on component scores
   - Ranking = weighted sum of pre-computed components

2. **Lazy Evaluation**
   - Cache frequently-ranked patterns
   - Only recompute when feedback updates

3. **Vectorize Operations**
   - Use NumPy/Pandas for batch ranking
   - Avoid Python loops, use matrix operations

4. **Top-K Retrieval**
   - For 1M patterns, only rank top-K by effectiveness first
   - Then combine other factors on top-K

---

## Validation

### A/B Testing Ranking Formulas

**Setup**: Compare two ranking formulas

- Formula A (current): 0.4/0.3/0.2/0.1 weights
- Formula B (proposed): 0.5/0.2/0.2/0.1 weights

**Metrics**:

- User satisfaction: avg rating of recommended patterns
- Adoption: % of recommendations actually used
- Success rate: outcome quality when pattern used

**Significance**: p < 0.05 (statistical test)

---

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Wrong weights → bad recommendations | High | A/B test multiple weight configs |
| Expensive Neo4j queries for 1M | Medium | Index + pre-compute + batch ops |
| Circular dependencies (rank→danger) | Low | One-way dependency, graceful degrade |
| Non-normalized scores | High | Validate all inputs [0, 1] |