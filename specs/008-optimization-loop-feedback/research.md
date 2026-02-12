# Research: Feedback Loop & Optimization

## Problem Statement

After extracting and ranking patterns, how do we ensure they remain effective as the system and environment change (concept drift)?

**Key Challenge**: Pattern that worked well in January may fail in March if user behavior, data distribution, or requirements shift.

---

## Concept Drift Detection

### What is Concept Drift?

**Definition**: Systematic change in the statistical properties of the target variable over time.

**Example**: 
- Pattern "IF temperature > 30, activate cooling" worked well in summer (80% success)
- Same pattern in winter succeeds only 20% of the time (new distribution)

### Detection Approaches

#### Option A: Fixed Threshold (Recommended for MVP)

**Algorithm**:
```python
effectiveness_30d = average(success_rate for last 30 days)
effectiveness_60d = average(success_rate for days 30-60)

drift_percentage = (effectiveness_30d - effectiveness_60d) / effectiveness_60d × 100

if drift_percentage < -15:  # More than 15% decline
    alert_drift(pattern_id, drift_reason="success_rate_decline")
```

**Parameters**:
- Window size: 30 days (tunable)
- Threshold: 15% decline (tunable)
- Metrics: success_rate, avg_quality, cost (latency/memory)

**Pros**:
- Simple, deterministic
- No statistical assumptions
- Fast to compute

**Cons**:
- Arbitrary threshold (requires tuning)
- May have false positives (random noise)
- Doesn't detect gradual/slow drift well

**Decision**: Use for MVP ✓

---

#### Option B: Statistical Process Control (Advanced)

**Algorithm**: CUSUM (Cumulative Sum Control Chart)

```python
# Track cumulative deviations from baseline
cusum = 0
baseline_mean = effectiveness_60d
threshold = 0.5 * (baseline_mean × 0.15)  # 15% of baseline

for day in recent_days:
    deviation = effectiveness[day] - baseline_mean
    cusum += deviation
    if abs(cusum) > threshold:
        alert_drift(pattern_id)
        cusum = 0  # Reset
```

**Pros**:
- Detects gradual drift earlier
- Statistically principled
- Well-researched (quality control)

**Cons**:
- More complex
- Requires tuning (threshold, window)
- Higher false positive rate initially

**Decision**: Phase 3.4+ (advanced)

---

### Drift Metrics

Track multiple metrics to avoid single-metric bias:

| Metric | Weight | Threshold |
|--------|--------|-----------|
| success_rate | 40% | 15% decline |
| avg_outcome_quality | 35% | 15% decline |
| error_rate | 15% | 15% increase |
| cost_score | 10% | 20% increase (different direction) |

**Formula**:
```
drift_index = 0.4×(drift_success) + 0.35×(drift_quality) + 0.15×(drift_error) + 0.1×(drift_cost)

if drift_index > 0.5:  # Combined threshold
    alert_drift(pattern_id, reason=f"drift_index={drift_index}")
```

---

## Feedback Event Collection

### Event Schema

```python
class FeedbackEvent(BaseModel):
    event_id: str
    pattern_id: str
    trace_id: str
    
    # Execution outcome
    success: bool                        # Did execution succeed?
    outcome_quality: int (0-10)          # Quality of result
    user_satisfaction: int (0-5)         # User feedback
    
    # Performance metrics
    latency_ms: float                    # Execution time
    memory_mb: float                     # Peak memory
    
    # Context
    domain: str (optional, e.g., "ml")
    fsm_type: str (optional)
    user_id: str (optional)
    
    timestamp: ISO8601
```

### Collection Strategy

**Option 1: Inline Collection (Recommended)**
- Instrument pattern execution code
- Collect metrics synchronously
- Immediate availability, accurate but adds overhead (~5-10%)

**Option 2: Asynchronous Collection**
- Fire-and-forget: Send feedback to async queue
- Process in batch later
- Lower latency but risks data loss

**Option 3: Sampling**
- Collect 1% of events randomly
- Extrapolate full statistics
- Much lower overhead but statistical noise

**Decision**: Inline for MVP (accuracy > latency)

---

### Deduplication

**Problem**: Same pattern execution might be reported multiple times (retry logic, distributed tracing).

