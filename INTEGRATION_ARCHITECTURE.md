# Grimoire Integration Architecture

**Version**: 1.0  
**Status**: Architecture Specification Complete  
**Date**: February 12, 2026  
**Scope**: Phases 1-3 (8 Features)

---

## Executive Summary

This document defines the complete integration architecture for Grimoire's 8-feature reasoning engine. It maps data flows, API contracts, storage schemas, and cross-feature dependencies to enable parallel development with clear integration points.

**Architecture Pattern**: Event-Driven Microservices with Shared Storage  
**Storage Strategy**: Neo4j (graph relationships) + Qdrant (vector search) + S3 (artifacts)  
**Communication**: REST APIs + Async Events (feedback loop)

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           GRIMOIRE SYSTEM                                   │
│                    Continuously Improving Reasoning Engine                    │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 1: FOUNDATION (Complete ✅)                                          │
│ Feature 001: Canonical Schema Implementation                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Input: HuggingFace datasets (OpenThoughts, etc.)                          │
│ • Process: Ingest → Normalize → Embed → Store                               │
│ • Output: Canonical traces (TraceBundle, Step, Edge) in Neo4j/Qdrant       │
│ • APIs: /ingest, /retrieve, /storage, /versioning                          │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 2: CLASSIFICATION & SAFETY (Specified 📋)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│ │ 002: Danger     │  │ 003: FSM        │  │ 004: Transition │              │
│ │    Router       │  │    Router       │  │    Guards       │              │
│ │    (Classify)   │  │    (Classify)   │  │    (Enforce)    │              │
│ └────────┬────────┘  └────────┬────────┘  └────────┬────────┘              │
│          │                    │                    │                       │
│          ▼                    ▼                    ▼                       │
│    DangerScore          FSMClassification    GuardDecision                │
│    [0-1] × 4 types      [10 types]           [ALLOW/BLOCK/WARN]           │
│          │                    │                    │                       │
│          └────────────────────┼────────────────────┘                       │
│                               │                                            │
│                               ▼                                            │
│                    Combined Safety Context                                 │
│                    (consumed by Phase 3)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PHASE 3: LEARNING & OPTIMIZATION (Specified 📋)                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐              │
│ │ 005: Pattern    │  │ 006: Pattern    │  │ 008: Optimization│             │
│ │    Extraction   │──│    Ranking      │──│    Loop         │              │
│ │    (Discover)   │  │    (Score)      │  │    (Feedback)   │              │
│ └─────────────────┘  └─────────────────┘  └─────────────────┘              │
│          │                    │                    │                       │
│          ▼                    ▼                    ▼                       │
│    Pattern (gSpan)      RankedPattern         FeedbackEvent                 │
│    + CostProfile        + ScoreBreakdown      + DriftAlert                 │
│          │                    │                    │                       │
│          └────────────────────┼────────────────────┘                       │
│                               │                                            │
│                               ▼                                            │
│                    ┌─────────────────────┐                                 │
│                    │   Pattern Library   │                                 │
│                    │   (Versioned +      │                                 │
│                    │    A/B Tested)      │                                 │
│                    └─────────────────────┘                                 │
│                               │                                            │
│                               ▼                                            │
│                    ┌─────────────────────┐                                 │
│                    │   Execution Engine  │◄───────────────────────────────┘
│                    │   (uses best patterns)│    Feedback Loop (async)
│                    └─────────────────────┘
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow Architecture

### 1. Ingestion Flow (Phase 1)

```
HuggingFace Dataset
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Ingestion  │────▶│   Canonical  │────▶│   Storage    │
│     API      │     │   Schema     │     │   Layer      │
│  /v1/ingest  │     │  Transform   │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          ▼                     ▼                     ▼
                   ┌────────────┐        ┌────────────┐        ┌────────────┐
                   │   Neo4j    │        │   Qdrant   │        │    S3      │
                   │  (Graph)   │        │  (Vector)  │        │ (Artifacts)│
                   │            │        │            │        │            │
                   │ • Trace    │        │ • Step     │        │ • Raw      │
                   │ • Step     │        │   vectors  │        │   traces   │
                   │ • Edge     │        │ • Metadata │        │ • Models   │
                   └────────────┘        └────────────┘        └────────────┘
```

**Key Data Models**:
- `TraceBundle`: Container with Trace + Steps + Edges
- `Step`: Individual reasoning step with embeddings
- `Edge`: Relationships between steps

