# Data Models: Pattern Extraction

All models use **Pydantic v2** with strict validation.

---

## Core Models

### `Pattern` (Primary)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Set
from enum import Enum
import uuid

class PatternTarget(str, Enum):
    """What type of graph node does this pattern match?"""
    DECISION = "decision_step"
    ITERATION = "iteration_loop"
    BRANCHING = "branch"
    FILTER = "filter_operation"
    AGGREGATE = "aggregate_operation"
    TRANSFORM = "transform_operation"
    END = "end_node"

class Pattern(BaseModel):
    """Reusable reasoning pattern extracted from traces."""

    pattern_id: str = Field(
        default_factory=lambda: f"pat_{uuid.uuid4().hex[:12]}",
        description="Unique pattern identifier"
    )

    # Graph structure
    nodes: List[dict] = Field(
        description="List of nodes in the pattern graph. "
        "Each: {id, type, properties}. "
        "Canonical form (sorted by degree + adjacency)."
    )
    edges: List[dict] = Field(
        description="List of edges in the pattern graph. "
        "Each: {source_id, target_id, relation_type}. "
        "Sorted edge list for determinism."
    )

    # Metadata
    targets: Set[PatternTarget] = Field(
        description="What types of nodes/operations does this pattern match?"
    )
    fsm_types: Set[str] = Field(
        default_factory=set,
        description="FSM types where this pattern appears "
        "(e.g., DECISION, ITERATION). From Phase 2.2."
    )
    domains: Set[str] = Field(
        default_factory=set,
        description="Problem domains: ml, finance, legal, healthcare, general"
    )

    # Performance metrics
    success_rate: float = Field(
        ge=0.0, le=1.0,
        description="Proportion of traces where pattern succeeded (0-1)"
    )
    avg_outcome_quality: float = Field(
        ge=0.0, le=10.0,
        description="Average outcome quality when pattern applied (0-10)"
    )

    cost_profile: Optional['CostProfile'] = Field(
        default=None,
        description="Execution cost: latency, memory, errors"
    )

    # Lifecycle
    num_matching_traces: int = Field(
        ge=0,
        description="How many traces contain this pattern?"
    )
    first_discovered: str = Field(
        description="ISO8601 timestamp when pattern was first extracted"
    )
    last_updated: str = Field(
        description="ISO8601 timestamp of last update"
    )

    # De-duplication tracking
    canonical_hash: str = Field(
        description="SHA256 hash of canonical form (for dedup)"
    )
    merged_from: List[str] = Field(
        default_factory=list,
        description="Pattern IDs that were merged into this one (fuzzy dedup)"
    )

    version: int = Field(
        default=1,
        ge=1,
        description="Version number (incremented on promotion)"
    )

    class Config:
        use_enum_values = False
```

---

### `CostProfile`

```python
class CostProfile(BaseModel):
    """Execution cost metrics for a pattern."""

    latency_ms: float = Field(
        ge=0,
        description="Average execution latency (milliseconds)"
    )
    latency_p95_ms: float = Field(
        ge=0,
        description="95th percentile latency"
    )
    memory_peak_mb: float = Field(
        ge=0,
        description="Peak memory usage (megabytes)"
    )
    error_rate: float = Field(
        ge=0, le=1.0,
        description="Proportion of executions that failed (0-1)"
    )
    error_types: Optional[dict] = Field(
        default=None,
        description="Categorized errors: {error_type: count, ...}"
    )

    # Derived
    cost_score: float = Field(
        ge=0,
        description="Normalized cost score (0=cheap, 1=expensive). "
        "Calculated as: (lat_ms/1000 + mem_mb/100 + err*10) / 3"
    )

    sample_size: int = Field(
        ge=1,
        description="Number of executions sampled"
    )
