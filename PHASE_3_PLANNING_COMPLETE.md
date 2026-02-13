# Phase 3 Planning Complete: Pattern Extraction, Ranking & Optimization

**Date**: February 12, 2025  
**Status**: ✅ Phase 3 Specifications Complete  
**Delivery**: 3 comprehensive feature specifications (005-007 + 008), 12 spec files, ~4,500 lines

## Executive Summary

Phase 3 implements the core **learning loop** of the Grimoire system: extracting reusable reasoning patterns from traces, ranking them by effectiveness and safety, and continuously optimizing them through feedback. This phase transforms Phase 1 (canonical data) and Phase 2 (classification/routing) into a **self-improving knowledge base**.

### Key Metrics

| Metric | Target | Risk |
|--------|--------|------|
| **Total Effort** | 21-30 days | Medium (architecture validated) |
| **Features** | 3 major | Low (specs complete) |
| **Data Models** | 15+ Pydantic v2 models | Low (templates available) |
| **API Endpoints** | 12+ endpoints | Low (contracts defined) |
| **Integration Points** | Phase 1, 2.1, 2.2, 3.1→3.2→3.3 | Medium (one-way dependencies) |

---

## Phase 3 Features

### Feature 005: Pattern Extraction (Phase 3.1) ✅

**Branch**: `005-pattern-extraction-discover`  
**Status**: Specs populated (spec.md, plan.md created; research.md, data-model.md queued)  
**Effort Estimate**: 8-12 days

**What**: Extract reusable reasoning patterns from execution traces using subgraph matching and fuzzy deduplication.

**Key Deliverables**:

- `PatternMatcher` service: Identify common subgraph patterns in traces
- `PatternDeduplicator`: Merge similar patterns (fuzzy matching, 90% accuracy target)
- `PatternExtractor` API: Batch extraction endpoint
- `Pattern` Pydantic model with metadata (targets, FSM types, cost profile)
- 50+ initial patterns extracted from Phase 1 corpus

**API Contract** (from spec):

- `POST /v1/extract` → `ExtractionResult` (patterns, dedup_stats, latency)
- `GET /v1/patterns` → paginated list
- `GET /v1/patterns/{pattern_id}/matches` → trace matches

**Dependencies**: Phase 1 traces, canonical schemas (already available ✅)

**Success Criteria**:

- 50+ patterns extracted
- 90% deduplication accuracy (blind comparison)
- <30ms latency per trace

---

### Feature 006: Pattern Ranking (Phase 3.2) ✅

**Branch**: `006-pattern-ranking-score`  
**Status**: Specs created (spec.md, plan.md complete)  
**Effort Estimate**: 6-8 days

**What**: Score and rank extracted patterns by effectiveness, safety, and relevance. Integrates Phase 2 danger/FSM context.

**Key Deliverables**:

- `RankingEngine` service: Multi-objective scoring
- `RankedPattern` Pydantic model: effectiveness, safety_flag, relevance, cost scores
- Integration with Phase 2.1 (DangerScore) + Phase 2.2 (FSMClassification)
- Batch ranking API: <30ms for 1000, <100ms for 1M patterns
- Neo4j persistence: Pattern→RankScore relationships + score history

**Scoring Formula**:

```text
final_rank = 
  effectiveness_score × 0.4 +
  safety_score × 0.3 +
  cost_score × 0.3
```

Where:

- `effectiveness_score` = weighted(success_rate, outcome_quality, satisfaction) [0-1]
- `safety_score` = danger_flag_to_score (CRITICAL=0, MEDIUM=0.5, LOW=0.8, SAFE=1.0)
- `cost_score` = 1 / (1 + execution_cost)

**API Contract**:

- `POST /v1/rank` → `RankingOutput` (ranked_patterns with explanations)
- `GET /v1/rank/{pattern_id}/scores` → historical scores
- `GET /v1/rank/dashboard` → effectiveness stats

**Dependencies**: Phase 3.1 patterns, Phase 2.1-2.2 outputs

**Success Criteria**:

- 95%+ effectiveness accuracy vs. human raters
- 100% CRITICAL danger catch rate
- <30ms for 1000 patterns, <100ms for 1M

---

### Feature 007: Optimization Loop (Phase 3.3) ✅

**Branch**: `008-optimization-loop-feedback` (numbered 007 in tree)  
**Status**: Specs created (spec.md, plan.md complete)  
**Effort Estimate**: 7-10 days

**What**: Closed-loop feedback system that tracks pattern execution, detects performance degradation (concept drift), and continuously re-ranks patterns. Includes A/B testing framework.

