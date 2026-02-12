# Grimoire Specification Review

**Version**: 1.0  
**Date**: February 12, 2026  
**Scope**: Phases 1-3 (8 Features)  
**Status**: Review Complete

---

## Executive Summary

This document provides a comprehensive review of all 8 feature specifications, identifying:

- ✅ **Strengths**: Well-structured, clear dependencies, comprehensive data models
- ⚠️ **Gaps**: Minor inconsistencies, missing integration details
- 🔧 **Recommendations**: Specific improvements for implementation readiness

**Overall Assessment**: **READY FOR IMPLEMENTATION** with minor refinements.

---

## Feature-by-Feature Review

### Phase 1: Canonical Schema (001) ✅ COMPLETE

| Aspect | Status | Notes |
|--------|--------|-------|
| Specification | ✅ Complete | 10 files, 2,500+ lines |
| Data Models | ✅ Validated | Pydantic v2, all 34 issues resolved |
| API Contracts | ✅ Complete | 5 contracts (ingestion, retrieval, storage, versioning) |
| Integration | ✅ Ready | Production-ready, tested |

**Key Strengths**:

- Canonical schemas (`TraceBundle`, `Step`, `Edge`) are well-defined
- Neo4j + Qdrant storage mapping is clear
- All Pydantic v2 models validated

**No Blockers**: Phase 1 is production-ready.

---

### Phase 2.1: Danger Router (002) 📋 SPECIFIED

| Aspect | Status | Notes |
|--------|--------|-------|
| User Stories | ✅ Complete | 8 stories (P1: 6, P2: 2) |
| Data Models | ✅ Complete | `DangerScores`, `DangerEvidence` |
| API Contract | ✅ Complete | `POST /v1/classify`, `POST /v1/classify/batch` |
| Integration | ⚠️ Needs Detail | How scores attach to Neo4j Step nodes |

**Strengths**:

- Clear 4-danger taxonomy (ambiguity, adversarial, irreversibility, institutional)
- Keyword-based MVP approach is pragmatic
- Evidence spans provide explainability

**Gaps Identified**:

1. **Storage Integration** (Minor)
   - Current: "Store danger scores on Neo4j Step nodes"
   - Missing: Exact Cypher query for updating scores
   - **Recommendation**: Add Cypher template:

   ```cypher
   MATCH (s:Step {step_id: $step_id})
   SET s.danger_ambiguity = $ambiguity,
       s.danger_adversarial = $adversarial,
       s.danger_irreversibility = $irreversibility,
       s.danger_institutional = $institutional,
       s.danger_computed_at = datetime()
   ```

2. **Batch Size Limits** (Minor)
   - Current: "Up to 100 per batch"
   - Missing: Memory/timeout constraints for batch
   - **Recommendation**: Add max payload size (10MB) and timeout (30s)

3. **Confidence Score** (Minor)
   - Current: Evidence-based scoring
   - Missing: How confidence is calculated
   - **Recommendation**: Add `confidence = min(1.0, evidence_weight_sum / threshold)`

**Implementation Priority**: Ready to start. Address gaps during implementation.

---

### Phase 2.2: FSM Router (003) 📋 SPECIFIED

| Aspect | Status | Notes |
|--------|--------|-------|
| User Stories | ✅ Complete | 8 stories (P1: 6, P2: 2) |
| Data Models | ✅ Complete | `FSMClassification`, `FSMOption` |
| API Contract | ✅ Complete | `POST /v1/route`, `POST /v1/route/batch` |
| Integration | ⚠️ Needs Detail | Hot-reload config mechanism |

**Strengths**:

- 10 FSM types cover reasoning space well
- Config-driven approach enables customization
- Confidence scoring with alternatives is robust

**Gaps Identified**:

1. **Config Hot-Reload** (Medium)
   - Current: "Hot-loadable config"
   - Missing: Mechanism for reloading without restart
   - **Recommendation**: Add file watcher or API endpoint:

   ```python
   @app.post("/v1/config/reload")
   async def reload_config():
       global keyword_map, fsm_configs
       keyword_map = load_routing_config()
       return {"status": "reloaded", "fsm_count": len(keyword_map)}
   ```

2. **Keyword Conflict Resolution** (Minor)
   - Current: "Keywords matched (7/7)"
   - Missing: What if multiple FSMs match?
   - **Recommendation**: Add tie-breaking rule: highest confidence wins, if tie → most specific (most keywords matched)

3. **Default FSM** (Minor)
   - Current: `fsm_clarify_frame` for ambiguous
   - Missing: What if config is empty/corrupted?
   - **Recommendation**: Add fallback: if no FSM matches with confidence > 0.3, default to `fsm_clarify_frame`

