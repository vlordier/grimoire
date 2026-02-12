# Danger Classifier API Contract

**Version**: 1.0  
**Status**: Spec Phase  
**Last Updated**: Phase 2.1 Planning

---

## Overview

**Base Interface**: `DangerClassifier`

The Danger Classifier analyzes reasoning traces for 4 danger types (ambiguity, adversarial intent, irreversibility, institutional risk) and produces danger scores [0, 1] for each. Consumers (FSM, Guards, Retrieval) use these scores to block/warn/escalate decisions.

**Integration**:
- **Upstream (Phase 1)**: Receives `TraceBundle` + text to classify
- **Downstream (Phase 2.3)**: Scores consumed by `GuardOrchestrator` + `FSMRouter`
- **Storage**: Danger scores on Neo4j Step nodes + Qdrant step_windows payloads

---

## API Endpoints

### 1. Classify Single Trace

```
POST /v1/classify
```

**Request**

```python
DangerClassifierRequest(
    trace_id: str,              # "trace-001-abcd"
    text_to_classify: str,      # Problem statement or step text
    context_role: str,          # "goal" | "problem" | "observation" | "plan" | "execute"
    prior_scores?: DangerScores  # Optional: scores from parent step (for refinement)
)
```

**Response**

```python
DangerClassifierResponse(
    trace_id: str,
    danger_scores: DangerScores,  # [ambiguity, adversarial, irrev, inst] ∈ [0,1]
    evidence: DangerEvidence,
    classifier_version: str,      # "1.0.0"
    computed_at: datetime,
    processing_ms: int
)
```

**Example**

```bash
curl -X POST http://localhost:8000/v1/classify \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "trace-001-abcd",
    "text_to_classify": "Delete all cache entries to speed up the system",
    "context_role": "execute",
    "prior_scores": null
  }'
```

**Response**

```json
{
  "trace_id": "trace-001-abcd",
  "danger_scores": {
    "trace_id": "trace-001-abcd",
    "danger_ambiguity": 0.2,
    "danger_adversarial": 0.1,
    "danger_irreversibility": 0.9,
    "danger_institutional": 0.3,
    "evidence": {
      "ambiguity_spans": [],
      "adversarial_spans": [],
      "irreversibility_spans": [
        {
          "text_span": "Delete",
          "start_char": 0,
          "end_char": 6,
          "rule_name": "irreversibility_keywords.delete",
          "weight": 0.8
        }
      ],
      "institutional_spans": []
    },
    "computed_at": "2024-01-15T10:30:45Z",
    "classifier_version": "1.0.0",
    "confidence": 0.85
  },
  "processing_ms": 12
}
```

---

### 2. Batch Classify Traces

```
POST /v1/classify/batch
```

**Request**

```python
DangerClassifierBatchRequest(
    traces: List[DangerClassifierRequest],  # Up to 100 per batch
    parallel: bool = True
)
```

**Response**

```python
DangerClassifierBatchResponse(
    results: List[DangerClassifierResponse],
    failed: List[BatchError],
    total_ms: int
)
```

**Example**

```bash
curl -X POST http://localhost:8000/v1/classify/batch \
  -H "Content-Type: application/json" \
  -d '{
    "traces": [
      {
        "trace_id": "trace-001",
        "text_to_classify": "Maybe optimize this later",
        "context_role": "plan"
      },
      {
        "trace_id": "trace-002",
        "text_to_classify": "Deploy live now",
        "context_role": "execute"
      }
    ],
    "parallel": true
  }'
```

---

### 3. Get Classifier Config

```
GET /v1/config
```

**Response**

```python
ClassifierConfig(
    ambiguity_keywords: List[str],
    adversarial_keywords: List[str],
    irreversibility_keywords: List[str],
    institutional_keywords: List[str],
    block_threshold: float,
    warn_threshold: float,
    escalate_threshold: float,
    problem_statement_weight: float,
    observation_weight: float,
    step_based_weight: float
)
```

**Example**

```bash
curl http://localhost:8000/v1/config
```

**Response**

```json
{
  "ambiguity_keywords": ["unclear", "maybe", "probably", "assume", "guess"],
  "adversarial_keywords": ["bypass", "exploit", "attack"],
  "irreversibility_keywords": ["delete", "deploy", "commit"],
  "institutional_keywords": ["hire", "fire", "policy"],
  "block_threshold": 0.7,
  "warn_threshold": 0.5,
  "escalate_threshold": 0.6,
  "problem_statement_weight": 2.0,
  "observation_weight": 1.0,
  "step_based_weight": 1.5
}
```

---

### 4. Update Classifier Config

```
PUT /v1/config
```

**Request**

```python
ClassifierConfigUpdate(
    ambiguity_keywords?: List[str],
    block_threshold?: float,
    # ... other fields
)
```

