# Data Models: Optimization Loop

All models use **Pydantic v2** with strict validation.

---

## Core Models

### `FeedbackEvent`

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import uuid

class FeedbackEvent(BaseModel):
    """Execution feedback for a pattern."""
    
    event_id: str = Field(
        default_factory=lambda: f"fb_{uuid.uuid4().hex[:12]}",
        description="Unique feedback event ID"
    )
    
    # Pattern + Trace
    pattern_id: str = Field(
        description="Pattern that was executed"
    )
    trace_id: str = Field(
        description="Trace where pattern was executed"
    )
    
    # Execution outcome
    success: bool = Field(
        description="Did pattern execution succeed?"
    )
    outcome_quality: Optional[int] = Field(
        default=None, ge=0, le=10,
        description="Quality of outcome (0-10). None if unknown."
    )
    user_satisfaction: Optional[int] = Field(
        default=None, ge=0, le=5,
        description="User satisfaction rating (0-5). None if not rated."
    )
    
    # Performance metrics
    latency_ms: float = Field(
        ge=0,
        description="Execution time in milliseconds"
    )
    memory_mb: Optional[float] = Field(
        default=None, ge=0,
        description="Peak memory usage. None if not measured."
    )
    
    # Error handling
    error_code: Optional[str] = Field(
        default=None,
        description="Error type if failed (e.g., TIMEOUT, OVERFLOW, INVALID_STATE)"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Human-readable error description"
    )
    
    # Context
    domain: Optional[str] = Field(
        default=None,
        description="Problem domain (ml, finance, legal, healthcare, general)"
    )
    fsm_type: Optional[str] = Field(
        default=None,
        description="FSM state when pattern executed"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="User ID (for future multi-tenant)"
    )
    
    # Experiment tracking
    experiment_id: Optional[str] = Field(
        default=None,
        description="A/B experiment ID if applicable"
    )
    experiment_variant: Optional[bool] = Field(
        default=None,
        description="True=treatment (v2), False=control (v1)"
    )
    
    # Lifecycle
    timestamp: str = Field(
        description="ISO8601 timestamp when feedback recorded"
    )
    
    class Config:
        use_enum_values = False

    # Validation
    @field_validator('timestamp')
    @classmethod
    def validate_timestamp(cls, v):
        from dateutil.parser import isoparse
        isoparse(v)  # Validates ISO8601 format
        return v
```

---

### `ConceptDriftAlert`

```python
class ConceptDriftMetric(str, Enum):
    SUCCESS_RATE = "success_rate"
    OUTCOME_QUALITY = "outcome_quality"
    ERROR_RATE = "error_rate"
    COST = "cost_score"

class ConceptDriftAlert(BaseModel):
    """Alert when concept drift detected for a pattern."""
    
    alert_id: str = Field(
        default_factory=lambda: f"drift_{uuid.uuid4().hex[:12]}"
    )
    
    pattern_id: str = Field(
        description="Pattern with detected drift"
    )
    
    # Drift detection
    metric: ConceptDriftMetric = Field(
        description="Which metric drifted?"
    )
    
    # Values
    value_30d_bin: float = Field(
        description="Average value (last 30 days)"
    )
    value_60d_bin: float = Field(
        description="Average value (30-60 days ago)"
    )
    
    drift_percentage: float = Field(
        description="Percentage change: (30d−60d)/60d × 100"
    )
    drift_threshold: float = Field(
        default=15.0,
        description="Threshold for alerting (%)"
    )
    
    # Classification
    severity: str = Field(
        description="LOW (15-25%), MEDIUM (25-50%), HIGH (>50%)"
    )
    
    # Lifecycle
    detection_timestamp: str = Field(
        description="ISO8601 when drift detected"
    )
    alert_status: str = Field(
        default="ACTIVE",
        description="ACTIVE, ACKNOWLEDGED, RESOLVED"
    )
    resolved_timestamp: Optional[str] = Field(
        default=None,
        description="When pattern was re-ranked or manually reviewed"
    )
```

---

### `ABExperiment`

```python
class ExperimentStatus(str, Enum):
    CREATED = "created"
    RUNNING = "running"
    CONCLUDED = "concluded"
    CANCELLED = "cancelled"