**Implementation Priority**: Ready to start. Config hot-reload is nice-to-have.

---

### Phase 2.3: Transition Guards (004) 📋 SPECIFIED

| Aspect | Status | Notes |
|--------|--------|-------|
| User Stories | ✅ Complete | 6 stories (P1: 4, P2: 2) |
| Data Models | ✅ Complete | `GuardDecision`, `GuardRule` |
| API Contract | ⚠️ Partial | Internal only (no REST API defined) |
| Integration | ⚠️ Needs Detail | Aggregation logic specifics |

**Strengths**:

- 4 guard types cover safety requirements
- Aggregated decision simplifies consumption
- Escalation path is clear

**Gaps Identified**:

1. **No REST API** (Medium)
   - Current: "Internal" consumption
   - Missing: REST endpoint for external guard checks
   - **Recommendation**: Add API:

   ```python
   @app.post("/v1/guards/check")
   async def check_transition(request: GuardCheckRequest) -> GuardDecision:
       # Aggregate all guards
       decisions = [
           check_ambiguity_guard(request),
           check_irreversibility_guard(request),
           check_adversarial_guard(request),
           check_institutional_guard(request)
       ]
       return aggregate_decisions(decisions)
   ```

2. **Aggregation Logic** (Minor)
   - Current: "Aggregated decision"
   - Missing: Priority order when multiple guards trigger
   - **Recommendation**: Define priority: BLOCK > ESCALATE > WARN > ALLOW

3. **Guard State Machine** (Minor)
   - Current: Single-step guards
   - Missing: Multi-step context (e.g., "requires VERIFICATION step before")
   - **Recommendation**: Add trace context to GuardCheckRequest:

   ```python
   class GuardCheckRequest(BaseModel):
       current_step: Step
       trace_history: List[Step]  # For context-aware guards
   ```

**Implementation Priority**: Ready to start. Add REST API for consistency.

---

### Phase 3.1: Pattern Extraction (005) 📋 SPECIFIED

| Aspect | Status | Notes |
|--------|--------|-------|
| User Stories | ✅ Complete | 5 stories (P1: 4, P2: 1) |
| Data Models | ✅ Complete | `Pattern`, `CostProfile`, `ExtractionResult` |
| Research | ✅ Complete | gSpan algorithm, Jaccard+GED dedup |
| Integration | ⚠️ Needs Detail | Neo4j subgraph query specifics |

**Strengths**:

- gSpan algorithm choice is well-researched
- Fuzzy deduplication (90% accuracy target) is realistic
- Cost profiling enables ranking

**Gaps Identified**:

1. **Subgraph Query** (Medium)
   - Current: "Query Neo4j for subgraphs"
   - Missing: Exact Cypher for pattern extraction
   - **Recommendation**: Add query template:

   ```cypher
   // Extract candidate patterns from traces
   MATCH (t:Trace)-[:CONTAINS]->(s:Step)-[:FOLLOWS*1..5]->(next:Step)
   WHERE t.domain = $domain
   WITH s, next, count(*) as frequency
   WHERE frequency >= $min_support
   RETURN s.step_id as start_node, 
          collect(next.step_id) as pattern_steps,
          frequency
   ```

2. **Canonical Hash** (Minor)
   - Current: "SHA256 hash of canonical form"
   - Missing: Canonical form definition
   - **Recommendation**: Define canonical form:

   ```python
   def canonical_form(pattern: Pattern) -> str:
       """Sort nodes by degree, edges by (src, dst, type)"""
       sorted_nodes = sorted(pattern.nodes, key=lambda n: (n['degree'], n['id']))
       sorted_edges = sorted(pattern.edges, key=lambda e: (e['source_id'], e['target_id'], e['relation_type']))
       return json.dumps({'nodes': sorted_nodes, 'edges': sorted_edges}, sort_keys=True)
   ```

3. **Pattern Frequency Threshold** (Minor)
   - Current: "Frequent subgraph mining"
   - Missing: Minimum support threshold
   - **Recommendation**: Add configurable threshold: `min_support = max(5, total_traces * 0.01)`

**Implementation Priority**: Ready to start. Subgraph query needs refinement.

---

### Phase 3.2: Pattern Ranking (006) 📋 SPECIFIED

| Aspect | Status | Notes |
|--------|--------|-------|
| User Stories | ✅ Complete | 5 stories (P1: 4, P2: 1) |
| Data Models | ✅ Complete | `RankedPattern`, `RankingContext`, `ScoreBreakdown` |
| API Contract | ✅ Complete | `POST /v1/rank`, `GET /v1/scores` |
| Integration | ✅ Complete | Clear Phase 2 integration |