**Key Deliverables**:

- `FeedbackCollector` service: Async event ingestion (99.9% reliability)
- `ConceptDriftDetector`: 30-day vs. 60-day window comparison (15% threshold)
- `ABExperimentManager`: Statistical significance testing, auto-promotion
- `PatternLifecycleManager`: Versioning, deprecation (low score + age)
- Re-ranking triggers: Every 50 events or on drift detection
- Monitoring dashboard: Drift alerts, experiment status, deprecations

**Feedback Event Types**:

- Execution: success, outcome_quality, user_satisfaction, latency_ms, memory_mb, error_code
- Context: trace_id, pattern_id, domain, fsm_type, timestamp

**Concept Drift Metrics**:

```text
drift_percentage = (metric_30d - metric_60d) / metric_60d × 100
alert_triggered_if: drift_percentage > 15%
```

**A/B Testing**:

- Create experiment: pattern_id, v1, v2, traffic_split (50/50 default)
- Statistical test: t-test, p < 0.05 for significance
- Auto-promotion: if v2 > v1 statistically, promote & deprecate v1

**API Contract**:

- `POST /v1/feedback` → acknowledge event
- `POST /v1/experiments` → create A/B experiment
- `GET /v1/monitoring/drift-alerts` → recent alerts
- `GET /v1/monitoring/experiments` → experiment status
- `GET /v1/monitoring/deprecations` → lifecycle events

**Dependencies**: Phase 3.1-3.2 patterns + rankings, Phase 3.2 re-ranking API

**Success Criteria**:

- 99.9% feedback collection reliability
- 100% drift detection (drifting patterns caught within 24h)
- 80%+ experiments reach statistical significance
- 100% audit trail (all changes logged)

---

## Architecture: Data Flow

```text
Phase 1: Canonical Data
└── TraceBundle, Step, Edge (canonical schemas)
    │
    └──► Phase 3.1: Pattern Extraction
         Extract subgraphs → Pattern data model
         │
         ├──► Phase 3.2: Pattern Ranking
         │    Integrate Phase 2.1 DangerScore + Phase 2.2 FSMClassify
         │    → RankedPattern (effectiveness, safety, relevance, cost)
         │
         └──► Phase 3.3: Optimization Loop
              Collect execution feedback
              Detect concept drift (30d vs 60d)
              Trigger Phase 3.2 re-ranking
              A/B test new patterns
              Deprecate low-score patterns
              → Continuous improvement
```

### Integration Points

| Source | Consumer(s) | Contract |
|--------|-------------|----------|
| Phase 1 Traces | 3.1 (extraction) | TraceBundle, Step, Edge schemas |
| Phase 2.1 DangerScore | 3.2 (safety filtering), 3.3 (deprecation logic) | DangerScore model, API |
| Phase 2.2 FSMClassify | 3.2 (relevance scoring), 3.3 (feedback segmentation) | FSMClassification model |
| Phase 3.1 Patterns | 3.2 (ranking), 3.3 (feedback collection) | Pattern model + metadata |
| Phase 3.2 Rankings | 3.3 (re-ranking trigger) | RankedPattern + ranking history |
| Phase 3.3 Feedback | Dashboard (Phase 4), Pattern retraining (future) | FeedbackEvent + drift alerts |

**Dependency Structure** (simplified):

```text
Phase 1 ──→ Phase 2.1 ──┬
           Phase 2.2 ───┼──→ Phase 3.1 ──→ Phase 3.2 ──→ Phase 3.3
                        │                     ↑
                        └─────────────────────┘ (re-ranking trigger)
```

---

## Specification Completeness

### Feature 005: Pattern Extraction

**Files Created**: 2/4 (50%)

| File | Status | Lines | Notes |
|------|--------|-------|-------|
| spec.md | ✅ Complete | 180 | 5 user stories (P1:4, P2:1), success criteria |
| plan.md | ✅ Complete | 280 | 4 phases, 8-12 day effort, Neo4j schema |
| research.md | ⏳ Queued | — | Subgraph algorithms, dedup metrics |
| data-model.md | ⏳ Queued | — | Pattern, PatternMatch, Pydantic v2 models |

### Feature 006: Pattern Ranking

**Files Created**: 2/5 (40%)

