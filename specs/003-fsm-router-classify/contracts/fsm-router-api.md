# API Contract: FSM Router

**Version**: 1.0  
**Status**: Specification  
**Base URL**: `http://localhost:8000/v1`

---

## Quick Reference

| Endpoint | Method | Purpose | Latency |
|----------|--------|---------|---------|
| `/route` | POST | Route single problem to FSM | < 100ms |
| `/route/batch` | POST | Route multiple problems | < 100ms per problem |
| `/config` | GET | Get routing configuration | < 10ms |
| `/config` | PUT | Update routing configuration | < 10ms |
| `/health` | GET | Health check | < 5ms |

---

## API Endpoints

### 1. Route Single Problem

```
POST /v1/route
```

**Request**

```json
{
  "trace_id": "trace-001-abcd",
  "problem_text": "Why do database queries timeout under load?",
  "context": {
    "domain": "backend",
    "user_level": "architect"
  },
  "optional_fsm_hints": null
}
```

**Response (200)**

```json
{
  "trace_id": "trace-001-abcd",
  "route": {
    "selected_fsm_id": "fsm_diagnose_fix",
    "selected_fsm_name": "Diagnose & Fix",
    "confidence": 0.85,
    "reasoning": "Keywords matched (7/7): debug, timeout, root cause, why → fsm_diagnose_fix",
    "alternative_fsms": [
      {
        "fsm_id": "fsm_optimize",
        "fsm_name": "Optimize",
        "confidence": 0.45
      }
    ]
  },
  "routing_ms": 42,
  "router_version": "1.0.0",
  "computed_at": "2024-01-15T10:30:45.123456Z"
}
```

---

### 2. Route Batch Problems

```
POST /v1/route/batch
```

**Request**

```json
{
  "traces": [
    {
      "trace_id": "trace-001",
      "problem_text": "Debug why async tasks timeout",
      "context": null
    },
    {
      "trace_id": "trace-002",
      "problem_text": "Design a new caching strategy",
      "context": {"domain": "architecture"}
    }
  ],
  "parallel": true
}
```

**Response (200)**

```json
{
  "results": [
    {
      "trace_id": "trace-001",
      "route": {
        "selected_fsm_id": "fsm_diagnose_fix",
        "confidence": 0.88
      },
      "routing_ms": 35
    },
    {
      "trace_id": "trace-002",
      "route": {
        "selected_fsm_id": "fsm_design_decide",
        "confidence": 0.80
      },
      "routing_ms": 38
    }
  ],
  "failed": [],
  "total_ms": 95
}
```

---

### 3. Get Configuration

```
GET /v1/config
```

**Response (200)**

```json
{
  "fsm_keywords": {
    "fsm_diagnose_fix": [
      "bug", "debug", "error", "fix", "root cause",
      "why", "not working", "broken", "fail"
    ],
    "fsm_design_decide": [
      "design", "architect", "build", "choose", "option",
      "alternative", "compare", "decision", "which"
    ],
    "fsm_optimize": [
      "performance", "speed", "optimize", "faster", "slow",
      "latency", "throughput", "tune", "improve"
    ],
    "fsm_verify": [
      "test", "verify", "validate", "check", "hypothesis",
      "confirm", "assertion"
    ],
    "fsm_transform": [
      "reshape", "restructure", "reorganize", "rearchitect"
    ],
    "fsm_operate_harden": [
      "stabilize", "harden", "production", "deploy", "operationalize",
      "secure", "resilience", "reliability"
    ],
    "fsm_clarify_frame": [
      "clarify", "scope", "define", "what", "unclear", "vague"
    ],
    "fsm_postmortem": [
      "postmortem", "failure", "incident", "analyze", "learn", "lessons"
    ],
    "fsm_resolve_conflict": [
      "conflict", "negotiate", "consensus", "stakeholder", "constraint",
      "tradeoff"
    ],
    "fsm_adversarial_loop": [
      "adversarial", "attack", "defense", "anticipate", "threat",
      "exploit", "security"
    ]
  },
  "confidence_threshold": 0.5,
  "default_fsm": "fsm_clarify_frame",
  "keyword_weights": {}
}
```

---

### 4. Update Configuration

```
PUT /v1/config
```

**Request** (partial update)

```json
{
  "confidence_threshold": 0.6,
  "fsm_keywords": {
    "fsm_adversarial_loop": [
      "adversarial", "attack", "defense", "anticipate", "threat",
      "exploit", "security", "strengthen"
    ]
  }
}
```

**Response (200)**

```json
{
  "fsm_keywords": {
    "...": "..."
  },
  "confidence_threshold": 0.6,
  "default_fsm": "fsm_clarify_frame"
}
```

---

### 5. Health Check

```
GET /v1/health
```