**Storage Mapping**:
| Entity | Neo4j | Qdrant | S3 |
|--------|-------|--------|-----|
| Trace | Node (`Trace`) | - | Raw JSON |
| Step | Node (`Step`) | Vector + Payload | - |
| Edge | Relationship | - | - |
| Artifact | Reference | Reference | Binary |

---

### 2. Classification Flow (Phase 2)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         CLASSIFICATION PIPELINE                             │
└─────────────────────────────────────────────────────────────────────────────┘

Step/Trace Text
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ PARALLEL CLASSIFICATION (Independent)                                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────┐    ┌─────────────────────┐                      │
│  │ 002: Danger Router  │    │ 003: FSM Router     │                      │
│  │                     │    │                     │                      │
│  │ Input: text + role  │    │ Input: problem_text │                      │
│  │                     │    │                     │                      │
│  │ Process:            │    │ Process:            │                      │
│  │ • Keyword matching  │    │ • Keyword matching  │                      │
│  │ • Pattern detection │    │ • FSM type scoring  │                      │
│  │ • Score [0-1]       │    │ • Confidence [0-1]  │                      │
│  │                     │    │                     │                      │
│  │ Output:             │    │ Output:             │                      │
│  │ DangerScores        │    │ FSMClassification   │                      │
│  │ • ambiguity         │    │ • selected_fsm_id   │                      │
│  │ • adversarial       │    │ • confidence        │                      │
│  │ • irreversibility   │    │ • alternatives      │                      │
│  │ • institutional     │    │                     │                      │
│  └──────────┬──────────┘    └──────────┬──────────┘                      │
│             │                          │                                  │
│             └────────────┬─────────────┘                                  │
│                          ▼                                                │
│              ┌─────────────────────┐                                      │
│              │ Combined Context    │                                      │
│              │ (for Phase 3)       │                                      │
│              └──────────┬──────────┘                                      │
│                         │                                                 │
│                         ▼                                                 │
│              ┌─────────────────────┐                                      │
│              │ 004: Guard Decision │                                      │
│              │                     │                                      │
│              │ Input:              │                                      │
│              │ • DangerScores      │                                      │
│              │ • FSMClassification │                                      │
│              │ • Guard rules       │                                      │
│              │                     │                                      │
│              │ Process:            │                                      │
│              │ • Rule evaluation   │                                      │
│              │ • Aggregation       │                                      │
│              │ • Escalation check  │                                      │
│              │                     │                                      │
│              │ Output:             │                                      │
│              │ GuardDecision       │                                      │
│              │ • decision          │                                      │
│              │ • required_approvers│                                      │
│              │ • monitoring_flags  │                                      │
│              └─────────────────────┘                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**API Integration Points**:

| Source | Target | API | Data |
|--------|--------|-----|------|
| Phase 1 | 002 | `POST /v1/classify` | `trace_id`, `text_to_classify` |
| Phase 1 | 003 | `POST /v1/route` | `trace_id`, `problem_text` |
| 002+003 | 004 | Internal | `DangerScores`, `FSMClassification` |
| 002 | Neo4j | Cypher | `danger_*` properties on Step |
| 003 | Neo4j | Cypher | `fsm_type` property on Step |
| 004 | Neo4j | Cypher | Guard decision on Trace |

---

