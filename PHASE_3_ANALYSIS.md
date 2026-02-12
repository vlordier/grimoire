# Phase 3 Roadmap — Pattern Recognition & Optimization

**Date**: 12 February 2026  
**Current State**: Phase 1 ✅ Complete | Phase 2 ✅ Specified (ready for implementation)  
**Next Phase**: Phase 3 (Pattern Recognition — Rank & optimize reasoning strategies)

---

## Architecture Overview

Phase 3 builds the **optimization plane** that learns from past reasoning and improves future decisions:

```
Completed Reasoning Traces (Phase 1, 2)
    ↓
[Extract Patterns] ← What sequence of steps worked well?
    ↓
[Pattern Classification] ← By problem type (FSM), by danger profile, by domain
    ↓
[Effectiveness Scoring] ← F1 score, time-to-solution, cost, safety
    ↓
[Ranking] ← Sort patterns by (safety × effectiveness × domain_match)
    ↓
[Recommendation] ← Suggest top patterns for similar future problems
    ↓
[Feedback Loop] ← Track if recommended patterns were followed + improved outcomes
    ↓
[Optimization] ← Adjust scoring, weights, thresholds based on feedback
```

---

## Phase 3 Features (3 Total)

### 3.1: Pattern Extraction (005) — Detect Solution Archetypes

**Purpose**: Identify recurring multi-step solution patterns from historical reasoning traces.

**What it does**:
- Scan historical traces for common step sequences
- Cluster similar sequences into **Patterns**
- Extract: problem type, FSM used, danger profile, steps taken, outcome
- Store patterns in dedicated Neo4j nodes + Qdrant vectors

**Example**:
```
Problem: "Database queries timeout under load"
FSM: diagnose_fix
Danger: ambiguity=0.2, irreversibility=0.8

Pattern: DIAGNOSE_TIMEOUT_INDEXING
  Steps:
    1. OBSERVATION: "Check query execution plans"  
    2. OBSERVATION: "Find missing indexes"
    3. PLAN: "Add indexes to frequently queried columns"
    4. EXECUTE: "Deploy index changes"
    5. VERIFY: "Rerun queries, confirm performance"
  
  Outcomes:
    - Success rate: 85% (17/20 similar problems resolved same way)
    - Avg time-to-solution: 6 hours
    - Safety: No false positives
    - Cost: $0 (no external service calls)
```

**Key Deliverables**:
- Pattern schema (Neo4j + Qdrant)
- Extraction algorithm (find common subgraph sequences)
- Clustering logic (group by FSM + problem keywords + outcome)
- Deduplication (recognize same pattern, different wording)

**Effort Estimate**: 8-12 days
- Days 1-3: Schema design (Pattern, PatternMatch, PatternUse entities)
- Days 3-5: Extraction algorithm (subgraph matching + clustering)
- Days 5-8: Integration with Phase 1 (backfill historical traces)
- Days 8-10: Testing + deduplication tuning
- Days 10-12: Performance optimization (1M+ traces)

**Success Criteria**:
- [ ] Extract 50+ distinct patterns from Phase 1 data
- [ ] Patterns have >70% accuracy (same pattern solves similar problems)
- [ ] Execution time < 30ms per trace queried
- [ ] Zero duplicate patterns (deduplication works)

---

### 3.2: Pattern Ranking (006) — Score by Effectiveness + Safety

**Purpose**: Rank extracted patterns by how likely they are to succeed on similar problems.

**What it does**:
- Score each pattern on: **effectiveness** (success rate), **safety** (danger compatibility), **cost** (time/resources)
- Weight scores by: FSM alignment, danger profile match, domain similarity
- Produce ranking: top patterns for each problem class

**Example Scoring**:
```
Problem: "Database timeout" (ambiguity=0.2)

Candidate patterns:
  1. DIAGNOSE_TIMEOUT_INDEXING
     - Effectiveness: 0.85 (success rate)
     - Safety: 0.95 (handles low ambiguity well)
     - Cost: 0.90 (fast, cheap)
     - Domain match: "database" = perfect
     → Final score: 0.90 (weighted avg)
  
  2. OPTIMIZE_QUERY_REWRITE
     - Effectiveness: 0.70
     - Safety: 0.80
     - Cost: 0.60 (slower)
     - Domain match: "database" = perfect
     → Final score: 0.70
  
  3. SCALE_HORIZONTALLY_CACHE
     - Effectiveness: 0.60
     - Safety: 0.70
     - Cost: 0.40
     - Domain match: "database" = partial
     → Final score: 0.55

Recommendation: Use DIAGNOSE_TIMEOUT_INDEXING (score: 0.90)
```