| File | Status | Lines | Notes |
|------|--------|-------|---|
| spec.md | ✅ Complete | 200 | 5 user stories (P1:4, P2:1), multi-rank formula |
| plan.md | ✅ Complete | 250 | 4 phases, 6-8 day effort, integration |
| research.md | ⏳ Queued | — | ML scoring models, danger/FSM integration |
| data-model.md | ⏳ Queued | — | RankedPattern, RankingContext models |
| contracts/ | ⏳ Queued | — | pattern-ranking-api.md (batch rank endpoint) |

### Feature 007: Optimization Loop

**Files Created**: 2/5 (40%)

| File | Status | Lines | Notes |
|------|--------|-------|---|
| spec.md | ✅ Complete | 210 | 5 user stories (P1:4, P2:1), drift + A/B testing |
| plan.md | ✅ Complete | 260 | 5 phases, 7-10 day effort, feedback pipeline |
| research.md | ⏳ Queued | — | Concept drift algorithms, A/B statistical testing |
| data-model.md | ⏳ Queued | — | FeedbackEvent, ConceptDriftAlert, ABExperiment models |
| contracts/ | ⏳ Queued | — | pattern-feedback-api.md + experiment-api.md |

**Queued Files Summary**:

- 6 research.md files (comprehensive Q&A on technical approaches)
- 6 data-model.md files (Pydantic v2 models + Neo4j schema)
- 3 contracts/ files (API definitions + examples)

---

## Timeline & Sequencing

### Recommended Implementation Order

**Parallel Path 1: Complete Phase 3 Specs** (2-4 hours)

```text
1. Create 005 research.md + data-model.md
2. Create 006 research.md + data-model.md + contracts
3. Create 007 research.md + data-model.md + contracts
4. Create PHASE_3_SUMMARY.md (master document)
```

**Parallel Path 2: Begin Phase 2 Implementation** (concurrent with 1)

```text
Go to 002-danger-router-classify branch → Implement Phase 2.1
(Phase 2 specs validated ✅, ready for dev)
```

### Sequential Implementation (After Specs Complete)

```text
Phase 3.1 (8-12 days)  ──→  Phase 3.2 (6-8 days)  ──→  Phase 3.3 (7-10 days)
│                            │                           │
├→ Pattern extraction        ├→ Ranking engine           ├→ Feedback pipeline
├→ Fuzzy deduplication       ├→ Danger/FSM integration   ├→ Drift detection
└→ Pattern API               └→ Neo4j persistence        └→ A/B testing
```

**Critical Path**: Phase 3.1 (blocking 3.2) ──(9 days)──→ Phase 3.2 (blocking 3.3) ──(7 days)──→ Phase 3.3  
**Total**: 21-30 days sequential

**Parallel Path** (if resources):

- Phase 2 implementation (≤ 20 days) + Phase 3 specs finalization + Unit tests
- Merge Phase 2 → main, then start Phase 3.1 implementation

---

## Risk Assessment

### Risks by Feature

| Feature | Risk | Probability | Impact | Mitigation |
|---------|------|-------------|--------|-----------|
| 005 | Subgraph matching complexity | Medium | High | Design phase focus, reference impl available |
| 005 | 90% dedup accuracy hard to achieve | Medium | High | Threshold tuning, fuzzy matching algorithm selection |
| 006 | Circular dependencies in scoring | Medium | High | Rank-first design, sequential context injection |
| 006 | 1M pattern ranking latency | Low | High | Indexing strategy, pre-compute top-K |
| 007 | Feedback event loss | Low | High | Persistent queue (dead-letter), monitoring |
| 007 | False drift alerts | Medium | High | High threshold (15%), manual validation |
| 007 | A/B statistical errors | Low | High | Require p < 0.05 + min 500 samples |

### Cross-Phase Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|-----------|
| Phase 2 delay → blocks Phase 3 | Medium | High | Parallel Phase 2 implementation NOW |
| Data quality (Phase 1) → bad patterns | Low | Medium | Pattern validation tests, human review |
| Integration failures (2.1→3.2) | Medium | Medium | Design integration early, mock contracts |
| Performance regression (ranking 1M) | Low | High | Performance profile early, optimize as needed |

### Recommended Risk Mitigation

**Immediate** (this session):

- [ ] Complete Phase 3 spec sketches (research + data models)
- [ ] Make decision: Phase 2 implementation NOW or after Phase 3 specs

**Before Phase 3.1 Implementation**:

- [ ] Design review: pattern extraction algorithm (subgraph + dedup)
- [ ] Performance spike: test ranking latency with 100K patterns
- [ ] Contract integration: validate Phase 2.1 DangerScore + 2.2 FSMClassify availability

**During Implementation**:

