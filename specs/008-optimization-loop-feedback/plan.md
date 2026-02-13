# Implementation Plan: 007-Optimization-Loop

---

## 📚 Reference Documentation

**Prerequisites**: Features 001-006 — Accumulates feedback from entire system

**See Also:**
- [Build Plan](../../docs/architecture/build-plan.md) — Phase 3+ roadmap
- [Integration Test Strategy](../../docs/operations/INTEGRATION_TEST_STRATEGY.md) — Testing strategy
- [Control Flow Specification](../../docs/operations/CONTROL_FLOW_SPECIFICATION.md) — Loop patterns

---

## Overview

Build a closed-loop feedback system that continuously improves pattern rankings through execution monitoring, drift detection, and A/B testing.

## Architecture

```text
┌────────────────────────────────────────┐
│ Pattern Execution (Phases 3.1-3.2)     │
│ - Run pattern on trace                 │
│ - Record latency, memory, success      │
└────────────────┬───────────────────────┘
                 │
        ┌────────▼───────────────────────┐
        │ Feedback Collection             │
        │ - Async buffer (K=50 events)   │
        │ - Dedup (trace_id + pattern)   │
        │ - Tag with domain, fsm_type    │
        └────────┬───────────────────────┘
                 │
        ┌────────▼───────────────────────┐
        │ Batch Processing (per 50 events)
        │ - Aggregate metrics             │
        │ - Calculate effectiveness      │
        │ - Detect drift (30/60d windows) │
        └────────┬───────────────────────┘
                 │
        ┌────────▼───────────────────────┐
        │ Drift Detection & Re-ranking   │
        │ - If drift: Call Phase 3.2     │
        │ - If experiment: Route traffic │
        │ - Update rankings               │
        └────────┬───────────────────────┘
                 │
        ┌────────▼───────────────────────┐
        │ Pattern Lifecycle Management   │
        │ - Version management            │
        │ - Deprecation (low score + age)│
        │ - A/B experiment routing       │
        └────────┬───────────────────────┘
                 │
        ┌────────▼───────────────────────┐
        │ Dashboard & Monitoring         │
        │ - Drift alerts                 │
        │ - Experiment results           │
        │ - Deprecation notices          │
        └────────────────────────────────┘
```

## Phases

### Phase 1: Design & Data Models (Days 1-2)

**Deliverables**: Pydantic models, database schema, event design

**Tasks**:

1. Define FeedbackEvent model (Pydantic v2)
   - Fields: pattern_id, trace_id, success, outcome_quality, user_satisfaction, latency_ms, memory_mb, error_code, timestamp, user_context
   - Validation: quality (0-10), satisfaction (0-5), latency ≥ 0

2. Define ConceptDriftAlert model
   - Fields: pattern_id, metric (success_rate | quality | cost), previous_value, current_value, drift_percentage, detection_timestamp

3. Define PatternVersion model
   - Fields: pattern_id, version_number, created_at, promoted_at, deprecated_at, deprecation_reason

4. Define ABExperiment model
   - Fields: experiment_id, pattern_id, version_a, version_b, traffic_split, start_time, end_time, status (running | concluded), winner, p_value, effect_size

5. Create Neo4j schema extensions
   - Node: FeedbackEvent (relations to Pattern, Trace, GIT)
   - Node: ConceptDriftAlert (relations to Pattern)
   - Node: PatternVersion (relations to Pattern)
   - Node: ABExperiment (relations to PatternVersion)

6. Design feedback event buffer (in-memory ring buffer + persistent queue)

### Phase 2: Feedback Pipeline (Days 2-4)

**Deliverables**: Event collection, buffering, deduplication, storage

**Tasks**:

1. Implement FeedbackCollector async service
   - POST /v1/feedback (non-blocking, buffered)
   - Deduplication: (trace_id + pattern_id) → only latest event
   - Validation: ensure all required fields present
   - Retention: 90-day sliding window (auto-delete old events)

2. Implement FeedbackBuffer
   - In-memory ring buffer (K=50 events, auto-flush when full)
   - Time-based flush: every T=10 seconds
   - Error handling: dead-letter queue for failed events

3. Implement batch aggregation
   -Aggregate events per pattern: success_rate, avg outcome_quality, avg user_satisfaction
   - Time-decay weighting: recent events 2x weight
   - Persist to Neo4j: PatternMetrics node

4. Integration tests
   - Send 100 feedback events, verify 50-event batching
   - Send duplicates (same trace_id), verify dedup
   - Verify 90-day retention policy

### Phase 3: Drift Detection & Re-Ranking (Days 4-6)