**Solution**: Dedup by `(pattern_id, trace_id, timestamp_bucket)`
- Keep latest event (overwrites stale)
- Bucket by minute (tolerance for clock skew)

```python
dedup_key = f"{event.pattern_id}#{event.trace_id}#{event.timestamp.minute}"
events[dedup_key] = event  # Overwrites if duplicate
```

---

## Feedback Aggregation

### Buffering Strategy

**Option 1: Batch Collection (Recommended)**
- Buffer K=50 events
- Or flush every T=10 seconds (whichever comes first)
- Async aggregation (non-blocking)
- Trade-off: latency (10s delay) vs throughput (50 events/batch)

**Algorithm**:
```python
buffer = []
while True:
    event = await feedback_queue.get(timeout=10s)
    buffer.append(event)
    
    if len(buffer) >= 50 or timeout_reached:
        aggregate_and_rank(buffer)
        buffer = []
```

**Pros**:
- Batching = efficient database writes
- 10s delay acceptable for learning loop
- 99.9% reliability with retry logic

**Cons**:
- Up to 10s delay before re-ranking
- Loss possible if process crashes (mitigate with cleanup)

**Decision**: Use batch collection ✓

---

### Aggregation Formulas

**Per Pattern** (from N events in batch):

```
success_rate = count(success==True) / N
avg_quality = sum(outcome_quality) / N
avg_satisfaction = sum(user_satisfaction) / N

# Time-decay: recent batches weighted higher
weight = exp(-batch_age_hours / 24)  # 1.0 now, 0.37 after 24h
effective_success_rate = weighted_average(success_rate, weight)
```

---

## Re-Ranking Triggers

### Trigger 1: Event-Based (Automatic)

**Condition**: Every K=50 feedback events → trigger re-ranking of top-N patterns

**Implementation**:
```python
while True:
    batch = aggregate_feedback_batch()  # 50 events
    top_k_patterns = get_top_k_patterns(k=100)  # Affected patterns
    
    new_scores = phase_32_rank(top_k_patterns, context)  # Phase 3.2 integration
    neo4j.update_rankings(new_scores)
    
    log_rerank_event(reason="batch_feedback", patterns_affected=len(top_k_patterns))
```

**Expected Frequency**: Every hour (assuming 100-1000 events/hour)

---

### Trigger 2: Drift-Based (Priority)

**Condition**: Concept drift detected → immediately re-rank affected pattern

**Priority**: Higher than event-based (manual intervention-like)

```python
def check_drift():
    for pattern in active_patterns:
        drift = detect_concept_drift(pattern)
        if drift.severity > THRESHOLD:
            # Priority queue: process before next batch
            rerank_queue.put_front(pattern)
            notify_alert(f"DRIFT DETECTED: {pattern.id}")
```

---

### Trigger 3: Manual API (On-Demand)

**Endpoint**: `POST /v1/patterns/{pattern_id}/rerank`

```python
@app.post("/v1/patterns/{pattern_id}/rerank")
async def manual_rerank(pattern_id: str):
    new_scores = phase_32_rank([pattern_id], context=None)
    neo4j.update_rankings(new_scores)
    return {"status": "reranked", "new_rank_score": new_scores[0].final_rank}
```

---

## A/B Testing Framework

### Experiment Workflow

**Step 1: Create Experiment**

```python
experiment = ABExperiment(
    experiment_id: str,
    pattern_id_v1: str,  # Existing (control)
    pattern_id_v2: str,  # New (treatment)
    traffic_split: 50,   # 50% to each variant
    start_time: DateTime,
    end_time: DateTime,  # Min 7 days later
    min_sample_size: 500  # Per variant
)
```

**Step 2: Route Traffic**

```python
def should_use_v2(trace_id, experiment_id) -> bool:
    # Deterministic: same trace always gets same variant
    hash_value = hash(f"{trace_id}#{experiment_id}") % 100
    return hash_value < experiment.traffic_split
```

**Step 3: Collect Separate Feedback**

Tag all feedback with `experiment_id` so we can compute v1 vs v2 metrics separately.

**Step 4: Statistical Testing**