**Strengths**:

- Multi-objective scoring formula is well-defined
- Phase 2 integration is explicit
- Score breakdown provides explainability

**Gaps Identified**:

1. **Weight Tuning** (Minor)
   - Current: Fixed weights (0.4, 0.3, 0.2, 0.1)
   - Missing: How to tune weights based on domain
   - **Recommendation**: Add domain-specific overrides:

   ```python
   DOMAIN_WEIGHTS = {
       "security": {"safety": 0.5, "effectiveness": 0.3, "cost": 0.1, "relevance": 0.1},
       "performance": {"cost": 0.4, "effectiveness": 0.3, "safety": 0.2, "relevance": 0.1},
       "default": {"effectiveness": 0.4, "safety": 0.3, "relevance": 0.2, "cost": 0.1}
   }
   ```

2. **Cold Start** (Minor)
   - Current: Requires 5+ feedback events
   - Missing: How to rank new patterns
   - **Recommendation**: Add cold-start handling:

   ```python
   if feedback_count < 5:
       # Use similarity to ranked patterns
       effectiveness_score = similar_patterns_avg_effectiveness * 0.8
   ```

3. **Caching Strategy** (Minor)
   - Current: "<30ms for 1000 patterns"
   - Missing: Caching approach for 1M patterns
   - **Recommendation**: Add Redis caching for top-K patterns per FSM type:

   ```python
   cache_key = f"ranked_patterns:{fsm_type}:{domain}"
   cached = redis.get(cache_key)
   if cached and not force_refresh:
       return json.loads(cached)
   ```

**Implementation Priority**: Ready to start. Well-specified feature.

---

### Phase 3.3: Optimization Loop (008) 📋 SPECIFIED

| Aspect | Status | Notes |
|--------|--------|-------|
| User Stories | ✅ Complete | 5 stories (P1: 4, P2: 1) |
| Data Models | ✅ Complete | `FeedbackEvent`, `ConceptDriftAlert`, `ABExperiment` |
| Research | ✅ Complete | CUSUM algorithm, A/B testing framework |
| Integration | ⚠️ Needs Detail | Event bus mechanism |

**Strengths**:

- CUSUM for drift detection is statistically sound
- A/B testing with auto-promotion is production-ready
- Pattern lifecycle management is comprehensive

**Gaps Identified**:

1. **Event Bus** (Medium)
   - Current: "Async event collection"
   - Missing: Event bus technology choice
   - **Recommendation**: Add options comparison:
   | Technology | Pros | Cons | Recommendation |

   |------------|------|------|------------------|
   | Redis Streams | Simple, existing infra | Limited persistence | **Use for MVP** |
   | Kafka | Scalable, durable | Complex ops | Future upgrade |
   | RabbitMQ | Mature, routing | Single point | Alternative |

2. **Feedback Buffer Overflow** (Minor)
   - Current: "K=50 buffered"
   - Missing: Overflow handling
   - **Recommendation**: Add overflow strategy:

   ```python
   if buffer_size >= MAX_BUFFER:
       # Option 1: Drop oldest (current)
       buffer.pop(0)
       # Option 2: Trigger immediate processing
       await process_batch()
       # Option 3: Alert + backpressure
       await alert_ops("feedback_buffer_full")
   ```

3. **Drift Alert Deduplication** (Minor)
   - Current: "Alert escalates if drift persists >3 days"
   - Missing: Alert frequency
   - **Recommendation**: Add alert throttling:

   ```python
   last_alert = get_last_drift_alert(pattern_id)
   if drift_detected and (now - last_alert) > timedelta(hours=24):
       send_alert()
   ```

**Implementation Priority**: Ready to start. Define event bus in first sprint.

---

## Cross-Cutting Concerns

### 1. Data Consistency

| Concern | Status | Recommendation |
|---------|--------|----------------|
| Neo4j Schema Evolution | ⚠️ Partial | Add migration strategy document |
| Pydantic v2 Forward Compatibility | ✅ Good | All models use `Config` properly |
| API Versioning | ⚠️ Missing | Add `/v1/` prefix consistently |

**Recommendation**: Create `MIGRATION_GUIDE.md` for schema changes.

### 2. Error Handling

| Feature | Error Handling | Gap |
|---------|---------------|-----|
| 001 | ✅ Complete | Retry + dead letter queue |
| 002 | ⚠️ Partial | Missing timeout handling |
| 003 | ⚠️ Partial | Missing config parse errors |
| 004 | ⚠️ Partial | Missing aggregation failures |
| 005 | ⚠️ Partial | Missing gSpan OOM handling |
| 006 | ✅ Complete | Score calculation errors |
| 008 | ⚠️ Partial | Missing event bus failures |