### 3. Learning Flow (Phase 3)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         LEARNING PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 1 Traces (Neo4j)
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 005: PATTERN EXTRACTION (Discover)                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Input: Subgraph from Neo4j (steps + edges)                                  │
│                                                                             │
│  Process:                                                                   │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                   │
│  │   gSpan     │───▶│   Fuzzy     │───▶│   Pattern   │                   │
│  │  Algorithm  │    │   Deduplic. │    │   Storage   │                   │
│  │             │    │   (Jaccard+ │    │             │                   │
│  │ • Frequent  │    │    GED)     │    │ • Neo4j:    │                   │
│  │   subgraph  │    │             │    │   Pattern   │                   │
│  │   mining    │    │ • 90%       │    │   nodes     │                   │
│  │             │    │   accuracy  │    │ • Qdrant:   │                   │
│  │ Output:     │    │             │    │   pattern   │                   │
│  │ Candidate   │    │ Output:     │    │   vectors   │                   │
│  │ patterns    │    │ Unique      │    │             │                   │
│  │             │    │ patterns    │    │             │                   │
│  └─────────────┘    └─────────────┘    └─────────────┘                   │
│                                                                             │
│  Output: Pattern + CostProfile                                              │
│  • pattern_id, steps[], edges[], frequency, cost_profile                   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 006: PATTERN RANKING (Score)                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Input: Pattern + Phase 2 Context                                           │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         MULTI-OBJECTIVE SCORING                      │   │
│  │                                                                      │   │
│  │   effectiveness (0.4)    safety (0.3)    relevance (0.2)    cost (0.1)│   │
│  │        │                    │               │              │        │   │
│  │        ▼                    ▼               ▼              ▼        │   │
│  │   ┌─────────┐          ┌─────────┐     ┌─────────┐    ┌─────────┐   │   │
│  │   │ Success │          │ Danger  │     │  FSM    │    │ Latency │   │   │
│  │   │  Rate   │          │ Scores  │     │  Match  │    │ Memory  │   │   │
│  │   │ Quality │          │ (002)   │     │ (003)   │    │ Errors  │   │   │
│  │   │Satisfact│          │         │     │         │    │         │   │   │
│  │   └────┬────┘          └────┬────┘     └────┬────┘    └────┬────┘   │   │
│  │        │                    │               │              │        │   │
│  │        └────────────────────┼───────────────┼──────────────┘        │   │
│  │                             ▼               ▼                       │   │
│  │                    ┌─────────────────────────────┐                   │   │
│  │                    │   final_rank_score =        │                   │   │
│  │                    │   0.4×E + 0.3×S + 0.2×R +   │                   │   │
│  │                    │   0.1×C                     │                   │   │
│  │                    └─────────────┬───────────────┘                   │   │
│  │                                  ▼                                  │   │
│  │                    ┌─────────────────────────────┐                   │   │
│  │                    │      RankedPattern          │                   │   │
│  │                    │  + ScoreBreakdown           │                   │   │
│  │                    └─────────────────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  API: POST /v1/rank (batch)                                                 │
│  Storage: Neo4j (ranking history), Qdrant (score vectors)                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 008: OPTIMIZATION LOOP (Feedback)                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    CONTINUOUS IMPROVEMENT LOOP                       │   │
│  │                                                                      │   │
│  │   Pattern Execution ──▶ Feedback Collection ──▶ Analysis         │   │
│  │         │                      │                      │              │   │
│  │         │                      ▼                      ▼              │   │
│  │         │               ┌─────────────┐      ┌─────────────┐        │   │
│  │         │               │  Feedback   │      │   CUSUM     │        │   │
│  │         │               │   Event     │      │   Drift     │        │   │
│  │         │               │   (K=50)    │      │ Detection   │        │   │
│  │         │               └──────┬──────┘      └──────┬──────┘        │   │
│  │         │                      │                      │              │   │
│  │         │                      ▼                      ▼              │   │
│  │         │               ┌─────────────┐      ┌─────────────┐        │   │
│  │         │               │   A/B Test  │◄─────│  Drift      │        │   │
│  │         │               │   Engine    │      │  Alert      │        │   │
│  │         │               └──────┬──────┘      └─────────────┘        │   │
│  │         │                      │                                     │   │
│  │         │                      ▼                                     │   │
│  │         │               ┌─────────────┐                             │   │
│  │         └───────────────│   Pattern   │                             │   │
│  │                         │   Update    │                             │   │
│  │                         │   (Version)   │                             │   │
│  │                         └─────────────┘                             │   │
│  │                                                                      │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  Key Metrics:                                                               │
│  • Feedback reliability: 99.9%                                             │
│  • Drift threshold: 15% effectiveness decline                              │
│  • A/B significance: p < 0.05, n ≥ 500                                    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## API Contract Matrix

### Cross-Feature API Dependencies

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         API DEPENDENCY GRAPH                                │
└─────────────────────────────────────────────────────────────────────────────┘

