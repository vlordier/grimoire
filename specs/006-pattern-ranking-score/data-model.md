# Data Models: Pattern Ranking

All models use **Pydantic v2** with strict validation.

---

## Core Models

### `RankedPattern` (Primary Output)

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum
import uuid

class SafetyLevel(str, Enum):
    """Safety classification based on danger scores."""
    CRITICAL = "critical"   # Never recommend, escalate
    HIGH = "high"            # Recommend with caution alert
    MEDIUM = "medium"        # Recommend with warning
    LOW = "low"              # Recommend with note
    SAFE = "safe"            # Recommend freely

class RankedPattern(BaseModel):
    """Pattern with all ranking scores and final rank."""
    
    pattern_id: str = Field(
        description="Pattern being ranked (from Phase 3.1)"
    )
    
    # Component scores (all 0-1 range)
    effectiveness_score: float = Field(
        ge=0, le=1.0,
        description="How well does pattern work? "
        "(success_rate + quality + satisfaction weighted)"
    )
    
    safety_score: float = Field(
        ge=0, le=1.0,
        description="How safe is pattern? "
        "(mapped from Phase 2.1 DangerScore)"
    )
    safety_level: SafetyLevel = Field(
        description="Danger classification: CRITICAL→0, HIGH→0.25, etc."
    )
    
    relevance_score: float = Field(
        ge=0, le=1.0,
        description="How relevant to current context? "
        "(FSM type match from Phase 2.2)"
    )
    
    cost_score: float = Field(
        ge=0, le=1.0,
        description="How efficient is pattern? "
        "(1/(1 + cost_metric) where cost is latency + memory + error)"
    )
    
    # Final ranking
    final_rank_score: float = Field(
        ge=0, le=1.0,
        description="Weighted sum: 0.4×eff + 0.3×safe + 0.2×rel + 0.1×cost"
    )
    
    # Explanations (for debugging + UI)
    score_breakdown: dict = Field(
        description="Detailed breakdown: "
        "{'effectiveness': {...}, 'safety': {...}, ...}"
    )
    
    # Context
    fsm_type: Optional[str] = Field(
        default=None,
        description="Current FSM type (from Phase 2.2), used for relevance"
    )
    domain_context: Optional[str] = Field(
        default=None,
        description="Current domain (ML, finance, etc.), optional"
    )
    
    # Metadata
    ranked_at: str = Field(
        description="ISO8601 timestamp when ranking was computed"
    )
    ranking_version: int = Field(
        ge=1,
        description="Ranking algorithm version (for tracking changes)"
    )
    
    class Config:
        use_enum_values = False
```

---

### `RankingContext`

```python
class RankingContext(BaseModel):
    """Input context for ranking operation."""
    
    current_fsm_type: Optional[str] = Field(
        default=None,
        description="Current FSM state (e.g., DECISION, ITERATION)"
    )
    
    current_domain: Optional[str] = Field(
        default=None,
        description="Current problem domain (ml, finance, etc.)"
    )
    
    danger_scores: Optional[List['DangerScore']] = Field(
        default=None,
        description="Pre-computed danger scores from Phase 2.1. "
        "If missing, assume all SAFE."
    )
    
    execution_context: Optional[dict] = Field(
        default=None,
        description="Additional context (user_id, request_id, etc.)"
    )
```

---

### `DangerScore` (Input from Phase 2.1)

```python
class DangerScore(BaseModel):
    """Danger classification output from Phase 2.1."""
    
    pattern_id: str
    danger_types: List[str] = Field(
        description="Detected danger types: CRITICAL, HIGH, MEDIUM, LOW"
    )
    severity: float = Field(
        ge=0, le=1.0,
        description="Overall severity score (0=safe, 1=critical)"
    )
    reason: Optional[str] = Field(
        default=None,
        description="Human-readable explanation"
    )
```

---

### `RankingOutput`

```python
class RankingOutput(BaseModel):
    """API response from ranking operation."""
    
    ranking_id: str = Field(
        default_factory=lambda: f"rank_{uuid.uuid4().hex[:12]}"
    )
    
    ranked_patterns: List[RankedPattern] = Field(
        description="Patterns sorted by final_rank_score (desc)"
    )
    
    context_used: RankingContext = Field(
        description="Context that was applied"
    )
    
    # Stats
    num_ranked: int = Field(ge=0)
    num_critical: int = Field(
        ge=0,
        description="Patterns with CRITICAL danger level"
    )
    num_safe: int = Field(
        ge=0,
        description="Patterns with SAFE danger level"
    )
    
    avg_rank_score: float = Field(
        ge=0, le=1.0,
        description="Average final_rank_score"
    )
    
    # Performance
    ranking_duration_ms: float = Field(ge=0)
    ranked_at: str = Field(description="ISO8601")
```

---

### `RankingHistory`

```python
class RankingSnapshot(BaseModel):
    """Single ranking snapshot in history."""
    pattern_id: str
    final_rank_score: float
    effectiveness_score: float
    safety_score: float
    relevance_score: float
    cost_score: float
    ranked_at: str

class RankingHistory(BaseModel):
    """Historical tracking of pattern rankings over time."""
    
    pattern_id: str
    snapshots: List[RankingSnapshot] = Field(
        description="Time-ordered ranking snapshots"
    )
    
    # Trend analysis
    avg_rank_score_7d: Optional[float] = Field(
        default=None,
        description="7-day moving average"
    )
    trend: Optional[str] = Field(
        default=None,
        description="IMPROVING, STABLE, DEGRADING"
    )
    
    last_updated: str = Field(description="ISO8601")