**Key Deliverables**:
- Effectiveness score: success_rate(pattern) on similar problems
- Safety score: pattern compatible with danger profile?
- Cost function: (time + resource_usage) / effectiveness
- Weighting algorithm: FSM boost, domain boost, danger compatibility
- Ranking API: `rank_patterns(problem, fsm_type, danger_scores) → List[RankedPattern]`

**Effort Estimate**: 6-8 days
- Days 1-2: Score function design
- Days 2-4: Integration with Phase 2 (FSM alignment, danger compatibility)
- Days 4-6: Weighting tuning (A/B test different weights on test set)
- Days 6-8: Performance + caching (pattern rankings should be cached)

**Success Criteria**:
- [ ] Ranking correlates with human preference (80%+ agreement on test set)
- [ ] Top-ranked patterns have >80% success rate on similar problems
- [ ] Ranking API latency < 100ms (cached)
- [ ] All scoring components logged for transparency

---

### 3.3: Optimization Loop (007) — Feedback & Learning

**Purpose**: Close the loop: track if recommended patterns are followed, measure outcomes, improve scoring.

**What it does**:
- Log when patterns are recommended vs followed
- Track outcomes (problem solved? How long? Any issues?)
- Compute pattern effectiveness over time (sliding window: last 30 uses)
- Detect concept drift (pattern accuracy declining? Retrain?)
- A/B test scoring weights on new incoming problems

**Example**:
```
Recommended pattern: DIAGNOSE_TIMEOUT_INDEXING
Probability user follows: 60% (historically)
Expected outcome if followed: Success (0.85 expected)

Actual outcomes (last 30 uses):
  - Followed & succeeded: 24 (80%)
  - Followed & failed: 3 (10%)
  - Not followed: 3 (10%)

Updated effectiveness: 24/(24+3) = 0.89 (up from 0.85)
Override reason (when not followed):
  - "Indexes already existed" (2)
  - "Root cause was different" (1)

Recommendation: Increase boost for "check existing indexes first" heuristic
```

**Key Deliverables**:
- Recommendation logger (what pattern was suggested, confidence, FSM context)
- Outcome tracker (was it followed? Did it work? How long?)
- Effectiveness updater (running average over time)
- Concept drift detector (alert if pattern accuracy drops)
- A/B test framework (compare different scoring weights on new problems)
- Feedback dashboard (show pattern usage, effectiveness trends, learning curve)

**Effort Estimate**: 7-10 days
- Days 1-2: Logging schema (RecommendationEvent, OutcomeEvent)
- Days 2-4: Outcome tracking integration (feedback from users/system)
- Days 4-6: Effectiveness updater (sliding window, concept drift)
- Days 6-8: A/B testing framework
- Days 8-10: Dashboard + monitoring

**Success Criteria**:
- [ ] 100% of recommendations logged
- [ ] 90% outcome tracking rate (know if pattern was followed + result)
- [ ] Pattern effectiveness scores update within 24 hours
- [ ] Concept drift detector alerts when pattern accuracy drops >10%
- [ ] A/B tests run automatically, results visible in dashboard

---

## Phase 3 Timeline & Dependencies

### Critical Path

```
Phase 1 (Complete) ──────────────────────────────────────┐
                                                          ↓
Phase 2 (In Progress: 002, 003, 004)                      │
  2.1: Danger Classifier (7-11 days)  ────────┐          │
  2.2: FSM Router (4-6 days)  ────────┐       │          │
  2.3: Transition Guards (3-4 days)   │ ←─────┴──→ Combined 14-21 days
                                      ↓
Phase 3 (Ready to Plan):               │
  3.1: Pattern Extraction (8-12 days)  ├─→ Sequential 21-30 days
  3.2: Pattern Ranking (6-8 days)      │
  3.3: Optimization Loop (7-10 days) ←─┘

Recommended Sequencing:
  - Start Phase 3.1 (Pattern Extraction) once Phase 2 complete
  - Start Phase 3.2 (Pattern Ranking) after 3.1 has 50+ patterns
  - Start Phase 3.3 (Optimization Loop) after 3.2 has scoring working
  - Parallel: Phase 2 implementation + Phase 3 planning/design
```

### Interaction Between Phases