Phase 1                    Phase 2                    Phase 3
┌─────────┐              ┌─────────┐               ┌─────────┐
│ 001     │──────────────▶│ 002     │──────────────▶│ 006     │
│ Ingest  │   /classify   │ Danger  │  DangerScores │ Pattern │
│         │               │ Router  │               │ Ranking │
└────┬────┘               └────┬────┘               └────┬────┘
     │                         │                         │
     │    /route               │   FSMClassification   │
     └─────────────────────────▶│ 003     │──────────────▶│
                               │ FSM     │               │
                               │ Router  │               │
                               └────┬────┘               │
                                    │                    │
                                    │                    │
                                    ▼                    │
                               ┌─────────┐               │
                               │ 004     │               │
                               │ Guards  │               │
                               │         │               │
                               └─────────┘               │
                                                        │
     ┌────────────────────────────────────────────────────┘
     │
     ▼
┌─────────┐              ┌─────────┐               ┌─────────┐
│ 001     │──────────────▶│ 005     │──────────────▶│ 008     │
│ Traces  │   Subgraphs   │ Pattern │   Patterns    │ Optim.  │
│ (Neo4j) │               │ Extract │               │ Loop    │
└─────────┘               └─────────┘               └─────────┘
```

### API Endpoint Summary

| Feature | Endpoint | Method | Input | Output | Latency |
|---------|----------|--------|-------|--------|---------|
| **001** | `/v1/ingest` | POST | `IngestionRequest` | `IngestionResponse` | < 5 min |
| **001** | `/v1/retrieve` | POST | `RetrievalQuery` | `RetrievalResult` | < 100ms |
| **002** | `/v1/classify` | POST | `DangerClassifierRequest` | `DangerClassifierResponse` | < 50ms |
| **002** | `/v1/classify/batch` | POST | `DangerClassifierBatchRequest` | `DangerClassifierBatchResponse` | < 100ms |
| **003** | `/v1/route` | POST | `FSMRouterRequest` | `FSMRouterResponse` | < 100ms |
| **003** | `/v1/route/batch` | POST | `FSMRouterBatchRequest` | `FSMRouterBatchResponse` | < 100ms |
| **004** | Internal | - | `DangerScores` + `FSMClassification` | `GuardDecision` | < 20ms |
| **005** | `/v1/extract` | POST | `ExtractionRequest` | `ExtractionResult` | < 30s |
| **006** | `/v1/rank` | POST | `RankingRequest` | `RankingResponse` | < 30s |
| **006** | `/v1/scores` | GET | `pattern_id` | `RankedPattern` | < 10ms |
| **008** | `/v1/feedback` | POST | `FeedbackEvent` | `Ack` | < 5ms |
| **008** | `/v1/drift` | GET | - | `DriftStatus` | < 10ms |

---

## Storage Schema Integration

### Neo4j Graph Schema

```cypher
// Core Entities (Phase 1)
(:Trace {trace_id, domain, created_at, ...})
(:Step {step_id, content, embedding_id, ...})
(:Edge {edge_id, edge_type, ...})

// Phase 2 Extensions
(:Step)-[:HAS_DANGER_SCORE {ambiguity, adversarial, irreversibility, institutional}]->(:DangerScore)
(:Step)-[:HAS_FSM_CLASSIFICATION {fsm_type, confidence}]->(:FSMClassification)
(:Trace)-[:HAS_GUARD_DECISION {decision, required_approvers}]->(:GuardDecision)

// Phase 3 Extensions
(:Pattern {pattern_id, frequency, created_at, ...})
(:Pattern)-[:CONTAINS_STEP]->(:Step)
(:Pattern)-[:HAS_COST_PROFILE]->(:CostProfile)
(:Pattern)-[:HAS_RANKING {score, version}]->(:RankedPattern)
(:Pattern)-[:HAS_VERSION]->(:PatternVersion)
(:Pattern)-[:PART_OF_EXPERIMENT]->(:ABExperiment)

