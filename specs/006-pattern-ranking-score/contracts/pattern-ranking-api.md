# Contract: Pattern Ranking API

**Service**: Phase 3.2 Pattern Ranking Engine  
**Version**: 1.0  
**Status**: Specification (not implemented)

---

## Overview

Batch API for ranking extracted patterns using multi-objective scoring (effectiveness, safety, relevance, cost).

**Base URL**: `https://api.grimoire.local/v1`  
**Authentication**: Service-to-service (mutual TLS, or API key)  
**Rate Limit**: 1000 requests/min per client

---

## Endpoints

### 1. Rank Patterns (Batch)

**Endpoint**: `POST /rank`  
**Description**: Rank a batch of patterns given execution context  
**Timeout**: 30 seconds (for 1000 patterns)

#### Request

```json
{
  "pattern_ids": [
    "pat_001",
    "pat_002",
    "pat_003"
  ],
  "context": {
    "current_fsm_type": "DECISION",
    "current_domain": "ml",
    "danger_scores": [
      {
        "pattern_id": "pat_001",
        "danger_types": ["LOW"],
        "severity": 0.1,
        "reason": "Minor resource overhead"
      },
      {
        "pattern_id": "pat_002",
        "danger_types": [],
        "severity": 0.0,
        "reason": null
      },
      {
        "pattern_id": "pat_003",
        "danger_types": ["MEDIUM"],
        "severity": 0.5,
        "reason": "Reversibility concerns"
      }
    ],
    "execution_context": {
      "user_id": "user_123",
      "request_id": "req_456"
    }
  },
  "include_metadata": true,
  "limit_top_k": null
}
```

**Request Schema**:

```text
POST /rank HTTP/1.1
Content-Type: application/json
Authorization: Bearer <token> OR X-API-Key: <key>

{
  "pattern_ids": List[String] (required, 1-1M items),
  "context": {
    "current_fsm_type": String (optional),
    "current_domain": String (optional, enum: ["ml", "finance", "legal", "healthcare", "general"]),
    "danger_scores": List[DangerScore] (optional),
    "execution_context": Object (optional)
  },
  "include_metadata": Boolean (optional, default: true),
  "limit_top_k": Int (optional, if set return only top-K)
}
```

#### Response (Success)

**Status**: 200 OK

```json
{
  "ranking_id": "rank_xyz789",
  "ranked_patterns": [
    {
      "pattern_id": "pat_001",
      "effectiveness_score": 0.90,
      "safety_score": 0.80,
      "safety_level": "LOW",
      "relevance_score": 1.00,
      "cost_score": 0.95,
      "final_rank_score": 0.88,
      "score_breakdown": {
        "effectiveness": {
          "success_rate": 0.90,
          "avg_quality": 9.0,
          "avg_satisfaction": 4.5,
          "weighted": 0.90
        },
        "safety": {
          "danger_type": "LOW",
          "reason": "Minor resource overhead",
          "mapped_score": 0.80
        },
        "relevance": {
          "fsm_match": ["DECISION", "CONDITIONAL"],
          "jaccard": 1.00
        },
        "cost": {
          "latency_ms": 25.0,
          "memory_mb": 5.0,
          "error_rate": 0.01,
          "score": 0.95
        }
      },
      "fsm_type": "DECISION",
      "domain_context": "ml",
      "ranked_at": "2026-02-12T15:30:00Z",
      "ranking_version": 1
    },
    {
      "pattern_id": "pat_002",
      "effectiveness_score": 0.75,
      "safety_score": 1.00,
      "safety_level": "SAFE",
      "relevance_score": 0.50,
      "cost_score": 0.80,
      "final_rank_score": 0.79,
      "score_breakdown": { /* ... */ },
      "fsm_type": "DECISION",
      "domain_context": "ml",
      "ranked_at": "2026-02-12T15:30:00Z",
      "ranking_version": 1
    },
    {
      "pattern_id": "pat_003",
      "effectiveness_score": 0.60,
      "safety_score": 0.50,
      "safety_level": "MEDIUM",
      "relevance_score": 0.75,
      "cost_score": 0.70,
      "final_rank_score": 0.61,
      "score_breakdown": { /* ... */ },
      "fsm_type": "DECISION",
      "domain_context": "ml",
      "ranked_at": "2026-02-12T15:30:00Z",
      "ranking_version": 1
    }
  ],
  "stats": {
    "num_ranked": 3,
    "num_critical": 0,
    "num_safe": 1,
    "num_medium": 1,
    "num_low": 1,
    "avg_rank_score": 0.76
  },
  "ranking_duration_ms": 8.5,
  "ranked_at": "2026-02-12T15:30:00Z"
}
```

#### Response (Error)

**Status**: 400 Bad Request (validation error)

```json
{
  "error": "INVALID_REQUEST",
  "message": "Invalid pattern_id: pat_missing",
  "details": {
    "invalid_ids": ["pat_missing"]
  }
}
```

**Status**: 500 Internal Server Error

```json
{
  "error": "RANKING_FAILED",
  "message": "Failed to rank patterns",
  "ranking_id": "rank_xyz789",
  "details": {
    "failed_count": 1,
    "failed_ids": ["pat_003"],
    "reason": "Pattern not found in database"
  }
}
```

---

### 2. Get Pattern Ranking History

**Endpoint**: `GET /rank/{pattern_id}/scores`  
**Description**: Retrieve historical rankings for a specific pattern  
**Timeout**: 5 seconds

#### Request

```text
GET /rank/pat_001/scores?days=30&limit=100 HTTP/1.1
Authorization: Bearer <token>
```

**Query Parameters**:

- `days`: Int (optional, default 30) - How many days of history
- `limit`: Int (optional, default 100, max 1000) - Max snapshots
- `include_trend`: Boolean (optional, default true) - Include trend analysis

#### Response

**Status**: 200 OK

```json
{
  "pattern_id": "pat_001",
  "snapshots": [
    {
      "pattern_id": "pat_001",
      "final_rank_score": 0.88,
      "effectiveness_score": 0.90,
      "safety_score": 0.80,
      "relevance_score": 1.00,
      "cost_score": 0.95,
      "ranked_at": "2026-02-12T15:30:00Z"
    },
    {
      "pattern_id": "pat_001",
      "final_rank_score": 0.85,
      "effectiveness_score": 0.87,
      "safety_score": 0.80,
      "relevance_score": 0.90,
      "cost_score": 0.95,
      "ranked_at": "2026-02-11T15:30:00Z"
    }
  ],
  "avg_rank_score_7d": 0.86,
  "trend": "STABLE",
  "last_updated": "2026-02-12T15:30:00Z"
}
```

---

### 3. Get Ranking Dashboard Stats

**Endpoint**: `GET /rank/dashboard`  
**Description**: Aggregate statistics across all patterns  
**Timeout**: 10 seconds

#### Request

```text
GET /rank/dashboard?domain=ml HTTP/1.1
Authorization: Bearer <token>
```

**Query Parameters**:

- `domain`: String (optional) - Filter by domain
- `fsm_type`: String (optional) - Filter by FSM type

#### Response

**Status**: 200 OK

```json
{
  "total_patterns": 387,
  "avg_rank_score": 0.71,
  "percentiles": {
    "p50": 0.72,
    "p75": 0.85,
    "p90": 0.92,
    "p99": 0.98
  },
  "by_safety_level": {
    "CRITICAL": 2,
    "HIGH": 5,
    "MEDIUM": 15,
    "LOW": 45,
    "SAFE": 320
  },
  "by_domain": {
    "ml": {
      "count": 150,
      "avg_rank_score": 0.75
    },
    "finance": {
      "count": 120,
      "avg_rank_score": 0.68
    },
    "general": {
      "count": 117,
      "avg_rank_score": 0.70
    }
  },
  "trend_7d": {
    "avg_rank_score_change": -0.02,
    "patterns_improving": 120,
    "patterns_degrading": 45,
    "patterns_stable": 222
  },
  "dashboard_generated_at": "2026-02-12T15:30:00Z"
}
```

---

## Error Codes

| Code | HTTP Status | Description |
|------|------------|-------------|
| `INVALID_REQUEST` | 400 | Malformed request (validation failed) |
| `UNAUTHORIZED` | 401 | Authentication failed |
| `FORBIDDEN` | 403 | Not authorized for this operation |
| `PATTERN_NOT_FOUND` | 404 | Pattern ID doesn't exist |
| `RANKING_FAILED` | 500 | Ranking computation failed |
| `RESOURCE_EXHAUSTED` | 503 | Rate limit exceeded or service overloaded |

---

## SLAs & Performance

| Metric | Target |
|--------|--------|
| Latency (p50, 100 patterns) | <5ms |
| Latency (p95, 100 patterns) | <10ms |
| Latency (p50, 1000 patterns) | <25ms |
| Latency (p95, 1000 patterns) | <50ms |
| Latency (p50, 100K patterns) | <500ms |
| Latency (p95, 100K patterns) | <1000ms |
| Availability | 99.9% uptime |
| Error rate | <0.1% |

---

## Integration Points

### Inputs (Dependencies)

**Phase 2.1 (Danger Classifier)**

- Consumes: DangerScore objects
- Contract: Provides safety_level mapping

**Phase 2.2 (FSM Router)**

- Consumes: FSMClassification
- Contract: Provides current_fsm_type for relevance scoring

**Phase 3.1 (Pattern Extraction)**

- Consumes: Pattern metadata (FSM types, domains)
- Contract: Expects patterns in Neo4j with indexed scores

### Outputs (Consumers)

**Phase 3.3 (Optimization Loop)**

- Provides: RankedPattern scores + history
- Contract: Re-ranking triggers when feedback arrives

---

## Examples

### Example 1: Rank Patterns for Decision-Making

User is solving a ML optimization problem, currently in DECISION-making FSM state.

```bash
curl -X POST https://api.grimoire.local/v1/rank \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer token_123" \
  -d '{
    "pattern_ids": ["pat_001", "pat_002", "pat_003"],
    "context": {
      "current_fsm_type": "DECISION",
      "current_domain": "ml",
      "danger_scores": [
        {"pattern_id": "pat_001", "danger_types": [], "severity": 0.0},
        {"pattern_id": "pat_002", "danger_types": ["MEDIUM"], "severity": 0.5},
        {"pattern_id": "pat_003", "danger_types": ["LOW"], "severity": 0.1}
      ]
    },
    "include_metadata": true
  }'
```

**Response**: pat_001 ranked highest (0.88), pat_003 second (0.82), pat_002 third (0.61 due to MEDIUM danger)

### Example 2: Retrieve Historical Trend

Check if a pattern has improved or degraded over time.

```bash
curl https://api.grimoire.local/v1/rank/pat_001/scores?days=7&include_trend=true \
  -H "Authorization: Bearer token_123"
```

**Response**: Shows STABLE trend over 7 days, avg_score 0.86

### Example 3: Dashboard Stats

Monitor overall pattern quality across all domains.

```bash
curl https://api.grimoire.local/v1/rank/dashboard \
  -H "Authorization: Bearer token_123"
```

**Response**: 387 total patterns, average rank 0.71, 320 SAFE, 2 CRITICAL (flagged for review)