```

---

### `PatternMatch`

```python
class PatternMatch(BaseModel):
    """A single occurrence of a pattern in a trace."""

    match_id: str = Field(
        default_factory=lambda: f"m_{uuid.uuid4().hex[:12]}",
        description="Unique match identifier"
    )
    pattern_id: str = Field(description="Pattern that matched")
    trace_id: str = Field(description="TraceBundle ID containing match")

    # Match details
    matched_node_ids: List[str] = Field(
        description="Step IDs from trace that matched pattern nodes"
    )
    matched_edge_ids: List[str] = Field(
        description="Edge indices from trace that matched pattern edges"
    )

    # Quality
    similarity_score: float = Field(
        ge=0, le=1.0,
        description="How closely does this match the pattern? (0=poor, 1=exact)"
    )

    # Outcome
    execution_successful: bool = Field(
        description="Did execution succeed at this match?"
    )
    outcome_quality: Optional[float] = Field(
        ge=0, le=10.0,
        description="Quality of outcome at this match (0-10, None if unknown)"
    )

    timestamp: str = Field(
        description="When was this match discovered (ISO8601)"
    )
```

---

### `ExtractionResult`

```python
class ExtractionResult(BaseModel):
    """Output of pattern extraction operation."""

    extraction_id: str = Field(
        default_factory=lambda: f"ext_{uuid.uuid4().hex[:12]}"
    )

    # Results
    patterns_extracted: List[Pattern] = Field(
        description="List of extracted patterns"
    )
    matches_found: List[PatternMatch] = Field(
        description="All pattern matches in input traces"
    )

    # Stats
    num_input_traces: int = Field(ge=1)
    num_patterns: int = Field(ge=0)
    num_matches: int = Field(ge=0)
    num_dedup_merged: int = Field(
        ge=0,
        description="How many patterns were merged during fuzzy dedup?"
    )

    # Quality metrics
    avg_pattern_size: float = Field(
        description="Average nodes per pattern"
    )
    avg_success_rate: float = Field(
        ge=0, le=1.0,
        description="Average pattern success rate"
    )
    coverage: float = Field(
        ge=0, le=1.0,
        description="Proportion of traces covered by at least one pattern"
    )

    # Performance
    extraction_duration_sec: float = Field(ge=0)
    dedup_duration_sec: float = Field(ge=0)
    total_duration_sec: float = Field(ge=0)

    # Metadata
    extraction_timestamp: str = Field(description="ISO8601")
    parameters: dict = Field(
        description="Extraction parameters used: "
        "{min_frequency, max_size, similarity_threshold, ...}"
    )
```

---

## API Models

### `ExtractionRequest`

```python
class ExtractionRequest(BaseModel):
    """API request for pattern extraction."""

    trace_ids: List[str] = Field(
        min_items=1, max_items=100000,
        description="Trace IDs to extract patterns from"
    )

    min_frequency: int = Field(
        default=5, ge=1,
        description="Min traces containing pattern (5 = top 0.05% of 10K)"
    )
    max_pattern_size: int = Field(
        default=10, ge=2, le=50,
        description="Max nodes in pattern (balance: coverage vs complexity)"
    )

    similarity_threshold: float = Field(
        default=0.9, ge=0.0, le=1.0,
        description="Jaccard threshold for fuzzy dedup (0.9 = very similar)"
    )

    include_cost_profile: bool = Field(
        default=True,
        description="Compute cost profile for each pattern?"
    )

    include_metadata: bool = Field(
        default=True,
        description="Extract targets, fsm_types, domains?"
    )
```

### `ExtractionResponse`

```python
class ExtractionResponse(BaseModel):
    """API response for pattern extraction."""

    extraction_id: str
    status: str = Field(
        description="SUCCESS | IN_PROGRESS | FAILED"
    )
    result: Optional[ExtractionResult] = Field(
        default=None,
        description="Full result (null if still processing)"
    )

    error: Optional[str] = Field(default=None)

    # For long-running requests
    progress_percent: int = Field(
        default=0, ge=0, le=100,
        description="Extraction progress (0-100%)"
    )
    eta_seconds: Optional[int] = Field(
        default=None,
        description="Estimated time to completion"
    )
```

---

## Neo4j Schema

### Nodes

```cypher
# Pattern node
CREATE (p:Pattern {
    pattern_id: String,
    canonical_hash: String,
    num_matching_traces: Integer,
    success_rate: Float,
    avg_outcome_quality: Float,
    version: Integer,
    created_at: DateTime,
    updated_at: DateTime
})

# PatternMatch node
CREATE (m:PatternMatch {
    match_id: String,
    pattern_id: String,
    trace_id: String,
    similarity_score: Float,
    execution_successful: Boolean,
    outcome_quality: Float,
    discovered_at: DateTime
})

