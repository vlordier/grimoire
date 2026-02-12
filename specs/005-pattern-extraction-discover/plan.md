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

```text
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

### Neo4j Cypher Templates

**Extract Candidate Patterns from Traces**

```cypher
// Find frequent step sequences (gSpan candidate generation)
MATCH (t:Trace)-[:CONTAINS]->(s:Step)
WHERE t.status = 'completed'
  AND s.fsm_type IS NOT NULL
WITH t, s
ORDER BY t.trace_id, s.step_number
WITH t, collect(s {step_id: s.step_id, role: s.role, 
                   content_hash: s.content_hash}) as steps
WHERE size(steps) >= 2
RETURN t.trace_id,
       t.fsm_type,
       steps[0..10] as step_sequence
LIMIT 1000
```

**Find Traces with Similar Step Sequences**

```cypher
// Match traces with similar step patterns
MATCH (t1:Trace)-[:CONTAINS]->(s1:Step)
WHERE t1.trace_id = $reference_trace_id
WITH t1, collect(DISTINCT s1.role) as ref_roles

MATCH (t2:Trace)-[:CONTAINS]->(s2:Step)
WHERE t2.trace_id <> t1.trace_id
  AND t2.fsm_type = t1.fsm_type
WITH t1, ref_roles, t2, collect(DISTINCT s2.role) as cmp_roles

WITH t1, t2, ref_roles, cmp_roles,
     apoc.coll.intersection(ref_roles, cmp_roles) as intersection,
     apoc.coll.union(ref_roles, cmp_roles) as union
WHERE size(union) > 0
WITH t1, t2, 
     1.0 * size(intersection) / size(union) as jaccard_similarity
WHERE jaccard_similarity >= 0.8
RETURN t2.trace_id, jaccard_similarity
ORDER BY jaccard_similarity DESC
LIMIT 50
```

**Store Extracted Pattern**

```cypher
// Create Pattern node with metadata
CREATE (p:Pattern {
  pattern_id: $pattern_id,
  name: $name,
  description: $description,
  canonical_hash: $canonical_hash,
  fsm_types: $fsm_types,
  domains: $domains,
  success_rate: $success_rate,
  avg_outcome_quality: $avg_outcome_quality,
  num_matching_traces: $num_matching_traces,
  first_discovered: datetime(),
  last_updated: datetime(),
  version: 1
})

// Create step sequence relationships
WITH p
UNWIND $step_sequence as step_def
CREATE (ps:PatternStep {
  step_order: step_def.order,
  role: step_def.role,
  content_pattern: step_def.content_pattern
})
CREATE (p)-[:HAS_STEP {order: step_def.order}]->(ps)

RETURN p.pattern_id
```

**Query Patterns by FSM Type**

```cypher
// Get patterns for specific FSM type
MATCH (p:Pattern)
WHERE $fsm_type IN p.fsm_types
  AND p.success_rate >= 0.6
RETURN p.pattern_id,
       p.name,
       p.success_rate,
       p.num_matching_traces
ORDER BY p.success_rate DESC, p.num_matching_traces DESC
LIMIT 100
```

**Link Pattern to Source Traces**

```cypher
// Create relationships from pattern to matching traces
MATCH (p:Pattern {pattern_id: $pattern_id})
MATCH (t:Trace)
WHERE t.trace_id IN $matching_trace_ids
CREATE (p)-[:MATCHES_TRACE {
  match_score: $match_score,
  matched_at: datetime()
}]->(t)
```

**Find Similar Patterns (for Deduplication)**

```cypher
// Find patterns with similar structure
MATCH (p1:Pattern)-[:HAS_STEP]->(ps1:PatternStep)
WHERE p1.pattern_id = $pattern_id
WITH p1, collect(ps1.role) as roles1

MATCH (p2:Pattern)-[:HAS_STEP]->(ps2:PatternStep)
WHERE p2.pattern_id <> p1.pattern_id
WITH p1, roles1, p2, collect(ps2.role) as roles2

