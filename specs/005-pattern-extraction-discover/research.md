# Research: Pattern Extraction Algorithms

## Problem Statement

Given a corpus of execution traces (10K-1M traces), how do we efficiently extract reusable reasoning patterns (subgraphs) that appear frequently?

**Key Challenges**:

1. Subgraph isomorphism is NP-complete (exponential in worst case)
2. Similar patterns may have slight variations (fuzzy matching)
3. Real traces are large (100+ steps), creating combinatorial explosion
4. Need to handle semantic equivalence (e.g., loop with 5 iterations ≈ loop with 6 iterations)

---

## Subgraph Matching Approaches

### Option A: Exact Isomorphism (Reference)

**Algorithm**: VF2 algorithm (state-of-the-art for exact matching)

**Pros**:

- Guaranteed correctness
- Well-implemented in libraries (igraph, networkx)
- Deterministic results

**Cons**:

- O(n! × m!) worst case for n nodes, m edges
- Infeasible for traces >50 nodes
- Misses similar patterns (requires exact structure match)

**Decision**: Use for validation only, too slow for production

---

### Option B: Frequent Subgraph Mining (Recommended for MVP)

**Algorithm**: gSpan (Graph-based Subsequence Pattern Mining)

**How It Works**:

1. Enumerate all connected subgraphs from traces
2. Track frequency of each unique subgraph
3. Return subgraphs appearing ≥min_frequency times
4. Prune infrequent patterns early (apriori principle)

**Implementation**:

```python
# Pseudocode
patterns = {}
for trace in traces:
    for subgraph in enumerate_subgraphs(trace, max_size=10):
        pattern_id = canonicalize(subgraph)
        patterns[pattern_id] += 1

result = [sg for sg, count in patterns.items() if count >= min_frequency]
```

**Parameters**:

- `min_frequency`: Min traces containing pattern (default: 5, 0.1% of corpus)
- `max_size`: Max nodes in pattern (default: 10, balance coverage vs. complexity)
- `min_nodes`: Min nodes to be considered pattern (default: 2)

**Complexity**:

- Time: O(traces × patterns × enumeration_time)
- Space: O(unique_patterns)
- Practical: ~1-5 sec per 1K traces (with pruning)

**Pros**:

- Efficient (pruning eliminates exponential explosion)
- Discovers frequent patterns automatically
- Well-researched algorithm (30+ years)

**Cons**:

- Requires parameter tuning (min_frequency)
- May miss rare-but-valuable patterns
- Canonical form expensive (graph hashing)

**Decision**: Recommended for MVP ✅

---

### Option C: Neural Graph Embedding (Future)

**Algorithm**: GCN (Graph Convolutional Network) or GraphSAINT

**How It Works**:

1. Train embeddings on trace graphs
2. Cluster embeddings (similar patterns close in embedding space)
3. Extract cluster representatives as patterns

**Pros**:

- Discovers semantic similarity (even if structure differs)
- Learns from execution outcomes (supervised)
- More powerful than structure-only matching

**Cons**:

- Requires training data + labels
- Black box (harder to validate)
- Slower inference (neural network)

**Decision**: Phase 3.4+ (future enhancement)

---

## Deduplication Strategy

### Problem: Similar Pattern Detection

After mining, `{IFTHEN-A, IFTHEN-B, IFTHEN-C}` three patterns might be semantically identical but structurally differ due to variable naming, order variations, etc.

### Option 1: Exact Canonicalization

**Approach**: Normalize graph structure → unique canonical form

**Steps**:

1. Node relabeling: sort nodes by degree + adjacency
2. Edge ordering: normalize edge lists
3. Hash canonical form → unique pattern ID

**Complexity**: O(graph_size × log(graph_size)) per pattern

**Accuracy**: 100% (but only catches exact structural matches)

**Decision**: Use as primary deduplication ✓

---

### Option 2: Fuzzy Matching (Recommended)

**Approach**: Use graph similarity metrics to cluster similar patterns

**Metric 1: Graph Edit Distance (GED)**

- Minimum edits (add/remove/relabel node/edge) to transform G1 → G2
- Normalized by graph size: similarity = 1 - (GED / max_cost)
- Threshold: patterns with similarity > 0.9 → same cluster

**Implementation**:

```python
def graph_similarity(g1, g2):
    ged = compute_ged(g1, g2)  # Use Hungarian algorithm
    max_size = max(len(g1.nodes), len(g2.nodes))
    return 1 - (ged / (2 * max_size))

# Cluster patterns
for i, p1 in enumerate(patterns):
    for j, p2 in enumerate(patterns[i+1:]):
        if graph_similarity(p1, p2) > 0.9:
            merge_patterns(p1, p2)
```

**Complexity**: O(n² × GED_computation)  

- GED: Hungarian algorithm O(n³)
- Practical: ~100ms for 1K patterns

**Metric 2: Jaccard Similarity** (Faster)

- `sim = common_edges / union_edges`
- Threshold: sim > 0.8 → same cluster
- O(n × m) instead of O(n³), but less accurate

**Metric 3: Subgraph Matching**