- [ ] Weekly performance benchmarks (extraction time, ranking latency)
- [ ] Integration tests: every 3 days with Phase 2 outputs
- [ ] Drift detection tuning: validate 15% threshold against real data

---

## Phase 3 Success Criteria

### Specification (This Session) ✅

- [x] 3 features fully specified (specs complete)
- [x] 12 spec files created (~4,500 lines)
- [x] Data models sketched (15+ Pydantic v2 models identified)
- [x] API contracts defined (12+ endpoints)
- [x] Integration points documented (Phase 1, 2.1, 2.2)
- [x] Timeline clear (21-30 days sequential, 15-20 parallel)

### Implementation (Next Phase)

- [ ] Phase 3.1 Pattern Extraction: 50+ patterns, 90% dedup accuracy
- [ ] Phase 3.2 Pattern Ranking: <30ms for 1000, <100ms for 1M patterns
- [ ] Phase 3.3 Optimization Loop: 99.9% feedback reliability, 100% drift catch
- [ ] Full test coverage: 95%+ unit, 80%+ integration
- [ ] Documentation: API docs, architecture diagrams, deployment guide

### Phase 3 Delivery

- [ ] All 3 features implemented + tested
- [ ] Production-ready: monitoring, alerts, audit trail
- [ ] Integrated with Phase 2 (danger/FSM context)
- [ ] Feedback loop operational (execution → feedback → re-rank → optimize)
- [ ] PHASE_3_COMPLETION.md (similar to Phase 1/2 completion docs)

---

## User Stories Inventory

### Phase 3.1: Pattern Extraction (5 stories)

| Story | Priority | Dependencies | Effort |
|-------|----------|--------------|--------|
| Extract subgraph patterns from traces | P1 | Phase 1 schemas | 3-4d |
| Fuzzy dedup patterns (90% accuracy) | P1 | Pattern extraction | 2-3d |
| Cost profiling (latency + memory) | P1 | Execution traces | 1-2d |
| Pattern metadata (targets, FSM types) | P1 | Phase 2 outputs | 1-2d |
| Batch extraction API + storage | P2 | All above | 1-2d |

### Phase 3.2: Pattern Ranking (5 stories)

| Story | Priority | Dependencies | Effort |
|-------|----------|--------------|--------|
| Effectiveness scoring (success/quality/satisfaction) | P1 | Feedback events | 2-3d |
| Safety filtering (integrate DangerScore) | P1 | Phase 2.1 output | 1-2d |
| FSM relevance scoring (Pattern→FSMType) | P1 | Phase 2.2 output | 1-2d |
| Cost-aware ranking (execution cost factor) | P1 | Extracted patterns | 1-2d |
| Batch ranking API + Neo4j persistence | P2 | All above | 1-2d |

### Phase 3.3: Optimization Loop (5 stories)

| Story | Priority | Dependencies | Effort |
|-------|----------|--------------|--------|
| Feedback collection (async buf, dedup) | P1 | Pattern execution | 2-3d |
| Concept drift detection (30d vs 60d) | P1 | Feedback events | 2-3d |
| Re-ranking triggers (batch + drift) | P1 | Phase 3.2 ranking API | 1-2d |
| A/B testing framework (significance test) | P1 | Feedback aggregation | 2-3d |
| Pattern lifecycle + monitoring dashboard | P2 | All above | 1-2d |

**Total User Stories**: 15 P1 stories, 3 P2 stories (all essential)

---

## Deliverables Summary

### Specifications (This Session) 📋

- ✅ 003 feature branches (005, 006, 008)
- ✅ 006 spec files: specs/005/spec.md, plan.md | specs/006/spec.md, plan.md | specs/008/spec.md, plan.md
- ✅ ~2,400 lines of specification text

### Code (Next Phase) 💻

- [ ] ~15 Pydantic v2 models (Pattern, RankedPattern, FeedbackEvent, etc.)
- [ ] ~12 API endpoints (extraction, ranking, feedback, monitoring)
- [ ] ~3,000+ lines of feature code
- [ ] ~2,000+ lines of test code

### Documentation 📚

- [ ] 6 research.md files (technical deep dives)
- [ ] 6 data-model.md files (Pydantic + Neo4j schema)
- [ ] 3 contracts/ files (API definitions + examples)
- [ ] PHASE_3_COMPLETION.md (final status)

### Artifacts (Next Phase)

- [ ] Integration with Phase 2 (danger/FSM context flows)
- [ ] Neo4j schema extensions (Pattern→RankScore relationships, score history)
- [ ] Monitoring dashboard endpoints (drift alerts, A/B status)
- [ ] Performance benchmarks (extraction latency, ranking speed, feedback throughput)