**Recommendation**: Add error handling section to each plan.md.

### 3. Observability

| Aspect | Status | Notes |
|--------|--------|-------|
| Metrics | ⚠️ Partial | Latency defined, but not error rates |
| Logging | ⚠️ Partial | Structured logging not specified |
| Tracing | ⚠️ Missing | Distributed tracing not defined |

**Recommendation**: Add OpenTelemetry tracing to all features.

### 4. Security

| Aspect | Status | Notes |
|--------|--------|-------|
| Authentication | ⚠️ Missing | Only "service-to-service" mentioned |
| Authorization | ⚠️ Missing | No RBAC defined |
| Input Validation | ✅ Good | Pydantic handles this |

**Recommendation**: Add security section to integration architecture.

---

## Integration Gaps

### 1. Phase 2 → Phase 3 Data Flow

**Current**: "Phase 2 scores consumed by Phase 3"

**Gap**: Exact mechanism for passing scores

**Recommendation**: Define data flow:

```text
Phase 2 (Danger Router) 
  → Writes to Neo4j: (Step)-[:HAS_DANGER_SCORE]->(DangerScore)

Phase 3 (Pattern Ranking)
  → Reads from Neo4j: MATCH (p:Pattern)-[:CONTAINS_STEP]->(s:Step)-[:HAS_DANGER_SCORE]->(d:DangerScore)
  → Aggregates: avg(d.danger_ambiguity) as pattern_ambiguity
```

### 2. Feedback Loop Closure

**Current**: "Feedback drives optimization"

**Gap**: How does feedback reach Pattern Ranking?

**Recommendation**: Define event flow:

```text
Pattern Execution → FeedbackEvent → Event Bus → Optimization Loop 
  → Re-rank Trigger → Pattern Ranking API → Updated Scores → Neo4j
```

### 3. A/B Test Traffic Splitting

**Current**: "Route percentage of traffic"

**Gap**: How is traffic split determined?

**Recommendation**: Add routing logic:

```python
def route_to_variant(pattern_id: str, experiment_id: str, user_id: str) -> str:
    """Deterministic routing based on hash"""
    hash_input = f"{experiment_id}:{user_id}"
    hash_value = int(hashlib.md5(hash_input.encode()).hexdigest(), 16)
    if hash_value % 100 < 50:  # 50/50 split
        return "version_b"
    return "version_a"
```

---

## Recommendations Summary

### Immediate Actions (Before Implementation)

1. **Add REST API for Guards (004)**
   - Priority: High
   - Effort: 2 hours
   - Benefit: Consistency with other features

2. **Define Event Bus Technology (008)**
   - Priority: High
   - Effort: 4 hours
   - Benefit: Unblocks optimization loop implementation

3. **Add Cypher Templates (002, 003, 005)**
   - Priority: Medium
   - Effort: 3 hours
   - Benefit: Clearer integration points

### During Implementation

4. **Add Error Handling Sections**
   - Priority: Medium
   - Effort: 1 day
   - Benefit: Robustness

5. **Define Observability Strategy**
   - Priority: Medium
   - Effort: 1 day
   - Benefit: Production readiness

### Future Improvements

6. **Security Hardening**
   - Priority: Low
   - Effort: 2 days
   - Benefit: Production security

7. **Performance Tuning Guide**
   - Priority: Low
   - Effort: 1 day
   - Benefit: Operational excellence

---

## Conclusion

**Overall Status**: ✅ **READY FOR IMPLEMENTATION**

All 8 features have comprehensive specifications with:

- Clear user stories and acceptance criteria
- Well-defined data models (Pydantic v2)
- API contracts with request/response schemas
- Research backing algorithmic choices
- Integration points documented

**Critical Path**:

1. Phase 2 can start immediately (002, 003, 004)
2. Phase 3.1 (005) can start after Phase 1
3. Phase 3.2 (006) can start after Phase 2 + 3.1
4. Phase 3.3 (008) can start after Phase 3.2

**Risk Assessment**: **LOW**

- No architectural blockers
- Clear dependencies
- Well-researched algorithms
- Comprehensive specifications

**Next Steps**:

1. Address 3 immediate actions (REST API for 004, Event Bus for 008, Cypher templates)
2. Begin Phase 2 implementation
3. Set up CI/CD for cross-feature integration testing

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-12 | AI Assistant | Initial review |