**Deliverables**: Concept drift metrics, re-ranking triggers, Phase 3.2 integration

**Tasks**:

1. Implement ConceptDriftDetector
   - Query 30-day window metrics (success_rate, quality, cost)
   - Query 30-60 day window metrics
   - Calculate drift: (new - old) / old × 100
   - Threshold: >15% → drift alert

2. Implement re-ranking trigger
   - Trigger 1: Event-based (every K=50 events) [async, non-blocking]
   - Trigger 2: Drift-based (when ConceptDriftAlert created) [priority]
   - Trigger 3: Manual API endpoint

3. Implement Phase 3.2 integration
   - Call batch_rank_patterns() with updated feedback context
   - Update RankedPattern scores in Neo4j
   - Keep history: (pattern_id, old_rank, new_rank, reason, timestamp)

4. Implement graceful degradation
   - If ranking fails: keep previous ranks
   - If drift detection unavailable: continue without alerts
   - Retry logic: exponential backoff

5. Integration tests
   - Create pattern with trending down success_rate
   - Verify drift alert created after 30 events
   - Verify re-ranking triggered with new scores

### Phase 4: A/B Testing Framework (Days 6-7)

**Deliverables**: Experiment creation, routing logic, statistical testing

**Tasks**:

1. Implement ABExperimentManager
   - Create experiment: pattern_id, version_a, version_b, traffic_split (default 50/50)
   - Validate: min sample size (500+), min duration (7 days)

2. Implement traffic routing
   - Hash-based routing: hash(trace_id + experiment_id) % 100 < traffic_split
   - Deterministic (same trace always gets same variant)
   - Fallback: if experiment expired, use winner version