**Response**

```python
ClassifierConfig  # Updated config
```

**Example**

```bash
curl -X PUT http://localhost:8000/v1/config \
  -H "Content-Type: application/json" \
  -d '{
    "block_threshold": 0.75,
    "ambiguity_keywords": ["unclear", "vague", "uncertain"]
  }'
```

---

### 5. Health Check

```
GET /v1/health
```

**Response**

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "classifier_ready": true,
  "neo4j_connected": true,
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
    "received": "invalid-id"
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
      "field": "text_to_classify",
      "error": "String too long (max 10000 chars)"
    }
  ]
}
```

### 500: Classifier Error

```json
{
  "error": "classifier_error",
  "message": "Classifier crashed; returning neutral scores",
  "details": {
    "error_msg": "Regex compilation failed for keyword pattern",
    "fallback_scores": {
      "danger_ambiguity": 0.0,
      "danger_adversarial": 0.0,
      "danger_irreversibility": 0.0,
      "danger_institutional": 0.0
    }
  }
}
```

---

## Client Library

### Python Client

```python
from grimoire_client import DangerClassifierClient

client = DangerClassifierClient(
    base_url="http://localhost:8000",
    api_key="your-api-key"
)

# Single classification
response = client.classify(
    trace_id="trace-001",
    text="Delete the database",
    context_role="execute"
)

# Batch classification
responses = client.classify_batch(
    traces=[
        {"trace_id": "t1", "text": "...", "context_role": "plan"},
        {"trace_id": "t2", "text": "...", "context_role": "execute"},
    ]
)

# Config management
config = client.get_config()
client.update_config(block_threshold=0.75)
```

---

## Integration Examples

### Pattern 1: Ingestion Pipeline (Phase 1)

```python
# In grimoire_ingestion.trace_processor
def process_hf_record_with_danger(record: Dict) -> Trace:
    trace = normalize_to_trace(record)
    
    # Call classifier
    danger_response = classifier_client.classify(
        trace_id=trace.trace_id,
        text_to_classify=trace.problem,
        context_role="goal"
    )
    
    # Attach to trace
    trace.initial_danger = danger_response.danger_scores
    
    # Store in Neo4j + Qdrant
    neo4j.create_trace_with_danger_scores(trace)
    qdrant.index_trace_with_danger_scores(trace)
    
    return trace
```

### Pattern 2: Guard Decision (Phase 2.3)

```python
# In grimoire_fsm.guard_orchestrator
def check_transition_guard(
    step: Step,
    proposed_role: str,
    fsm_state: FSMState
) -> GuardDecision:
    # Ensure step has danger scores
    if not step.danger_scores:
        step.danger_scores = classifier_client.classify(
            trace_id=step.trace_id,
            text_to_classify=step.text,
            context_role=step.role
        ).danger_scores
    
    # Check guards (instantiation, irreversibility, etc.)
    if proposed_role == "execute":
        if step.danger_scores.danger_ambiguity >= 0.7:
            return GuardDecision(
                allowed=False,
                decision_type="BLOCK",
                guard_name="NO_EXECUTE_AMBIGUOUS",
                reason="Ambiguity score 0.85; clarify problem first"
            )
    
    return GuardDecision(allowed=True)
```

### Pattern 3: Retrieval Filtering (Phase 3)

```python
# In grimoire_retrieval.pattern_ranker
def rank_patterns_by_safety(
    candidate_patterns: List[Pattern],
    current_trace: Trace
) -> List[Pattern]:
    # Get danger scores for current trace
    current_danger = classifier_client.classify(
        trace_id=current_trace.trace_id,
        text_to_classify=current_trace.problem
    ).danger_scores
    
    # Filter: don't recommend patterns that amplify danger
    safe_patterns = []
    for pattern in candidate_patterns:
        pattern_danger = getattr(pattern, "danger_scores", None)
        
        if pattern_danger is None:
            continue  # Skip patterns without danger info
        
        # Don't recommend adversarial patterns if current trace is already adversarial
        if current_danger.danger_adversarial > 0.5 and pattern_danger.danger_adversarial > 0.5:
            continue
        
        safe_patterns.append(pattern)
    
    return safe_patterns