// Relationships
(:Trace)-[:CONTAINS]->(:Step)
(:Step)-[:FOLLOWS]->(:Step)
(:Pattern)-[:SIMILAR_TO {similarity_score}]->(:Pattern)
(:Pattern)-[:SUPERSEDES]->(:Pattern)
```

### Qdrant Collections

| Collection | Vector Dim | Payload Fields | Purpose |
|------------|------------|----------------|---------|
| `steps` | 384/768 | `trace_id`, `step_id`, `content_hash`, `domain` | Semantic search |
| `patterns` | 384/768 | `pattern_id`, `fsm_type`, `frequency`, `rank_score` | Pattern retrieval |
| `step_windows` | 384/768 | `window_id`, `trace_id`, `danger_scores` | Danger classification |

---

## Event Flow & Async Processing

### Feedback Loop Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EVENT-DRIVEN FEEDBACK                               │
└─────────────────────────────────────────────────────────────────────────────┘

Pattern Execution
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Pattern    │────▶│   Feedback   │────▶│   Buffer     │
│   Engine     │     │   Collector  │     │   (K=50)     │
│              │     │              │     │              │
└──────────────┘     └──────────────┘     └──────┬───────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            ▼                            │
                    │                   ┌──────────────┐                       │
                    │                   │   Process    │                       │
                    │                   │   Batch      │                       │
                    │                   └──────┬───────┘                       │
                    │                          │                              │
                    ▼                          ▼                              ▼
           ┌──────────────┐          ┌──────────────┐               ┌──────────────┐
           │   Update     │          │   CUSUM      │               │   A/B Test   │
           │   Pattern    │          │   Drift      │               │   Update     │
           │   Stats      │          │   Detect     │               │              │
           └──────────────┘          └──────┬───────┘               └──────────────┘
                                            │
                                            ▼
                                   ┌──────────────┐
                                   │   Trigger    │
                                   │   Re-rank    │
                                   │   if drift   │
                                   └──────────────┘
```

**Event Types**:
1. `pattern.executed` → Update execution count
2. `pattern.succeeded` → Update success rate
3. `pattern.failed` → Update error rate + alert
4. `feedback.batch_ready` → Trigger analysis
5. `drift.detected` → Trigger re-ranking
6. `ab.test_complete` → Promote winning pattern

---

## Integration Points & Contracts

### Phase 1 → Phase 2

| Source | Target | Contract | Location |
|--------|--------|----------|----------|
| `TraceBundle` | Danger Router | `trace_id`, `steps[].content` | `specs/002/contract` |
| `TraceBundle` | FSM Router | `trace_id`, `problem_text` | `specs/003/contract` |
| Neo4j Step | Both | `step_id`, `content`, `embedding` | Shared storage |

### Phase 2 → Phase 3

| Source | Target | Contract | Location |
|--------|--------|----------|----------|
| `DangerScores` | Pattern Ranking | `danger_scores[]` | `specs/006/contract` |
| `FSMClassification` | Pattern Ranking | `fsm_type`, `confidence` | `specs/006/contract` |
| Combined | Pattern Extraction | Context for subgraph queries | `specs/005/plan` |

### Phase 3 Internal

| Source | Target | Contract | Notes |
|--------|--------|----------|-------|
| Pattern Extraction | Pattern Ranking | `Pattern` + `CostProfile` | Neo4j + Qdrant |
| Pattern Ranking | Optimization Loop | `RankedPattern` + `ScoreBreakdown` | Event stream |
| Optimization Loop | Pattern Ranking | `FeedbackEvent` | Async buffer |

---

## Deployment Architecture

### Service Topology

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DEPLOYMENT VIEW                                     │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway                                    │
│                    (Rate limiting, Auth, Routing)                           │
└─────────────────────────────────────────────────────────────────────────────┘
       │              │              │              │
       ▼              ▼              ▼              ▼
┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐
│  Ingestion │ │  Danger    │ │   FSM      │ │  Pattern   │
│  Service   │ │  Service   │ │  Router    │ │  Services  │
│  (001)     │ │  (002)     │ │  (003)     │ │  (005-008) │
│            │ │            │ │            │ │            │
│ • /ingest  │ │ • /classify│ │ • /route   │ │ • /extract │
│ • /retrieve│ │ • /config  │ │ • /config  │ │ • /rank    │
│ • /storage │ │            │ │            │ │ • /feedback│
└─────┬──────┘ └─────┬──────┘ └─────┬──────┘ └─────┬──────┘
      │              │              │              │
      └──────────────┼──────────────┼──────────────┘
                     │              │
                     ▼              ▼
            ┌────────────┐  ┌────────────┐
            │   Neo4j    │  │   Qdrant   │
            │   Cluster  │  │   Cluster  │
            │            │  │            │
            │ • Traces   │  │ • Vectors  │
            │ • Patterns │  │ • Metadata │
            │ • Rankings │  │            │
            └────────────┘  └────────────┘