**Phase 2 → Phase 3 Data Flow**:
- Danger scores → Pattern scoring (filter by danger compatibility)
- FSM type → Pattern classification & ranking (FSM alignment)
- Guard decisions → Pattern safety assessment (learn which guards fail)

**Phase 3 → Phase 2 Feedback**:
- Pattern effectiveness → Refine danger thresholds (if patterns show lower threshold works better)
- Recommendation feedback → Improve FSM routing (if wrong FSM recommended for patterns)

---

## Data Models

### Pattern (Neo4j Entity)

```python
Pattern(
    pattern_id: str,              # "pattern-003-diagnose-timeout-indexing"
    name: str,                    # "Diagnose Timeout (Indexing)"
    description: str,
    fsm_type: str,                # "fsm_diagnose_fix"
    problem_keywords: List[str],  # ["timeout", "database", "query"]
    problem_regex: str,           # Optional regex for matching
    danger_profile: Dict,         # {"ambiguity": [0.0, 0.4], ...}
    step_sequence: List[Dict],    # Sequence of steps in pattern
    success_count: int,           # How many times has this pattern succeeded?
    total_uses: int,              # How many times has this been recommended/followed?
    avg_time_to_solution: float,  # Hours
    cost: float,                  # Relative cost (time + resources)
    last_updated: datetime,       # When was effectiveness last recalculated?
    confidence: float,            # [0, 1] how confident we are in this pattern
)
```

### PatternMatch (Edge)

```
Trace ---(MATCHED_PATTERN)---> Pattern
  with properties:
    - match_score: 0.0-1.0 (how closely did trace follow pattern?)
    - success: bool (did trace reach good outcome?)
    - time_to_solution: float (hours)
    - deviations: List[str] (where did trace deviate from pattern?)
```

### RankedPattern (Response Model)

```python
RankedPattern(
    pattern_id: str,
    name: str,
    rank: int,                    # 1 = best match for this problem
    score: float,                 # [0, 1] composite score
    effectiveness: float,         # Success rate
    safety: float,                # Danger compatibility
    cost: float,                  # Relative cost
    reason: str,                  # Why this pattern ranks high
    confidence: float,            # Confidence in recommendation
)
```

---

## Integration with Phase 2

### Danger Classifier → Pattern Safety Filtering

```
Problem: "Deploy new config to production" (institutional=0.8)

Candidate patterns:
  1. DEPLOY_WITH_GRADUAL_ROLLOUT
     - Expected danger: institutional=0.7 ✓ (compatible)
     - Confidence: High
  
  2. DEPLOY_ALL_AT_ONCE
     - Expected danger: institutional=0.95 ✗ (too risky)
     - Guard recommendation: INSTITUTIONAL_REQUIRES_STAKEHOLDERS
     - Exclude from recommendations
```

### FSM Router → Pattern Classification

```
Problem routed to: fsm_design_decide

Search for patterns:
  - Filtered by: fsm_type = "fsm_design_decide"
  - Ranked by: success_rate on design problems (60%)
  - Examples: CHOOSE_ARCHITECTURE, EVALUATE_OPTIONS, COMPARE_ALTERNATIVES
```

### Transition Guards → Pattern Validation

```
Pattern: EXECUTE_IRREVERSIBLE_ACTION
  - Requires prior VERIFY step (NO_IRREVERSIBLE_UNVERIFIED guard)
  - Requires low ambiguity (NO_EXECUTE_AMBIGUOUS guard)
  - Pattern score reduced if it doesn't follow guard rules
```

---

## Success Metrics (Phase 3 Complete)

| Metric | Target | How Measured |
|--------|--------|--------------|
| **Coverage** | 80%+ of problems match ≥1 pattern | % traces with match_score ≥ 0.7 |
| **Accuracy** | Top-ranked pattern successful 75%+ | % times top pattern solved problem |
| **Learning** | Pattern effectiveness improves 5-10% after 30 uses | Trending of effectiveness scores |
| **Performance** | Pattern ranking < 100ms | Latency measured on 1000 problems |
| **Adoption** | Users follow top-3 recommendations 60%+ | Outcome tracking data |
| **Safety** | 0 patterns violate guard thresholds | Audit log of pattern safety reviews |

---

## Phase 3 Feature Details (Compact)

### 005-Pattern-Extraction (Pattern Discovery)