```python
v1_outcomes = [e.outcome_quality for e in feedback if not e.experiment_variant]
v2_outcomes = [e.outcome_quality for e in feedback if e.experiment_variant]

if len(v1_outcomes) >= 500 and len(v2_outcomes) >= 500:
    t_stat, p_value = ttest_ind(v1_outcomes, v2_outcomes)
    effect_size = cohens_d(v1_outcomes, v2_outcomes)
    
    if p_value < 0.05 and effect_size > 0.2:
        # v2 is statistically significantly better
        winner = "v2"
    else:
        winner = "v1"
    
    return ExperimentResult(winner=winner, p_value=p_value, effect_size=effect_size)
```

**Step 5: Promotion**

```python
if experiment_result.winner == "v2":
    # Promote v2 → production
    mark_pattern_as_current(pattern_id_v2)
    mark_pattern_as_deprecated(pattern_id_v1, reason="superseded_by_v2")
    # 100% traffic → v2
else:
    # Keep v1
    cancel_experiment(experiment_id)
```

---

## Pattern Lifecycle Management

### Versioning

Patterns are versioned: `pattern_001_v1`, `pattern_001_v2`, etc.

**Transitions**:
```
v1 (active)
├── v2 (tested, in A/B)
│   └── PROMOTE → v2 (active), v1 (superseded)
└── v3 (tested, in A/B)
    └── PROMOTE → v3 (active), v1+v2 (superseded)
```

---

### Deprecation Rules

**Automatic Deprecation** (if conditions met):
- Success rate < 30% for 60+ days → LOW_EFFECTIVENESS
- Error rate > 20% for 14+ days → HIGH_ERROR_RATE
- Superseded by newer version → SUPERSEDED
- Manual review → MANUAL_REVIEW

**Process**:
```python
for pattern in all_patterns:
    if pattern.success_rate < 0.3 and age_days > 60:
        mark_deprecated(pattern, reason="low_effectiveness_aged")
    
    if pattern.error_rate > 0.2 and age_days > 14:
        mark_deprecated(pattern, reason="high_error_rate")
```

---

## Monitoring & Alerting

### Dashboard Metrics

1. **Pattern Effectiveness Trends** (7-day rolling)
   - Which patterns improving/degrading?
   - Early warning for drift

2. **A/B Experiment Status** (active, concluded, winners)
   - How many experiments running?
   - Success rate of experiments

3. **Deprecation Events** (recent)
   - Was pattern manually deprecated or auto?
   - Reason (low score, error, superseded)

### Alerts

| Alert | Trigger | Action |
|-------|---------|--------|
| Drift Detected | 15%+ decline | Notify operator, mark for review |
| Experiment Ready | p < 0.05 | Auto-promote winner, notify |
| High Error Rate | >20% errors | Flag pattern, notify |
| Critical Safety | Danger=CRITICAL | Block from auto-exec, escalate |

---

## Storage & Retention

### Data Retention Policies

| Data Type | Retention | Rationale |
|-----------|-----------|-----------|
| Feedback Events | 90 days | Enough for drift detection |
| Ranking Snapshots | 1 year | Long-term trend analysis |
| A/B Experiments | 2 years | Audit trail + learning |
| Deprecated Patterns | Permanent | Audit + history |

### Database Design

**Table: FeedbackEvent**
- Columns: event_id, pattern_id, trace_id, success, quality, satisfaction, latency, memory, timestamp
- Index: (pattern_id, timestamp) for aggregation queries
- Partitioned by timestamp (monthly) for retention

**Table: ConceptDriftAlert**
- Columns: alert_id, pattern_id, metric, old_value, new_value, drift_percentage, detection_time
- Index: (pattern_id, detection_time)

---

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| Feedback event loss | Low | Persistent queue (dead-letter), retry logic |
| False drift alerts | Medium | High threshold (15%), manual validation |
| Type I error in A/B test | Low | p < 0.05 + min 500 samples + effect size |
| Circular re-ranking | Low | Trigger only after batch complete (atomic) |
| Database overload (90d retention) | Medium | Partition by date, archive old data |

---

## Performance Targets

| Operation | Target |
|-----------|--------|
| Feedback collection | <10ms per event |
| Batch aggregation (50 events) | <100ms |
| Drift detection (per pattern) | <1s (hourly batch) |
| Re-ranking (Phase 3.2 call) | <30s for 1000 patterns |
| A/B statistical test | <1s |