# PatternVersion node (for lifecycle tracking)
CREATE (v:PatternVersion {
    version_id: String,
    pattern_id: String,
    version_number: Integer,
    promoted_at: DateTime,
    deprecated_at: DateTime,
    deprecation_reason: String
})
```

### Relationships

```cypher
# Pattern→Pattern (merged)
MATCH (p1:Pattern), (p2:Pattern)
CREATE (p1)-[:MERGED_INTO {similarity: Float}]->(p2)

# Pattern→Trace (matches)
MATCH (p:Pattern), (t:TraceBundle)
CREATE (p)-[:MATCHES_TRACE {num_matches: Integer}]->(t)

# Pattern→FSMType
MATCH (p:Pattern)
CREATE (p)-[:APPLIES_TO_FSM_TYPE {fsm_type: String}]->(fsm:FSMType)

# Pattern→PatternVersion
MATCH (p:Pattern), (v:PatternVersion)
CREATE (p)-[:HAS_VERSION {version_number: Integer}]->(v)

# PatternMatch→Step (node mapping)
MATCH (m:PatternMatch), (s:Step)
CREATE (m)-[:MATCHES_STEP {pattern_node_id: String}]->(s)

# Index for performance
CREATE INDEX pattern_hash ON Pattern(canonical_hash)
CREATE INDEX pattern_success ON Pattern(success_rate)
CREATE INDEX pattern_fsm ON Pattern(fsm_types)
CREATE INDEX match_pattern ON PatternMatch(pattern_id)
CREATE INDEX match_trace ON PatternMatch(trace_id)
```

---

## Validation Rules

### Pattern Validation

- ✅ `pattern_id`: non-empty, unique
- ✅ `nodes`: at least 2
- ✅ `edges`: at least 1
- ✅ Edges reference valid node IDs
- ✅ Graph is connected (all nodes reachable)
- ✅ `success_rate`: 0-1
- ✅ `num_matching_traces`: ≥ min_frequency parameter
- ✅ `canonical_hash`: SHA256, 64 characters

### CostProfile Validation

- ✅ `latency_ms` ≤ `latency_p95_ms`
- ✅ `error_rate`: 0-1
- ✅ `cost_score`: 0-10
- ✅ `sample_size` ≥ 1

### PatternMatch Validation

- ✅ `similarity_score`: 0-1
- ✅ `matched_node_ids`: same length as pattern nodes
- ✅ `outcome_quality`: 0-10 if present

---

## JSON Examples

### Pattern Example

```json
{
  "pattern_id": "pat_abc123def456",
  "nodes": [
    {"id": "n1", "type": "decision_step", "properties": {}},
    {"id": "n2", "type": "iteration_loop", "properties": {"max_iters": 10}}
  ],
  "edges": [
    {"source_id": "n1", "target_id": "n2", "relation_type": "leads_to"}
  ],
  "targets": ["decision_step", "iteration_loop"],
  "fsm_types": ["DECISION", "ITERATION"],
  "domains": ["ml", "optimization"],
  "success_rate": 0.87,
  "avg_outcome_quality": 8.2,
  "cost_profile": {
    "latency_ms": 45.3,
    "latency_p95_ms": 120.5,
    "memory_peak_mb": 15.2,
    "error_rate": 0.02,
    "cost_score": 1.5,
    "sample_size": 500
  },
  "num_matching_traces": 425,
  "first_discovered": "2026-02-12T10:30:00Z",
  "last_updated": "2026-02-12T14:45:00Z",
  "canonical_hash": "a1b2c3d4e5f6...",
  "merged_from": [],
  "version": 1
}
```

### ExtractionResult Example

```json
{
  "extraction_id": "ext_xyz789",
  "patterns_extracted": [/*.. multiple patterns ..*/],
  "matches_found": [/*.. multiple matches ..*/],
  "num_input_traces": 10000,
  "num_patterns": 387,
  "num_matches": 45320,
  "num_dedup_merged": 23,
  "avg_pattern_size": 5.2,
  "avg_success_rate": 0.84,
  "coverage": 0.92,
  "extraction_duration_sec": 124.5,
  "dedup_duration_sec": 8.2,
  "total_duration_sec": 132.7,
  "extraction_timestamp": "2026-02-12T15:00:00Z",
  "parameters": {
    "min_frequency": 5,
    "max_size": 10,
    "similarity_threshold": 0.9
  }
}
```