```

---

## API Models

### `BatchRankRequest`

```python
class BatchRankRequest(BaseModel):
    """API request for batch ranking."""
    
    pattern_ids: List[str] = Field(
        min_items=1, max_items=1000000,
        description="Patterns to rank"
    )
    
    context: RankingContext = Field(
        description="Ranking context (FSM type, domain, danger scores)"
    )
    
    include_metadata: bool = Field(
        default=True,
        description="Include score_breakdown (verbose)"
    )
    
    limit_top_k: Optional[int] = Field(
        default=None,
        description="Return only top-K patterns (for performance)"
    )
```

### `BatchRankResponse`

```python
class BatchRankResponse(BaseModel):
    """API response from batch ranking."""
    
    ranking_id: str
    ranked_patterns: List[RankedPattern]
    
    stats: dict = Field(
        description="Aggregated stats (num_critical, avg_score, etc.)"
    )
    
    ranking_duration_ms: float
    ranked_at: str
```

---

## Neo4j Schema

### Nodes

```cypher
# RankedPattern node
CREATE (rp:RankedPattern {
    pattern_id: String,
    final_rank_score: Float,
    effectiveness_score: Float,
    safety_score: Float,
    relevance_score: Float,
    cost_score: Float,
    safety_level: String,  # CRITICAL, HIGH, MEDIUM, LOW, SAFE
    ranked_at: DateTime,
    ranking_version: Integer
})

# RankingSnapshot node (historical)
CREATE (rs:RankingSnapshot {
    snapshot_id: String,
    pattern_id: String,
    final_rank_score: Float,
    effectiveness_score: Float,
    ranked_at: DateTime
})
```

### Relationships

```cypher
# Pattern → RankedPattern (current ranking)
MATCH (p:Pattern), (rp:RankedPattern)
CREATE (p)-[:HAS_RANKING {version: Integer}]->(rp)

# RankedPattern → RankingSnapshot (history)
MATCH (rp:RankedPattern), (rs:RankingSnapshot)
CREATE (rp)-[:RANKING_HISTORY {sequence: Integer}]->(rs)

# RankedPattern → DangerScore (safety data from Phase 2.1)
MATCH (rp:RankedPattern), (ds:DangerScore)
CREATE (rp)-[:ASSESSED_BY]->(ds)

# RankedPattern → FSMType (relevance context from Phase 2.2)
MATCH (rp:RankedPattern), (fsm:FSMType)
CREATE (rp)-[:RELEVANT_TO_FSM]->(fsm)

# Indexes
CREATE INDEX ranked_score ON RankedPattern(final_rank_score)
CREATE INDEX ranked_pattern ON RankedPattern(pattern_id)
CREATE INDEX ranked_timestamp ON RankedPattern(ranked_at)
CREATE INDEX ranked_safety ON RankedPattern(safety_level)
```

---

## Validation Rules

### RankedPattern Validation

- ✅ All scores: 0-1 range
- ✅ `final_rank_score` ≤ max(component scores) + tolerance (5%)
- ✅ Components must sum to 1.0 (weighted)
- ✅ `safety_level` must match `safety_score` range (0→CRITICAL, 1→SAFE)
- ✅ `pattern_id` is valid and exists

### RankingContext Validation

- ✅ If `fsm_type` provided: must be valid FSM type name
- ✅ If `domain` provided: must be ["ml", "finance", "legal", "healthcare", "general"]
- ✅ If `danger_scores` provided: all must be valid DangerScore objects

### RankingOutput Validation

- ✅ `ranked_patterns`: sorted by `final_rank_score` descending
- ✅ `num_ranked` = len(ranked_patterns)
- ✅ `avg_rank_score` must match actual average of patterns
- ✅ `ranking_duration_ms` ≥ 0

---

## JSON Examples

### RankedPattern Example

```json
{
  "pattern_id": "pat_abc123def456",
  "effectiveness_score": 0.85,
  "safety_score": 0.8,
  "safety_level": "LOW",
  "relevance_score": 0.75,
  "cost_score": 0.9,
  "final_rank_score": 0.82,
  "score_breakdown": {
    "effectiveness": {
      "success_rate": 0.9,
      "avg_quality": 8.5,
      "avg_satisfaction": 4.2,
      "weighted": 0.85
    },
    "safety": {
      "danger_type": "LOW",
      "reason": "minor resource overhead",
      "mapped_score": 0.8
    },
    "relevance": {
      "fsm_match": ["DECISION"],
      "jaccard": 0.75
    },
    "cost": {
      "latency_ms": 45.0,
      "memory_mb": 12.0,
      "error_rate": 0.01,
      "score": 0.9
    }
  },
  "fsm_type": "DECISION",
  "domain_context": "ml",
  "ranked_at": "2026-02-12T15:30:00Z",
  "ranking_version": 1
}
```

### BatchRankResponse Example

```json
{
  "ranking_id": "rank_xyz789",
  "ranked_patterns": [
    {
      "pattern_id": "pat_001",
      "final_rank_score": 0.95,
      "effectiveness_score": 0.9,
      "safety_score": 1.0,
      "relevance_score": 1.0,
      "cost_score": 0.85,
      "safety_level": "SAFE",
      "ranked_at": "2026-02-12T15:30:00Z",
      "ranking_version": 1
    },
    {
      "pattern_id": "pat_002",
      "final_rank_score": 0.82,
      "effectiveness_score": 0.85,
      "safety_score": 0.8,
      "relevance_score": 0.75,
      "cost_score": 0.9,
      "safety_level": "LOW",
      "ranked_at": "2026-02-12T15:30:00Z",
      "ranking_version": 1
    }
  ],
  "stats": {
    "num_ranked": 2,
    "num_critical": 0,
    "num_safe": 1,
    "avg_rank_score": 0.885
  },
  "ranking_duration_ms": 12.5,
  "ranked_at": "2026-02-12T15:30:00Z"
}
```