```

---

## Data Model Reference

### DangerClassifierRequest

```python
{
    "trace_id": "trace-001-abcd",
    "text_to_classify": "string (max 10000 chars)",
    "context_role": "goal|problem|observation|plan|execute",
    "prior_scores": {  # Optional
        "trace_id": "string",
        "danger_ambiguity": 0.2,
        "danger_adversarial": 0.1,
        "danger_irreversibility": 0.8,
        "danger_institutional": 0.3
    }
}
```

### DangerScores

```python
{
    "trace_id": "string",
    "danger_ambiguity": 0.0,        # [0, 1]
    "danger_adversarial": 0.0,     # [0, 1]
    "danger_irreversibility": 0.0, # [0, 1]
    "danger_institutional": 0.0,   # [0, 1]
    "evidence": {
        "ambiguity_spans": [
            {
                "text_span": "string",
                "start_char": 0,
                "end_char": 5,
                "rule_name": "string",
                "weight": 0.5
            }
        ],
        "adversarial_spans": [],
        "irreversibility_spans": [],
        "institutional_spans": []
    },
    "computed_at": "2024-01-15T10:30:45Z",
    "classifier_version": "1.0.0",
    "confidence": 0.85
}
```

---

## Performance SLA

| Metric | Target | Notes |
|--------|--------|-------|
| P50 Latency | < 50ms | Single classification |
| P99 Latency | < 200ms | Single classification |
| Batch Throughput | > 1000 traces/sec | 100-trace batch |
| Error Rate | < 0.1% | Skips only on crash (returns neutral) |
| Uptime | 99.9% | During business hours |

---

## Versioning

**Current**: v1.0 (rules-based keyword detection)  
**Planned**: v2.0 (LLM-based scoring for higher accuracy)

**Migration Path**:
- v1.0 API stays same
- v1.1 adds `classifier_version` to response
- v2.0 changes `computing_ms` due to LLM latency (~500ms)

---

## Security

### Authentication

All requests require API key header:

```bash
curl -H "Authorization: Bearer $GRIMOIRE_API_KEY" http://localhost:8000/v1/classify
```

### Input Validation

- `text_to_classify`: Max 10,000 chars, UTF-8 only
- `trace_id`: UUID format or `trace-NNN-XXXX`
- `context_role`: Whitelist: goal, problem, observation, plan, execute

### Rate Limiting

- Per API key: 10,000 requests/min
- Batch endpoint: 100,000 traces/min
- Per IP: 1,000 requests/min (unauthenticated)

---

## Testing Contracts

### Test Case 1: Irreversibility Detection

```python
def test_irreversibility_high_score():
    response = client.classify(
        trace_id="test-001",
        text_to_classify="Delete all user data from production",
        context_role="execute"
    )
    assert response.danger_scores.danger_irreversibility >= 0.7
    assert len(response.danger_scores.evidence.irreversibility_spans) > 0
```

### Test Case 2: Guard Blocking

```python
def test_execute_with_high_irreversibility_blocked():
    step = Step(
        step_id="step-001",
        role="execute",
        text="Deploy this change immediately",
        danger_scores=DangerScores(
            danger_irreversibility=0.95
        )
    )
    
    guard = GuardOrchestrator()
    decision = guard.check_transition(
        step=step,
        proposed_role="execute"
    )
    
    assert decision.allowed == False
    assert "irreversibility" in decision.reason.lower()
```

### Test Case 3: Batch Processing

```python
def test_batch_classify():
    response = client.classify_batch(
        traces=[
            {"trace_id": f"t{i}", "text": f"Task {i}", "context_role": "plan"}
            for i in range(50)
        ]
    )
    
    assert len(response.results) == 50
    assert response.total_ms < 500  # < 10ms per trace on average
```

---

## Implementation Notes

**Classifier Backend**:
- Keyword lists maintained in `config/classifier_config.yaml`
- Regex compiled at startup for performance
- Scores computed using weighted keyword matching + position boost
- Empty input returns neutral scores [0, 0, 0, 0]

**Storage Integration**:
- Danger scores persisted on Step nodes in Neo4j
- Also indexed in Qdrant payload (for vector-based retrieval)
- Scores immutable after Step creation

**Upgrade Path**:
- v1.0: Rules-based (this implementation)
- v2.0: LLM-based (Phase 2.1+, ~2 week effort)
  - Pluggable Scorer interface enables swap
  - API stays same; only `computing_ms` increases

---

## FAQ

**Q: What if a step has no text to classify?**  
A: Returns neutral scores [0, 0, 0, 0], logs warning.

**Q: Can I call classify multiple times for the same step?**  
A: Yes, but expensive. Better to store once, reuse.

**Q: What's the difference between `block_threshold` and `warn_threshold`?**  
A: Block (≥0.7) stops execution. Warn ([0.5, 0.7)) logs but allows. Configure per risk tolerance.

**Q: How do I add my own danger keywords?**  
A: Update `classifier_config.yaml`, no code change needed.

**Q: Can I use this for languages other than English?**  
A: v1.0 is English-only. May expand in v2.0.

---

## See Also

- [spec.md](../spec.md) — User stories + requirements
- [data-model.md](../data-model.md) — Pydantic v2 schema
- [plan.md](../plan.md) — Implementation design
- [guards.md](./guards-api.md) — Guard orchestration API (Phase 2.3)