class ABExperiment(BaseModel):
    """A/B test comparing pattern versions."""
    
    experiment_id: str = Field(
        default_factory=lambda: f"exp_{uuid.uuid4().hex[:12]}"
    )
    
    # Patterns
    pattern_id: str = Field(
        description="Base pattern ID"
    )
    pattern_id_v1: str = Field(
        description="Version 1 (control, existing)"
    )
    pattern_id_v2: str = Field(
        description="Version 2 (treatment, new)"
    )
    
    # Configuration
    traffic_split: int = Field(
        default=50, ge=1, le=99,
        description="% traffic to v2 (default 50%)"
    )
    
    min_sample_size: int = Field(
        default=500, ge=100,
        description="Min feedback events per variant for conclusion"
    )
    
    # Lifecycle
    start_time: str = Field(
        description="ISO8601 when experiment started"
    )
    end_time: str = Field(
        description="ISO8601 planned end time (min 7 days duration)"
    )
    status: ExperimentStatus = Field(
        default="CREATED"
    )
    
    # Results
    v1_sample_size: Optional[int] = Field(default=None, ge=0)
    v2_sample_size: Optional[int] = Field(default=None, ge=0)
    
    v1_avg_quality: Optional[float] = Field(default=None, ge=0, le=10)
    v2_avg_quality: Optional[float] = Field(default=None, ge=0, le=10)
    
    p_value: Optional[float] = Field(
        default=None, ge=0, le=1.0,
        description="Statistical significance (t-test)"
    )
    effect_size: Optional[float] = Field(
        default=None,
        description="Cohen's d (0.2=small, 0.5=medium, 0.8=large)"
    )
    
    # Conclusion
    winner: Optional[str] = Field(
        default=None,
        description="v1, v2, or None (tie/inconclusive)"
    )
    conclusion_timestamp: Optional[str] = Field(
        default=None,
        description="When experiment concluded"
    )
    
    # Promotion
    auto_promoted: bool = Field(
        default=False,
        description="Was winner automatically promoted?"
    )
```

---

### `PatternVersion`

```python
class VersionStatus(str, Enum):
    CURRENT = "current"
    SUPERSEDED = "superseded"
    DEPRECATED = "deprecated"
    EXPERIMENTAL = "experimental"

class DeprecationReason(str, Enum):
    LOW_EFFECTIVENESS = "low_effectiveness_aged"
    HIGH_ERROR_RATE = "high_error_rate"
    SUPERSEDED = "superseded_by_newer_version"
    MANUAL_REVIEW = "manual_review"
    SAFETY_CONCERN = "safety_concern"

class PatternVersion(BaseModel):
    """Version tracking for patterns."""
    
    version_id: str = Field(
        default_factory=lambda: f"v_{uuid.uuid4().hex[:12]}"
    )
    
    pattern_id: str = Field(
        description="Base pattern ID"
    )
    version_number: int = Field(
        ge=1,
        description="Incremental version: 1, 2, 3, ..."
    )
    
    # Status
    status: VersionStatus = Field(
        default="EXPERIMENTAL"
    )
    
    # Lifecycle
    created_at: str = Field(
        description="ISO8601 when version created"
    )
    promoted_at: Optional[str] = Field(
        default=None,
        description="When promoted to CURRENT"
    )
    deprecated_at: Optional[str] = Field(
        default=None,
        description="When deprecated"
    )
    
    # Deprecation info
    deprecation_reason: Optional[DeprecationReason] = Field(default=None)
    deprecation_reason_detail: Optional[str] = Field(
        default=None,
        description="Additional details (e.g., 'success rate dropped 50%')"
    )
    
    # Relationships
    superseded_by_version_id: Optional[str] = Field(
        default=None,
        description="If SUPERSEDED, which version replaced this?"
    )
    
    # Audit
    promoted_by: Optional[str] = Field(
        default=None,
        description="User ID or system that promoted"
    )
    promoted_reason: Optional[str] = Field(
        default=None,
        description="Why was this version promoted?"
    )
```

---

### `PatternAuditEvent`

```python
class AuditEventType(str, Enum):
    CREATED = "created"
    PROMOTED = "promoted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"
    RERANKED = "reranked"
    DRIFT_DETECTED = "drift_detected"
    EXPERIMENT_STARTED = "experiment_started"
    EXPERIMENT_CONCLUDED = "experiment_concluded"

class PatternAuditEvent(BaseModel):
    """Immutable audit trail for pattern changes."""
    
    event_id: str = Field(
        default_factory=lambda: f"audit_{uuid.uuid4().hex[:12]}"
    )
    
    pattern_id: str
    event_type: AuditEventType
    
    # Event details
    reason: str = Field(
        description="Why did this event occur?"
    )
    details: dict = Field(
        description="Event-specific data (flexible JSON)"
    )
    
    # Audit
    actor: str = Field(
        default="system",
        description="User ID or 'system' for automated actions"
    )
    timestamp: str = Field(
        description="ISO8601"
    )
```

---

## API Models

### `FeedbackRequest`

```python
class FeedbackRequest(BaseModel):
    """API request to submit feedback."""
    
    pattern_id: str = Field(
        description="Pattern being evaluated"
    )
    trace_id: str = Field(
        description="Trace where pattern executed"
    )
    
    success: bool
    outcome_quality: Optional[int] = Field(None, ge=0, le=10)
    user_satisfaction: Optional[int] = Field(None, ge=0, le=5)
    
    latency_ms: float = Field(ge=0)
    memory_mb: Optional[float] = Field(None, ge=0)
    
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    
    domain: Optional[str] = None
    fsm_type: Optional[str] = None
    user_id: Optional[str] = None
    
    experiment_id: Optional[str] = None
    experiment_variant: Optional[bool] = None