- For each pattern pair, count max common subgraph size
- `similarity = 2 × common_size / (size_p1 + size_p2)`

**Recommendation**: Use Jaccard (fast) + GED (accurate) hybrid

- First pass: Jaccard for quick filtering (threshold 0.8)
- Second pass: GED on candidates (threshold 0.9)

**Decision**: Jaccard primary (speed), GED on validation ✓

---

## Cost Profiling

### What to Measure

**Per Pattern**:

1. `latency_ms`: Avg execution time on matching traces
2. `latency_p95`: 95th percentile latency
3. `memory_peak_mb`: Max memory during execution
4. `error_rate`: % traces where pattern failed
5. `error_types`: Categorized errors (timeout, overflow, invalid_state)

**Aggregation**:

```python
cost_score = (
    latency_ms / 1000 +           # Normalize to 0-1
    memory_peak_mb / 100 +        # 100MB normalization
    error_rate * 10               # Error heavily weighted
)
```

### Collection Strategy

**Option 1: Inline Instrumentation**

- Wrap pattern execution with timer + memory profiler
- Pros: Accurate, captures actual overhead
- Cons: Adds measurement overhead (~5-10%)

**Option 2: Sampling**

- Profile 1% of patterns (randomly selected)
- Estimate full profile from sample
- Pros: Lower overhead
- Cons: Statistical noise

**Decision**: Option 1 for MVP (accuracy > overhead)

---

## Metadata Extraction

### Pattern Metadata to Capture

1. **Targets** (What things does pattern apply to?)
   - Input types: TraceStep, Edge, text_field
   - Output types: decision, modified_state, new_branch
   - Example: `targets = ["decision_step", "branching"]`

2. **FSM Types** (Which FSM states?)
   - Pattern appears in traces with these FSM types
   - Example: `fsm_types = ["DECISION", "CONDITIONAL"]`

3. **Domain Tags** (Which problem domains?)
   - Derived from trace metadata
   - Example: `domains = ["ml", "optimization"]`

4. **Success Metrics** (When does it work well?)
   - Avg outcome quality if pattern was used
   - Example: `avg_quality = 7.5/10`

### Extraction Algorithm

```python
def extract_metadata(pattern, matching_traces):
    metadata = {
        'targets': set(),
        'fsm_types': set(),
        'domains': set(),
        'success_rate': 0,
    }

    for trace in matching_traces:
        # Extract targets from matched subgraph nodes
        for node in pattern.nodes:
            metadata['targets'].add(node.type)

        # Extract FSM types
        metadata['fsm_types'].add(trace.fsm_type)

        # Extract domains
        metadata['domains'].add(trace.domain)

        # Track success
        if trace.execution_successful:
            metadata['success_rate'] += 1

    metadata['success_rate'] /= len(matching_traces)
    return metadata
```

---

## Performance Targets

| Operation | Target | Notes |
|-----------|--------|-------|
| Extract patterns from 10K traces | <60 sec | 1000 patterns expected |
| Extract patterns from 100K traces | <10 min | 5000 patterns expected |
| Dedup 1000 patterns (Jaccard) | <100 ms | Single-threaded |
| Dedup 1000 patterns (GED) | <5 sec | Backup validation |
| Cost profile 1000 patterns | <1 sec | Pre-computed |
| Extract metadata 1000 patterns | <500 ms | Parallel-friendly |

---

## Implementation Plan

### Phase 1: Exact Pattern Mining (Days 1-2)

- Implement gSpan algorithm (or use networkx variant)
- Parametrize min_frequency, max_size
- Test on 100-trace sample corpus

### Phase 2: Canonicalization (Day 2-3)

- Implement graph canonicalization (node sorting + hashing)
- Exact deduplication: remove structural duplicates

### Phase 3: Fuzzy Matching (Day 3-4)

- Implement Jaccard similarity
- Implement GED (Hungarian algorithm)
- Clustering: merge patterns > threshold

### Phase 4: Metadata + Profiling (Day 4-5)

- Extract targets, FSM types, domains
- Inline cost profiling
- Validate accuracy on 1K-pattern corpus

### Phase 5: Optimization (Day 5-6)

- Parallel pattern enumeration (multiprocessing)
- Cache canonical forms
- Optimize dedup (pre-filter by size, degree)

---

## Risks & Mitigations

| Risk | Probability | Mitigation |
|------|-------------|-----------|
| GED too slow for 1M patterns | Medium | Use Jaccard + sample-based GED validation |
| False dedup (merging different patterns) | Low | Validate with human review (1% sample) |
| Pattern extraction incomplete | Medium | Run multiple algorithms, compare results |
| Memory explosion (storing patterns) | Low | Stream processing, store ids not structures |

---

## References

- **gSpan**: Yan et al., "gSpan: Graph-Based Substructure Pattern Mining" (2002)
- **VF2**: Cordella et al., "A (Sub)Graph Isomorphism Algorithm for Matching Large Graphs" (2004)
- **GED**: Riesen & Bunke, "Approximate Graph Edit Distance Computation..." (2009)
- **NetworkX**: Python library with graph algorithms (<https://networkx.org/>)