**Response (200)**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "router_ready": true,
  "keywords_loaded": true,
  "uptime_ms": 3600000
}
```

---

## Error Responses

### 400: Bad Request

```json
{
  "error": "bad_request",
  "message": "Invalid trace_id format",
  "details": {
    "field": "trace_id",
    "expected": "UUID or trace-NNN-XXXX format",
    "received": "bad-id"
  }
}
```

### 422: Validation Error

```json
{
  "error": "validation_error",
  "message": "Request validation failed",
  "details": [
    {
      "field": "problem_text",
      "error": "String too short (min 10 chars)",
      "received": "short"
    },
    {
      "field": "problem_text",
      "error": "String too long (max 5000 chars)",
      "received": 15000
    }
  ]
}
```

### 500: Router Error

```json
{
  "error": "router_error",
  "message": "Keyword matching failed; returning default FSM",
  "details": {
    "error_msg": "Regex compilation failed",
    "fallback_fsm": "fsm_clarify_frame",
    "fallback_confidence": 0.0
  }
}
```

---

## Request/Response Models

### FSMRouterRequest

```
{
  "trace_id": string (required)
    format: "trace-NNN-XXXX" or UUID
    example: "trace-001-abcd"
  
  "problem_text": string (required)
    minLength: 10
    maxLength: 5000
    example: "Debug the timeout issue"
  
  "context": object (optional)
    properties:
      "domain": string (optional) - backend, frontend, data, etc.
      "user_level": string (optional) - junior, senior, architect
      "language": string (optional) - en, es, fr, etc.
  
  "optional_fsm_hints": array (optional)
    items: string
    values: ["fsm_diagnose_fix", "fsm_design_decide", ...]
    example: ["fsm_diagnose_fix"]
}
```

### FSMRouterResponse

```
{
  "trace_id": string
  
  "route": {
    "selected_fsm_id": string - enum of 10 FSM types
    "selected_fsm_name": string - human-readable name
    "confidence": number [0, 1]
    "reasoning": string - explanation of decision
    "alternative_fsms": [
      {
        "fsm_id": string,
        "fsm_name": string,
        "confidence": number [0, 1]
      }
    ]
  }
  
  "routing_ms": integer - latency in milliseconds
  "router_version": string - "1.0.0"
  "computed_at": string - ISO 8601 timestamp
}
```

---

## Integration Examples

### Python Client (Requests Library)

```python
import requests

class FSMRouterClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def route(self, trace_id: str, problem_text: str) -> dict:
        """Route a single problem."""
        response = requests.post(
            f"{self.base_url}/v1/route",
            json={
                "trace_id": trace_id,
                "problem_text": problem_text
            }
        )
        response.raise_for_status()
        return response.json()
    
    def route_batch(self, traces: list) -> dict:
        """Route multiple problems."""
        response = requests.post(
            f"{self.base_url}/v1/route/batch",
            json={"traces": traces, "parallel": True}
        )
        response.raise_for_status()
        return response.json()
    
    def get_config(self) -> dict:
        """Get current configuration."""
        response = requests.get(f"{self.base_url}/v1/config")
        response.raise_for_status()
        return response.json()
    
    def update_config(self, updates: dict) -> dict:
        """Update configuration."""
        response = requests.put(
            f"{self.base_url}/v1/config",
            json=updates
        )
        response.raise_for_status()
        return response.json()

# Usage
client = FSMRouterClient()
response = client.route(
    trace_id="trace-001-abcd",
    problem_text="Why does the database timeout?"
)
print(response["route"]["selected_fsm_id"])  # fsm_diagnose_fix
```

### Integration with Phase 1 Ingestion

```python
# In grimoire_ingestion.py
def process_trace_with_fsm_routing(trace: Trace):
    """Add FSM routing to trace processing."""
    
    # Call FSM Router
    router_response = fsm_router_client.route(
        trace_id=trace.trace_id,
        problem_text=trace.problem
    )
    
    # Attach FSM to trace
    trace.fsm_type = router_response["route"]["selected_fsm_id"]
    trace.fsm_confidence = router_response["route"]["confidence"]
    
    # Store in Neo4j
    neo4j.create_trace_with_fsm(trace)
    
    return trace
```

### Integration with Phase 2.3 Guards

```python
# In grimoire_fsm.guard_orchestrator
def check_transition_with_fsm_context(
    step: Step,
    fsm_router_client
) -> GuardDecision:
    """Check transition using FSM type context."""
    
    # Get FSM for step's trace
    if not step.fsm_type:
        routing = fsm_router_client.route(
            trace_id=step.trace_id,
            problem_text=step.text
        )
        fsm_type = routing["route"]["selected_fsm_id"]
    else:
        fsm_type = step.fsm_type
    
    # Apply FSM-specific guards
    if fsm_type == "fsm_diagnose_fix":
        # Diagnose problems: require evidence/analysis before jumping to solutions
        if step.role == "execute" and not step.has_analysis:
            return GuardDecision(
                allowed=False,
                reason="Diagnose FSM: must complete analysis before execution"
            )
    
    elif fsm_type == "fsm_design_decide":
        # Design problems: require exploration before decision
        if step.role == "execute" and step.step_number < 3:
            return GuardDecision(
                allowed=False,
                reason="Design FSM: insufficient exploration before decision"
            )
    
    return GuardDecision(allowed=True)
```

---

## Performance Targets

| Scenario | Latency | SLA |
|----------|---------|-----|
| Single route | P50: 40ms, P99: 100ms | < 100ms |
| Batch 100 | P50: 38ms/trace, P99: 95ms/trace | < 10s total |
| Batch 1000 | P50: 38ms/trace, P99: 95ms/trace | < 100s total |

---

## Rate Limiting

```
X-RateLimit-Limit: 10000
X-RateLimit-Remaining: 9999
X-RateLimit-Reset: 1705317045

Per minute: 10,000 requests
Per second: ~166 requests
Burst: up to 500 requests
```

---

## Versioning

**Current**: v1.0 (keyword-based routing)  
**Planned**: v2.0 (LLM-based routing for higher accuracy)

**Migration Path**:
- v1.0 API stays stable
- v2.0 uses same `/v1/route` endpoint
- Only backend scorer implementation changes
- Clients notice no API change, only improved accuracy

---

## See Also

- [spec.md](../spec.md) — User stories
- [data-model.md](../data-model.md) — Pydantic v2 models
- [plan.md](../plan.md) — Implementation roadmap
- [quickstart.md](../quickstart.md) — Developer quick reference