```

### `ABExperimentRequest`

```python
class ABExperimentRequest(BaseModel):
    """API request to create A/B experiment."""
    
    pattern_id: str
    pattern_id_v1: str
    pattern_id_v2: str
    
    traffic_split: int = Field(default=50, ge=1, le=99)
    min_sample_size: int = Field(default=500, ge=100)
    duration_days: int = Field(default=7, ge=1)
```

### `MonitoringDashboard`

```python
class DriftAlertSummary(BaseModel):
    active_alerts: int
    recent_alerts: List[ConceptDriftAlert]
    
class ExperimentSummary(BaseModel):
    running_experiments: int
    concluded_experiments: int
    avg_winner_effect_size: float

class MonitoringDashboard(BaseModel):
    """Aggregate monitoring data."""
    
    total_patterns: int
    patterns_drifting: int
    patterns_deprecated: int
    
    drift_alerts: DriftAlertSummary
    experiments: ExperimentSummary
    
    feedback_rate: float = Field(
        description="Events per hour"
    )
    reranking_frequency: int = Field(
        description="Re-rankings per day"
    )
    
    dashboard_generated_at: str
```

---

## Neo4j Schema

### Nodes

```cypher
CREATE (fe:FeedbackEvent {
    event_id: String,
    pattern_id: String,
    trace_id: String,
    success: Boolean,
    outcome_quality: Integer,
    latency_ms: Float,
    timestamp: DateTime
})

CREATE (da:ConceptDriftAlert {
    alert_id: String,
    pattern_id: String,
    metric: String,
    drift_percentage: Float,
    detection_timestamp: DateTime,
    alert_status: String
})

CREATE (ae:ABExperiment {
    experiment_id: String,
    pattern_id: String,
    pattern_id_v1: String,
    pattern_id_v2: String,
    traffic_split: Integer,
    status: String,
    winner: String,
    p_value: Float,
    conclusion_timestamp: DateTime
})

CREATE (pv:PatternVersion {
    version_id: String,
    pattern_id: String,
    version_number: Integer,
    status: String,
    created_at: DateTime,
    promoted_at: DateTime,
    deprecated_at: DateTime
})

CREATE (audit:PatternAuditEvent {
    event_id: String,
    pattern_id: String,
    event_type: String,
    timestamp: DateTime
})
```

### Relationships

```cypher
# Pattern → FeedbackEvent (many)
MATCH (p:Pattern), (fe:FeedbackEvent)
CREATE (p)-[:RECEIVED_FEEDBACK]->(fe)

# Pattern → ConceptDriftAlert (many)
MATCH (p:Pattern), (da:ConceptDriftAlert)
CREATE (p)-[:HAS_DRIFT_ALERT]->(da)

# ABExperiment → PatternVersion (v1 and v2)
MATCH (ae:ABExperiment), (pv:PatternVersion)
CREATE (ae)-[:COMPARES_VERSION {variant: 1}]->(pv)

# PatternVersion → PatternVersion (supersedence)
MATCH (pv1:PatternVersion), (pv2:PatternVersion)
CREATE (pv1)-[:SUPERSEDED_BY]->(pv2)

# Pattern → PatternAuditEvent
MATCH (p:Pattern), (audit:PatternAuditEvent)
CREATE (p)-[:AUDIT_TRAIL]->(audit)

# Indexes
CREATE INDEX fe_pattern ON FeedbackEvent(pattern_id)
CREATE INDEX fe_timestamp ON FeedbackEvent(timestamp)
CREATE INDEX drift_status ON ConceptDriftAlert(alert_status)
CREATE INDEX exp_status ON ABExperiment(status)
CREATE INDEX pv_pattern ON PatternVersion(pattern_id)
```

---

## Validation Rules

### FeedbackEvent
- ✅ `pattern_id` must be valid Pattern
- ✅ `success` + `outcome_quality` consistency (quality usually missing if failed)
- ✅ `latency_ms` ≥ 0
- ✅ Timestamp is ISO8601

### ABExperiment
- ✅ `end_time` ≥ `start_time` + 7 days
- ✅ `traffic_split` ∈ [1, 99] (not 0 or 100)
- ✅ `min_sample_size` ≥ 100
- ✅ Variants differ: `pattern_id_v1` ≠ `pattern_id_v2`

### PatternVersion
- ✅ `version_number` continuous (no gaps)
- ✅ Status transitions valid (EXPERIMENTAL→CURRENT, etc.)
- ✅ Deprecation reason required if DEPRECATED