3. Implement statistical testing
   - Collect separate feedback per variant
   - t-test: compare effectiveness_score between variants
   - Calculate p-value, effect size (Cohen's d)
   - Conclusion threshold: p < 0.05 + min 500 samples per variant

4. Implement auto-promotion
   - If version_b significantly better: promote to production
   - Deprecate version_a (mark deprecated_reason = "superseded")
   - Update rankings to use new version

5. Integration tests
   - Create A/B experiment with synthetic patterns
   - Route 50/50 traffic
   - Verify statistical significance calculated correctly

### Phase 5: Pattern Lifecycle & Monitoring (Days 7-8)

**Deliverables**: Deprecation logic, audit trail, monitoring dashboard

**Tasks**:

1. Implement pattern deprecation
   - Query patterns with effectiveness_score < 0.3 for 60+ days
   - Auto-deprecate with reason "low_effectiveness_aged"
   - Audit event: (pattern_id, deprecated_at, reason, replacement_pattern_id)

2. Implement version management
   - Track pattern → [v1, v2, v3...] relationships
   - Assign version_number on creation
   - Superseded relationship: v1 → superseded_by v2

3. Implement audit trail
   - Log all pattern changes: created, promoted, deprecated, superseded
   - Include: timestamp, reason, actor (system | admin), affected patterns

4. Implement monitoring dashboard endpoints
   - GET /v1/monitoring/drift-alerts (recent alerts, trending patterns)
   - GET /v1/monitoring/experiments (active + concluded experiments)
   - GET /v1/monitoring/deprecations (lifecycle events)

5. Implement alerting
   - Email alert: concept drift detected for pattern_id
   - Dashboard alert: A/B experiment ready for promotion
   - Audit log: all lifecycle events queryable

6. Integration tests
   - Create deprecated pattern, verify read-only
   - Promote new version, verify old version marked superseded
   - Query audit trail, verify all events logged

## Event Bus Architecture

### Technology Selection

| Technology | Pros | Cons | Recommendation |
|------------|------|------|----------------|
| **Redis Streams** | Simple, existing infra, fast | Limited persistence, no replay | **MVP Choice** |
| **RabbitMQ** | Mature, routing, reliable | Single point of failure, ops overhead | Alternative |
| **Kafka** | Scalable, durable, replay | Complex ops, overkill for MVP | Future upgrade |
| **AWS SNS/SQS** | Managed, scalable | Vendor lock-in, cost | Cloud option |

**Decision**: Use **Redis Streams** for MVP, migrate to Kafka when scaling beyond 10K events/sec.

### Event Bus Design

```text
┌─────────────────────────────────────────────────────────────────┐
│                     EVENT BUS (Redis Streams)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Stream: grimoire:feedback:events                              │
│  ├─ pattern_id                                                 │
│  ├─ trace_id                                                   │
│  ├─ event_type: EXECUTION_SUCCESS | EXECUTION_FAILURE          │
│  ├─ payload: JSON (FeedbackEvent)                              │
│  └─ timestamp                                                  │
│                                                                 │
│  Stream: grimoire:drift:alerts                                 │
│  ├─ pattern_id                                                 │
│  ├─ drift_type: EFFECTIVENESS | QUALITY | COST                │
│  ├─ severity: WARNING | CRITICAL                               │
│  └─ timestamp                                                  │
│                                                                 │
│  Stream: grimoire:ab:experiments                               │
│  ├─ experiment_id                                              │
│  ├─ event_type: VARIANT_A | VARIANT_B | CONCLUSION             │
│  └─ timestamp                                                  │
│                                                                 │
│  Consumer Groups:                                              │
│  ├─ feedback-processors (3 instances)                          │
│  ├─ drift-detectors (2 instances)                            │
│  └─ ab-test-routers (2 instances)                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Event Schema

```python
from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class BusEvent(BaseModel):
    """Base event for event bus."""

    event_id: str = Field(
        default_factory=lambda: f"evt_{uuid.uuid4().hex[:16]}"
    )
    event_type: str = Field(
        description="Type of event"
    )
    stream: str = Field(
        description="Stream name"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat()
    )
    payload: dict = Field(
        description="Event payload"
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Tracing, user context, etc."
    )

class FeedbackBusEvent(BusEvent):
    """Feedback event for event bus."""

    event_type: Literal["FEEDBACK"] = "FEEDBACK"
    stream: str = "grimoire:feedback:events"
    payload: FeedbackEvent

class DriftBusEvent(BusEvent):
    """Drift alert event."""

    event_type: Literal["DRIFT_DETECTED"] = "DRIFT_DETECTED"
    stream: str = "grimoire:drift:alerts"
    payload: ConceptDriftAlert

class ABTestBusEvent(BusEvent):
    """A/B test routing event."""

    event_type: Literal["EXPERIMENT_ROUTING"] = "EXPERIMENT_ROUTING"
    stream: str = "grimoire:ab:experiments"
    payload: dict = Field(
        description="{experiment_id, pattern_id, variant, trace_id}"
    )
```

### Producer API

```python
class EventBusProducer:
    """Produce events to Redis Streams."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def publish_feedback(
        self, 
        feedback: FeedbackEvent,
        metadata: Optional[dict] = None
    ) -> str:
        """Publish feedback event."""
        event = FeedbackBusEvent(
            payload=feedback.dict(),
            metadata=metadata
        )

        event_id = self.redis.xadd(
            "grimoire:feedback:events",
            event.dict(),
            maxlen=100000  # Keep last 100K events
        )
        return event_id

    async def publish_drift_alert(
        self,
        alert: ConceptDriftAlert
    ) -> str:
        """Publish drift alert."""
        event = DriftBusEvent(payload=alert.dict())

        event_id = self.redis.xadd(
            "grimoire:drift:alerts",
            event.dict(),
            maxlen=10000
        )
        return event_id
```

### Consumer API

```python
class EventBusConsumer:
    """Consume events from Redis Streams."""

    def __init__(
        self,
        redis_client: redis.Redis,
        consumer_group: str,
        consumer_name: str
    ):
        self.redis = redis_client
        self.group = consumer_group
        self.name = consumer_name

    async def consume_feedback(
        self,
        handler: Callable[[FeedbackEvent], Awaitable[None]],
        batch_size: int = 50
    ):
        """Consume feedback events."""
        while True:
            # Read from stream
            messages = self.redis.xreadgroup(
                groupname=self.group,
                consumername=self.name,
                streams={"grimoire:feedback:events": ">"},
                count=batch_size,
                block=5000  # 5 second timeout
            )

            for stream, events in messages:
                for event_id, fields in events:
                    try:
                        # Parse event
                        event = FeedbackBusEvent(**fields)
                        feedback = FeedbackEvent(**event.payload)

                        # Process
                        await handler(feedback)

                        # Acknowledge
                        self.redis.xack(
                            "grimoire:feedback:events",
                            self.group,
                            event_id
                        )
                    except Exception as e:
                        # Log error, don't ack (will be retried)
                        logger.error(f"Failed to process {event_id}: {e}")

    async def claim_pending(
        self,
        min_idle_time: int = 60000  # 60 seconds
    ):
        """Claim pending messages from failed consumers."""
        pending = self.redis.xpending_range(
            "grimoire:feedback:events",
            self.group,
            min=min_idle_time,
            count=10
        )

        for item in pending:
            # Claim and reprocess
            claimed = self.redis.xclaim(
                "grimoire:feedback:events",
                self.group,
                self.name,
                min_idle_time,
                [item['message_id']]
            )
            # Process claimed messages...
```

### Buffer Overflow Handling

```python
class FeedbackBuffer:
    """In-memory buffer with overflow protection."""

    def __init__(
        self,
        max_size: int = 50,
        overflow_strategy: str = "drop_oldest"
    ):
        self.buffer = deque(maxlen=max_size)
        self.overflow_strategy = overflow_strategy
        self.dropped_count = 0

    async def add(self, event: FeedbackEvent) -> bool:
        """Add event to buffer."""
        if len(self.buffer) >= self.max_size:
            if self.overflow_strategy == "drop_oldest":
                self.buffer.popleft()
                self.dropped_count += 1
            elif self.overflow_strategy == "trigger_flush":
                await self.flush()
            elif self.overflow_strategy == "alert":
                await alert_ops("feedback_buffer_full")
                return False

        self.buffer.append(event)
        return True

    async def flush(self):
        """Flush buffer to event bus."""
        batch = list(self.buffer)
        self.buffer.clear()

        # Publish to Redis
        for event in batch:
            await self.producer.publish_feedback(event)
```

### Monitoring

```python
# Metrics to expose
EVENT_BUS_METRICS = {
    "events_produced_total": Counter,
    "events_consumed_total": Counter,
    "events_failed_total": Counter,
    "consumer_lag": Gauge,  # Pending messages
    "buffer_size": Gauge,
    "buffer_dropped_total": Counter,
    "processing_latency": Histogram
}
```

## Dependencies

### Internal Dependencies

- **Phase 1 (Canonical Schema)**: Pattern, TraceBundle models
- **Phase 2.1 (Danger)**: Consider danger scores in deprecation policy
- **Phase 2.2 (FSM)**: Segment drift detection by FSM type
- **Phase 3.1 (Extraction)**: Pattern execution feedback
- **Phase 3.2 (Ranking)**: Re-rank API, RankedPattern model

### External Dependencies

- **Neo4j 5.x**: Graph persistence, pattern versioning relationships
- **Redis 7.x**: Event bus (streams), caching
- **Pydantic v2**: Data validation
- **scipy/numpy**: Statistical testing (t-test, effect size)

## Success Metrics

1. **Feedback Quality**
   - 99.9% collection reliability (no loss)
   - <10ms latency per feedback event
   - Deduplication working correctly (verified via audit logs)

2. **Drift Detection**
   - 100% catch rate (all drifting patterns detected within 24h)
   - Zero false positives (threshold validated against manual inspection)
   - Alert latency <5 min from drift occurrence

3. **Re-Ranking**
   - Triggered within 5 min of drift detection
   - <30s ranking latency for 1000 patterns (async)
   - Ranking updates reflected in next retrieval

4. **A/B Testing**
   - Statistical significance achieved for 80%+ experiments (t-test p < 0.05)
   - No winner declarations < 500 samples per variant
   - Effect size meaningful (Cohen's d > 0.2 for promotion)

5. **Pattern Lifecycle**
   - 100% audit trail (all changes logged + queryable)
   - Deprecated patterns remain readable (backward compat)
   - No accidental deletions (soft deprecation only)

## Timeline

- **Days 1-2**: Design & data models (Design review EOD Day 2)
- **Days 2-4**: Feedback pipeline + integration (Functional demo Day 4)
- **Days 4-6**: Drift detection + re-ranking (Integration test Day 6)
- **Days 6-7**: A/B testing framework (A/B experiment demo Day 7)
- **Days 7-8**: Lifecycle + monitoring (Performance benchmark, monitoring demo Day 8)

**Estimated Effort**: 7-10 days

## Risks & Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Feedback event loss | Low | High | Persistent queue (dead-letter) + monitoring |
| False drift alerts | Medium | High | High threshold (15%), manual validation |
| Statistical type I error | Low | High | Require p < 0.05 + min 500 samples |
| Pattern versioning complexity | Medium | Medium | Clear versioning schema, audit trail |
| Dashboard latency | Medium | Medium | Pre-compute metrics, cache rankings |

## Handoff Outputs

**Outputs to Future Phases**:

- FeedbackEvent + ConceptDriftAlert data (for Phase 3.4 ML-based pattern retraining)
- A/B experiment results + winner patterns (for Phase 4 recommendations)
- Audit trail (for compliance + knowledge reuse)

**Inputs Used**:

- Pattern execution results (Phase 3.1-3.2)
- Danger/FSM context (Phase 2.1-2.2)
- Ranking API (Phase 3.2)