```

### Scaling Strategy

| Component | Scaling | Strategy |
|-----------|---------|----------|
| Ingestion | Horizontal | Batch processing, parallel workers |
| Danger Router | Horizontal | Stateless, cache configs |
| FSM Router | Horizontal | Stateless, hot-reload configs |
| Pattern Extraction | Vertical | gSpan is memory-intensive |
| Pattern Ranking | Horizontal | Shard by pattern ID range |
| Optimization Loop | Horizontal | Async event processing |

---

## Error Handling & Resilience

### Failure Modes

| Component | Failure | Mitigation |
|-----------|---------|------------|
| Neo4j | Unavailable | Retry + circuit breaker + read replicas |
| Qdrant | Unavailable | Degrade to Neo4j-only queries |
| Classification | Timeout | Return default scores + log |
| Pattern Extraction | OOM | Reduce batch size + retry |
| Feedback Buffer | Full | Drop oldest + alert |

### Circuit Breaker Config

```yaml
circuit_breakers:
  neo4j:
    failure_threshold: 5
    recovery_timeout: 30s
    half_open_max_calls: 3
  qdrant:
    failure_threshold: 3
    recovery_timeout: 10s
    half_open_max_calls: 2
```

---

## Monitoring & Observability

### Key Metrics

| Category | Metric | Target | Alert |
|----------|--------|--------|-------|
| **Latency** | Ingestion | < 5 min | > 10 min |
| **Latency** | Classification | < 50ms | > 100ms |
| **Latency** | Pattern Ranking | < 30s | > 60s |
| **Accuracy** | Danger detection | > 80% | < 70% |
| **Accuracy** | FSM routing | > 85% | < 75% |
| **Accuracy** | Pattern dedup | > 90% | < 85% |
| **Reliability** | Feedback delivery | 99.9% | < 99% |
| **Drift** | False positive rate | < 5% | > 10% |

### Distributed Tracing

```
Trace ID: trace-001-abcd
├── Phase 1: Ingestion (5 min)
├── Phase 2: Classification (50ms)
│   ├── Danger Router (20ms)
│   └── FSM Router (25ms)
├── Phase 3: Pattern Match (100ms)
│   ├── Extract candidates (80ms)
│   └── Rank patterns (15ms)
└── Phase 3: Execution (varies)
```

---

## Development Roadmap

### Implementation Order

```
Phase 1: Foundation ✅
├── 001: Canonical Schema (COMPLETE)

Phase 2: Safety (Ready to Implement)
├── 002: Danger Router (7-11 days)
├── 003: FSM Router (4-6 days)
└── 004: Transition Guards (3-4 days)
    └── Parallel with 002-003

Phase 3: Learning (Ready to Implement)
├── 005: Pattern Extraction (8-12 days)
│   └── Depends on: Phase 1
├── 006: Pattern Ranking (6-8 days)
│   └── Depends on: 005 + Phase 2
└── 008: Optimization Loop (7-10 days)
    └── Depends on: 006

Total Sequential: 35-51 days
Total Parallel (Phase 2+3): 25-35 days
```

---

## Appendix: Data Model Reference

### Core Types

```python
# Phase 1
class TraceBundle(BaseModel):
    trace: Trace
    steps: List[Step]
    edges: List[Edge]
    artifacts: List[Artifact]

# Phase 2
class DangerScores(BaseModel):
    ambiguity: float  # [0, 1]
    adversarial: float
    irreversibility: float
    institutional: float

class FSMClassification(BaseModel):
    selected_fsm_id: str
    confidence: float  # [0, 1]
    alternatives: List[FSMOption]

class GuardDecision(BaseModel):
    decision: Literal["ALLOW", "BLOCK", "WARN", "ESCALATE"]
    required_approvers: List[str]
    monitoring_flags: List[str]

# Phase 3
class Pattern(BaseModel):
    pattern_id: str
    steps: List[PatternStep]
    edges: List[PatternEdge]
    frequency: int
    cost_profile: CostProfile

class RankedPattern(BaseModel):
    pattern: Pattern
    effectiveness_score: float
    safety_score: float
    relevance_score: float
    cost_score: float
    final_rank_score: float
    score_breakdown: ScoreBreakdown

class FeedbackEvent(BaseModel):
    pattern_id: str
    execution_id: str
    success: bool
    quality_score: float
    latency_ms: float
    timestamp: datetime
```

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-12 | AI Assistant | Initial integration architecture |

**Next Steps**
1. Review individual feature specifications
2. Define detailed integration test cases
3. Create service interface definitions
4. Set up CI/CD pipeline for cross-feature testing
