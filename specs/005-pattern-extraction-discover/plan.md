# Implementation Plan: Pattern Extraction (005)

**Phase**: 3.1  
**Branch**: `005-pattern-extraction-discover`  
**Status**: Planning Phase  
**Effort**: 8-12 days

---

## Phase 0: Design

### Key Questions

**Q1: How do we define a "pattern"?**  
A: Recurrent sequence of steps (observations → plans → executions) that solve similar problems. Identified by Neo4j subgraph matching.

**Q2: How many steps minimum for a pattern?**  
A: At least 2 steps (e.g., OBSERVE + DECIDE). Max 10-15 steps (longer patterns less common, less reusable).

**Q3: How do we detect "similar problems"?**  
A: Problem keywords + FSM type + danger profile matching. Use fuzzy text matching on problem statements.

**Q4: What about patterns that work but are rare?**  
A: Include if success_rate ≥ 0.6 and used ≥ 5 times. Confidence scaling: more uses = higher confidence.

---

## Phase 1: Data Models

```python
Pattern(
    pattern_id: str,              # "pattern-005-debug-database-timeout"
    name: str,
    description: str,
    fsm_type: str,                # "fsm_diagnose_fix"
    problem_keywords: List[str],  # ["database", "timeout"]
    danger_profile: Dict,         # {ambiguity: [0.1, 0.4], ...}
    step_sequence: List[Dict],    # [{role: "observe", action: "check logs"}, ...]
    success_count: int,
    total_uses: int,
    success_rate: float,          # success_count / total_uses
    avg_time_to_solution: float,  # hours
    confidence: float,            # [0, 1] based on sample size
    created_at: datetime,
    last_updated: datetime,
)

PatternMatch(trace_id, pattern_id):
  - match_score: float [0, 1]  # How closely did trace follow pattern?
  - success: bool              # Did trace reach good outcome?
  - time_to_solution: float
  - deviations: List[str]      # Where did it differ?
```

---

## Phase 2: Implementation

### Algorithm: Subgraph Matching

```
For each trace in Phase 1 data:
  1. Extract step sequence (observations → plans → executions)
  2. For each candidate pattern:
     - Compute similarity (edit distance + semantic matching)
     - If similarity > threshold (0.7):
       - Record as PatternMatch
       - Extract outcome (success? time? cost?)
  3. Aggregate matches:
     - success_count = # matches where outcome=success
     - total_uses = # matches
     - success_rate = success_count / total_uses
     
Deduplication:
  1. For each pattern:
     - Compute similarity to all other patterns (edit distance)
     - If similarity > 0.8:
       - Merge (keep higher success_rate, combine usage stats)
```

### Key Components

- **Trace Iterator**: Scan Phase 1 Neo4j for completed traces
- **Sequence Extractor**: Pull step sequence from trace
- **Similarity Matcher**: Fuzzy-match to existing patterns
- **Deduplicator**: Merge near-identical patterns
- **Metadata Extractor**: FSM, keywords, danger profile tagging
- **Neo4j Saver**: Persist Pattern nodes + PatternMatch edges

---

## Phase 3: Testing

- Unit tests: Similarity matching, deduplication
- Integration tests: Full extraction pipeline on 100 traces
- Performance tests: P99 <30ms per trace on 1000-trace batch
- Accuracy: Extract 50+ patterns, 90% dedup correctness

---

## Phase 4: Deployment

- Backfill Phase 1 data (first run: extract all 100K+ traces)
- Weekly job: Extract patterns from new incoming traces
- Monitoring: Pattern quality metrics, dedup accuracy trends

---

## Effort Breakdown

| Phase | Days | Tasks |
|-------|------|-------|
| Design | 1 | Algorithm + data model |
| Code | 3-4 | Subgraph matching + dedup + metadata |
| Tests | 2-3 | Unit + integration + performance |
| Integration | 1-2 | Phase 1 + Phase 3.2 handoff |
| **Total** | **8-12** | |

---

## See Also

- [PHASE_3_ANALYSIS.md](../../PHASE_3_ANALYSIS.md) — Phase 3 overview
- [data-model.md](data-model.md) — Detailed models