WITH p1, p2, roles1, roles2,
     apoc.coll.intersection(roles1, roles2) as intersection,
     apoc.coll.union(roles1, roles2) as union
WITH p1, p2, 
     1.0 * size(intersection) / size(union) as jaccard,
     CASE 
       WHEN size(roles1) = size(roles2) THEN 1.0
       ELSE 1.0 - abs(size(roles1) - size(roles2)) / 
                  (1.0 * (size(roles1) + size(roles2)))
     END as size_sim
WITH p1, p2, (jaccard * 0.7 + size_sim * 0.3) as similarity
WHERE similarity >= 0.9
RETURN p2.pattern_id, p2.name, similarity
ORDER BY similarity DESC
```

**Merge Duplicate Patterns**

```cypher
// Merge pattern2 into pattern1
MATCH (p1:Pattern {pattern_id: $keep_pattern_id})
MATCH (p2:Pattern {pattern_id: $merge_pattern_id})

// Transfer relationships
MATCH (p2)-[r:MATCHES_TRACE]->(t:Trace)
CREATE (p1)-[:MATCHES_TRACE {
  match_score: r.match_score,
  matched_at: r.matched_at
}]->(t)

// Update statistics
SET p1.num_matching_traces = p1.num_matching_traces + p2.num_matching_traces,
    p1.merged_from = coalesce(p1.merged_from, []) + $merge_pattern_id,
    p1.last_updated = datetime()

// Delete merged pattern
DETACH DELETE p2

RETURN p1.pattern_id, p1.num_matching_traces
```

### Canonical Hash Algorithm

```python
def compute_canonical_hash(pattern: Pattern) -> str:
    """
    Compute deterministic hash for pattern deduplication.

    Canonical form:
    1. Sort steps by order
    2. Normalize content (lowercase, remove whitespace)
    3. Create JSON representation
    4. SHA256 hash
    """
    import json
    import hashlib

    # Build canonical representation
    canonical = {
        "fsm_types": sorted(pattern.fsm_types),
        "steps": [
            {
                "role": step.role,
                "content_pattern": step.content_pattern.lower().strip()
                                   if step.content_pattern else None
            }
            for step in sorted(pattern.steps, key=lambda s: s.order)
        ]
    }

    # Create deterministic JSON
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(',', ':'))

    # Hash
    return hashlib.sha256(canonical_json.encode()).hexdigest()


def are_patterns_equivalent(p1: Pattern, p2: Pattern, threshold: float = 0.9) -> bool:
    """
    Check if two patterns are equivalent (for deduplication).

    Uses:
    1. Exact hash match (fast path)
    2. Graph edit distance (if hashes differ but close)
    """
    # Fast path: exact hash match
    if p1.canonical_hash == p2.canonical_hash:
        return True

    # Slow path: structural similarity
    # Compute Jaccard similarity of step roles
    roles1 = set(s.role for s in p1.steps)
    roles2 = set(s.role for s in p2.steps)

    intersection = len(roles1 & roles2)
    union = len(roles1 | roles2)

    if union == 0:
        return False

    jaccard = intersection / union
    return jaccard >= threshold
```

### Minimum Support Threshold

```python
def calculate_min_support(total_traces: int, 
                         base_threshold: int = 5,
                         ratio_threshold: float = 0.01) -> int:
    """
    Calculate minimum support threshold for pattern mining.

    Formula: max(base_threshold, total_traces * ratio_threshold)

    Examples:
    - 100 traces → max(5, 1) = 5
    - 10,000 traces → max(5, 100) = 100
    - 1,000,000 traces → max(5, 10,000) = 10,000
    """
    return max(base_threshold, int(total_traces * ratio_threshold))

# Usage in gSpan
MIN_SUPPORT = calculate_min_support(total_traces=len(all_traces))
```

---

## See Also

- [PHASE_3_ANALYSIS.md](../../PHASE_3_ANALYSIS.md) — Phase 3 overview
- [data-model.md](data-model.md) — Detailed models