| Aspect | Detail |
|--------|--------|
| **File Structure** | `specs/005-pattern-extraction/` (spec, plan, research, data-model, contracts) |
| **Key Algorithm** | Subgraph matching + clustering on Neo4j |
| **Input** | Historical traces from Phase 1 (~100K+) |
| **Output** | Pattern entities in Neo4j, vectors in Qdrant |
| **Effort** | 8-12 days |
| **Success Criteria** | 50+ patterns, <30ms per trace, 0 duplicates |

### 006-Pattern-Ranking (Effectiveness Scoring)

| Aspect | Detail |
|--------|--------|
| **File Structure** | `specs/006-pattern-ranking/` |
| **Key Algorithm** | Weighted scoring: effectiveness × safety × cost × domain_match |
| **Input** | Extracted patterns + Phase 2 danger/FSM data |
| **Output** | Ranked pattern lists per problem class |
| **Effort** | 6-8 days |
| **Success Criteria** | 80%+ human agreement, top patterns >80% success |

### 007-Optimization-Loop (Feedback & Learning)

| Aspect | Detail |
|--------|--------|
| **File Structure** | `specs/007-optimization-loop/` |
| **Key Algorithm** | Sliding window effectiveness, concept drift detection, A/B testing |
| **Input** | Outcome tracking + recommendations data |
| **Output** | Updated pattern scores, alerts on drift, A/B test results |
| **Effort** | 7-10 days |
| **Success Criteria** | 90% outcome tracking, 100% logging, automated updates |

---

## Implementation Approach

### Phase 3 Strategy: **Quick Win + Long Tail**

**Week 1 (Days 1-5): Pattern Extraction MVP**
- Extract basic patterns from Phase 1 data
- Deduplication + clustering
- Initial pattern storage
- Goal: 30-50 patterns identified

**Week 2 (Days 6-12): Pattern Ranking**
- Implement scoring functions
- Integrate danger + FSM context
- Build ranking API
- Goal: Ranked recommendations working

**Week 3 (Days 13-21): Optimization Loop + Refinement**
- Outcome tracking
- Effectiveness updates
- Feedback dashboard
- Goal: Learning loop closed + patterns improving

**Week 4+ (Days 21+): Tuning + Scaling**
- Concept drift detection tuning
- Performance optimization for 1M+ traces
- Dashboard + monitoring
- Goal: Production-ready

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| **Patterns too generic** | Recommendations not specific enough | Clustering + fsm-based segmentation |
| **Few patterns extracted** | Low coverage | Use Phase 2 (danger + FSM) to increase diversity |
| **Effectiveness score unstable** | Noisy updates | Use smoothing (sliding window), confidence intervals |
| **Concept drift** | Old patterns become stale | Drift detector alerts + retraining trigger |
| **User doesn't follow recommendation** | Feedback loop breaks | Track "recommended but not followed"; analyze why |

---

## Phase 3 Planning Artifacts

**To Create (This Sprint)**:
- [ ] Feature branch 005-pattern-extraction
- [ ] Feature branch 006-pattern-ranking
- [ ] Feature branch 007-optimization-loop
- [ ] Spec files for all 3 features (8 files total)
- [ ] Architecture diagram (Patterns → Ranking → Feedback)
- [ ] Database schema (Pattern entities + edges)

**Already Complete**:
- ✅ Phase 1 data (100K+ traces) available for pattern extraction
- ✅ Phase 2 (danger + FSM) context ready to integrate
- ✅ Canonical schemas (Pattern, PatternMatch model patterns)

---

## Next Actions

1. **Review Phase 3 Architecture** (30 min) — Validate approach
2. **Create Feature Branches** (1 hour) — 005, 006, 007
3. **Develop Feature Specs** (4-6 hours) — Detailed user stories, data models
4. **Integration Planning** (2 hours) — Phase 2 → Phase 3 data flow
5. **Effort Estimation** (1 hour) — Developer sign-off

**Total Phase 3 Planning**: 1 day (8 hours)  
**Phase 3 Implementation**: 3 weeks (after Phase 2 complete)

---

## See Also

- [PHASE_1_COMPLETION.md](PHASE_1_COMPLETION.md) — Phase 1 summary
- [PHASE_2_PLANNING_COMPLETE.md](PHASE_2_PLANNING_COMPLETE.md) — Phase 2 specs
- [docs/domain/fsm-catalogue.md](docs/domain/fsm-catalogue.md) — FSM context
- [docs/reference/danger-classification-impl.md](docs/reference/danger-classification-impl.md) — Reference logic