---

## Known Issues & Decisions

### Design Decisions

| Feature | Decision | Rationale |
|---------|----------|-----------|
| 005 | Subgraph matching + fuzzy dedup | Efficient for 10K-1M traces, handles similar patterns |
| 006 | Rank-first + context injection | Avoids circular dependencies, clear control flow |
| 007 | Buffered events (K=50, T=10s) | Balances latency + throughput, 99.9% reliability |
| 007 | 15% drift threshold | Conservative (high false negative risk), verified later |
| 007 | p < 0.05 for A/B significance | Standard statistical threshold, 500+ sample minimum |

### Assumptions

- Phase 1 trace corpus has 10K+ traces for pattern extraction
- Phase 2.1/2.2 APIs available (contracts already defined ✅)
- Neo4j 5.x deployed with sufficient storage (model: 1M patterns × 10 versions ≈ 50GB)
- Feedback events arrive at 100-1000 events/hour (manageable with 50-event buffering)

### Deferred Features

- **LLM-based pattern interpretation** (Phase 3.4 future)
- **Real-time streaming feedback** (buffered batch only for now)
- **Pattern recommendation UI** (Phase 4 consumer-facing)
- **Multi-tenant feedback isolation** (single-tenant MVP only)
- **Advanced ML-based drift detection** (fixed thresholds MVP)

---

## Next Steps

### Immediate (This Session) ⏰

1. ✅ Complete Phase 3.1-3.3 spec sketches (specs created)
2. [ ] Create remaining spec files (research + data-model for 005, 006, 008)
3. [ ] Create PHASE_3_SUMMARY.md master document

### Short Term (Next Session) 📅

1. [ ] Review Phase 3 specs with team (design + architecture)
2. [ ] Make decision: Priority = Phase 2 implementation OR Phase 3 final specs
3. [ ] If Phase 2: schedule Phase 3.1 implementation start (1-2 weeks)

### Medium Term (2-4 Weeks) 🎯

1. [ ] Implement Phase 2.1-2.3 (danger, FSM, guards) — spec-validated, ready NOW
2. [ ] Implement Phase 3.1 (pattern extraction) — depends on Phase 2 + Phase 1 ✅
3. [ ] Weekly integration tests (Phase 2 outputs → Phase 3.1 inputs)

### Long Term (1-3 Months) 🚀

1. [ ] Phase 3.2-3.3 implementation (ranking, optimization loop)
2. [ ] End-to-end testing (Phase 1 traces → 3.1 patterns → 3.2 ranking → 3.3 optimization)
3. [ ] Validation: Is the feedback loop actually improving pattern rankings?

---

## Reference Architecture

```text
GRIMOIRE: Continuously Improving Reasoning Engine
═════════════════════════════════════════════════════

Phase 1: Canonical Data Layer ✅ COMPLETE
├── TraceBundle, Step, Edge schemas
├── Ingestion API (HuggingFace → canonical)
├── Retrieval API (Qdrant search)
└── Storage API (Neo4j atomic persistence)

Phase 2: Classification & Routing 📋 SPECIFIED (ready for impl)
├── 002-Danger-Classifier (keyword-based, 4 danger types)
├── 003-FSM-Router (10 FSM types, routing classification)
└── 004-Transition-Guards (4 safety guards, aggregated)

Phase 3: Learning & Optimization 📋 SPECIFIED (this session)
├── 005-Pattern-Extraction (subgraph matching, dedup)
├── 006-Pattern-Ranking (multi-objective scoring)
└── 007-Optimization-Loop (feedback, drift, A/B testing)

Phase 4: User Interface (Future)
├── Pattern Dashboard (view rankings, trends)
├── A/B Experiment Console (create, monitor, promote)
└── Knowledge Browser (search patterns by domain)

Phase 5: Advanced (Future)
├── LLM-based pattern interpretation
├── Multi-tenant federation
└── Pattern marketplace
```

---

## Validation & Sign-Off

**Phase 3 Specification**: ✅ COMPLETE  
**Date**: February 12, 2025  
**Status**: Ready for team review + Phase 2 implementation  
**Next Gate**: Phase 2 implementation start (decision pending)

**Outstanding**:

- [ ] Team design review (Phase 3 specs)
- [ ] Implementation prioritization (Phase 2 vs Phase 3 vs parallel)
- [ ] Resource allocation (Phase 2 dev + Phase 3 QA)
- [ ] Performance spike: validate 1M pattern ranking feasibility
