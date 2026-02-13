# Integration Test Strategy

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: Phases 1-3 Cross-Feature Integration  
**Goal**: Ensure reliable data flow across all 8 features

---

## Overview

This document defines a comprehensive integration testing strategy for Grimoire's multi-phase architecture. Integration tests verify that:

1. Data flows correctly from Phase 1 → Phase 2 → Phase 3
2. APIs are compatible across feature boundaries
3. Database schema migrations work correctly
4. Event bus messages are processed reliably

---

## Test Pyramid

```text
                    ┌─────────────────┐
                    │   E2E Tests     │  (5%)
                    │  (User Journeys)│
                    └────────┬────────┘
                             │
           ┌─────────────────┼─────────────────┐
           │                 │                 │
    ┌──────▼──────┐   ┌──────▼──────┐   ┌──────▼──────┐
    │ Integration │   │  Integration│   │  Integration│  (15%)
    │  Phase 1-2  │   │  Phase 2-3  │   │  Phase 1-3  │
    └─────────────┘   └─────────────┘   └─────────────┘
                             │
                    ┌────────▼────────┐
                    │  Contract Tests │  (20%)
                    │  (API Compatibility)
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │   Unit Tests    │  (60%)
                    │ (Individual Features)
                    └─────────────────┘
```

---

## Integration Test Categories

### Category 1: Phase 1 → Phase 2 Integration

**Test**: Full ingestion → classification pipeline

```python
# tests/integration/test_phase1_to_phase2.py

@pytest.mark.integration
class TestPhase1ToPhase2Flow:
    """Test data flow from ingestion through classification."""

    def test_ingested_trace_gets_classified(self):
        """E2E: Ingest trace → Classify danger → Store scores."""
        # Phase 1: Ingest
        trace_bundle = load_test_trace("debug_timeout.json")
        response = ingest_api.post("/v1/ingest", json={
            "dataset_id": "test-dataset",
            "traces": [trace_bundle]
        })
        trace_id = response.json()["trace_ids"][0]

        # Wait for async processing
        wait_for_neo4j(trace_id)

        # Phase 2.1: Classify danger
        step = get_first_step(trace_id)
        classify_response = danger_api.post("/v1/classify", json={
            "trace_id": trace_id,
            "text_to_classify": step["content"],
            "context_role": "problem"
        })

        # Verify scores stored in Neo4j
        danger_scores = classify_response.json()["danger_scores"]
        stored_scores = neo4j_query(f"""
            MATCH (s:Step {{trace_id: '{trace_id}'}})
            RETURN s.danger_ambiguity, s.danger_adversarial
        """)

        assert stored_scores["s.danger_ambiguity"] == danger_scores["ambiguity"]

    def test_fsm_routing_after_ingestion(self):
        """E2E: Ingest → Route to FSM → Store classification."""
        # Phase 1: Ingest
        trace_id = ingest_test_trace("design_problem.json")

        # Phase 2.2: Route
        route_response = fsm_api.post("/v1/route", json={
            "trace_id": trace_id,
            "problem_text": "Design a new caching strategy"
        })

        fsm_type = route_response.json()["route"]["selected_fsm_id"]

        # Verify stored
        stored_fsm = neo4j_query(f"""
            MATCH (s:Step {{trace_id: '{trace_id}', step_number: 0}})
            RETURN s.fsm_type, s.fsm_confidence
        """)

        assert stored_fsm["s.fsm_type"] == fsm_type
        assert stored_fsm["s.fsm_confidence"] > 0.5
```

### Category 2: Phase 2 → Phase 3 Integration

**Test**: Classification → Pattern extraction/ranking

```python
# tests/integration/test_phase2_to_phase3.py

@pytest.mark.integration
class TestPhase2ToPhase3Flow:
    """Test data flow from classification through pattern learning."""

    def test_danger_scores_influence_pattern_ranking(self):
        """Phase 2.1 danger scores → Phase 3.2 ranking."""
        # Setup: Create pattern with danger context
        pattern_id = create_test_pattern("high_risk_pattern")

        # Add danger scores (simulating Phase 2.1 output)
        neo4j_query(f"""
            MATCH (p:Pattern {{pattern_id: '{pattern_id}'}})
            MATCH (p)-[:MATCHES_TRACE]->(t:Trace)-[:CONTAINS]->(s:Step)
            SET s.danger_ambiguity = 0.8,
                s.danger_adversarial = 0.2
        """)

        # Phase 3.2: Rank with danger context
        rank_response = ranking_api.post("/v1/rank", json={
            "pattern_ids": [pattern_id],
            "context": {
                "danger_scores": [{
                    "pattern_id": pattern_id,
                    "danger_types": ["HIGH"],
                    "severity": 0.8
                }]
            }
        })

        # Verify safety score reflects danger
        ranked = rank_response.json()["ranked_patterns"][0]
        assert ranked["safety_score"] < 0.5  # Low safety due to high ambiguity
        assert ranked["safety_level"] == "HIGH"

    def test_fsm_type_filters_patterns(self):
        """Phase 2.2 FSM → Phase 3.1 pattern extraction."""
        # Setup: Traces with different FSM types
        debug_traces = create_traces_with_fsm("fsm_diagnose_fix", count=10)
        design_traces = create_traces_with_fsm("fsm_design_decide", count=10)

        # Phase 3.1: Extract patterns by FSM type
        extract_response = extraction_api.post("/v1/extract", json={
            "fsm_type": "fsm_diagnose_fix",
            "min_support": 2
        })

        patterns = extract_response.json()["patterns"]

        # Verify only debug patterns extracted
        for pattern in patterns:
            assert "fsm_diagnose_fix" in pattern["fsm_types"]
            assert "fsm_design_decide" not in pattern["fsm_types"]
```

### Category 3: Phase 1 → Phase 3 Integration

**Test**: Full pipeline from ingestion to optimization

```python
# tests/integration/test_full_pipeline.py

@pytest.mark.slow
class TestFullPipeline:
    """End-to-end tests covering all phases."""

    def test_complete_reasoning_pipeline(self):
        """Full flow: Ingest → Classify → Route → Extract → Rank → Feedback."""
        # Phase 1: Ingest
        trace_id = ingest_test_trace("production_debug.json")

        # Phase 2: Classify + Route
        danger_response = danger_api.post("/v1/classify", json={
            "trace_id": trace_id,
            "text_to_classify": "Debug production timeout",
            "context_role": "problem"
        })

        fsm_response = fsm_api.post("/v1/route", json={
            "trace_id": trace_id,
            "problem_text": "Debug production timeout"
        })

        # Phase 3.1: Extract patterns
        extraction_api.post("/v1/extract", json={
            "trace_ids": [trace_id],
            "min_confidence": 0.7
        })

        # Get extracted pattern
        pattern = neo4j_query("""
            MATCH (p:Pattern)
            WHERE p.num_matching_traces >= 1
            RETURN p.pattern_id as id
            LIMIT 1
        """)

        # Phase 3.2: Rank pattern
        ranking_api.post("/v1/rank", json={
            "pattern_ids": [pattern["id"]],
            "context": {
                "current_fsm_type": fsm_response.json()["route"]["selected_fsm_id"],
                "danger_scores": [danger_response.json()["danger_scores"]]
            }
        })

        # Phase 3.3: Submit feedback
        feedback_api.post("/v1/feedback", json={
            "pattern_id": pattern["id"],
            "trace_id": trace_id,
            "success": True,
            "outcome_quality": 9,
            "user_satisfaction": 5,
            "latency_ms": 150.0
        })

        # Verify feedback stored
        stored_feedback = neo4j_query(f"""
            MATCH (p:Pattern {{pattern_id: '{pattern["id"]}'}})-[:HAS_FEEDBACK]->(f:FeedbackEvent)
            RETURN f.success, f.outcome_quality
        """)

        assert stored_feedback["f.success"] == True
        assert stored_feedback["f.outcome_quality"] == 9
```

### Category 4: Event Bus Integration

**Test**: Async feedback flow

```python
# tests/integration/test_event_bus.py

@pytest.mark.integration
class TestEventBusFlow:
    """Test Redis Streams event flow."""

    def test_feedback_event_published_and_consumed(self):
        """Feedback produced → Event bus → Processed."""
        import redis

        r = redis.Redis()

        # Clear test stream
        r.delete("grimoire:feedback:events")

        # Produce feedback
        feedback_api.post("/v1/feedback", json={
            "pattern_id": "test-pattern-001",
            "trace_id": "test-trace-001",
            "success": True,
            "latency_ms": 100.0
        })

        # Wait for async processing
        time.sleep(2)

        # Verify event in stream
        events = r.xread({"grimoire:feedback:events": "0"}, count=10)

        assert len(events) > 0
        stream_name, messages = events[0]
        assert stream_name == b"grimoire:feedback:events"

        # Verify consumer group processed
        pending = r.xpending("grimoire:feedback:events", "feedback-processors")
        assert pending["pending"] == 0  # All processed

    def test_drift_alert_triggers_re_ranking(self):
        """Drift detection → Alert → Re-ranking triggered."""
        # Create pattern with declining performance
        pattern_id = "drift-test-pattern"

        # Submit many negative feedback events
        for i in range(100):
            feedback_api.post("/v1/feedback", json={
                "pattern_id": pattern_id,
                "trace_id": f"trace-{i}",
                "success": i < 20,  # First 20 succeed, rest fail
                "outcome_quality": 2 if i >= 20 else 8,
                "timestamp": (datetime.now() - timedelta(days=i//10)).isoformat()
            })

        # Wait for drift detection
        time.sleep(5)

        # Verify drift alert created
        drift_alert = neo4j_query(f"""
            MATCH (p:Pattern {{pattern_id: '{pattern_id}'}})-[:HAS_DRIFT_ALERT]->(d:ConceptDriftAlert)
            RETURN d.metric, d.drift_percentage
            ORDER BY d.detection_timestamp DESC
            LIMIT 1
        """)

        assert drift_alert["d.metric"] == "success_rate"
        assert drift_alert["d.drift_percentage"] > 15.0
```

### Category 5: Schema Migration Integration

**Test**: Database migrations work across versions

```python
# tests/integration/test_schema_migrations.py

@pytest.mark.integration
@pytest.mark.slow
class TestSchemaMigrations:
    """Test Neo4j schema evolution."""

    def test_migration_v1_0_to_v1_1(self):
        """Test Phase 2.1 migration adds danger scores."""
        # Start with clean v1.0 schema
        run_migration("v1.0.0", clean=True)

        # Add test data
        neo4j_query("""
            CREATE (s:Step {step_id: 'test-step', content: 'test'})
        """)

        # Verify no danger scores
        before = neo4j_query("""
            MATCH (s:Step {step_id: 'test-step'})
            RETURN s.danger_ambiguity IS NULL as is_null
        """)
        assert before["is_null"] == True

        # Run migration
        run_migration("v1.1.0")

        # Verify danger scores added with defaults
        after = neo4j_query("""
            MATCH (s:Step {step_id: 'test-step'})
            RETURN s.danger_ambiguity, s.danger_adversarial
        """)
        assert after["s.danger_ambiguity"] == 0.0
        assert after["s.danger_adversarial"] == 0.0

        # Verify schema version updated
        version = get_schema_version()
        assert version == "1.1.0"

    def test_rollback_preserves_data(self):
        """Test migration rollback preserves existing data."""
        # Migrate to v2.0
        run_migration("v2.0.0")

        # Add pattern data
        neo4j_query("""
            CREATE (p:Pattern {
                pattern_id: 'test-pattern',
                name: 'Test Pattern',
                success_rate: 0.85
            })
        """)

        # Rollback to v1.3
        run_rollback("v1.3.0")

        # Verify Pattern nodes removed but Step nodes intact
        patterns = neo4j_query("MATCH (p:Pattern) RETURN count(p) as count")
        steps = neo4j_query("MATCH (s:Step) RETURN count(s) as count")

        assert patterns["count"] == 0
        # Steps should still exist from prior tests
```

---

## Test Data Fixtures

```python
# tests/integration/conftest.py

import pytest
import json
from pathlib import Path

@pytest.fixture
def sample_traces():
    """Load sample traces for testing."""
    traces_dir = Path(__file__).parent / "fixtures" / "traces"
    traces = {}
    for trace_file in traces_dir.glob("*.json"):
        with open(trace_file) as f:
            traces[trace_file.stem] = json.load(f)
    return traces

@pytest.fixture
def neo4j_clean():
    """Clean Neo4j before test."""
    # Delete test data
    neo4j_query("""
        MATCH (n)
        WHERE n.trace_id STARTS WITH 'test-'
           OR n.pattern_id STARTS WITH 'test-'
        DETACH DELETE n
    """)
    yield
    # Cleanup after test

@pytest.fixture
def api_clients():
    """Provide API clients for all services."""
    return {
        "ingest": TestClient(ingest_app),
        "danger": TestClient(danger_app),
        "fsm": TestClient(fsm_app),
        "guards": TestClient(guards_app),
        "extraction": TestClient(extraction_app),
        "ranking": TestClient(ranking_app),
        "feedback": TestClient(feedback_app),
    }
```

---

## Test Environment Matrix

| Environment | Neo4j | Qdrant | Redis | Purpose |
|-------------|-------|--------|-------|---------|
| Unit Tests | In-memory / mock | Mock | Mock | Fast, isolated |
| Integration | Docker (single) | Docker | Docker | Feature pairs |
| E2E | Docker cluster | Docker | Docker | Full pipeline |
| Staging | Cloud instance | Cloud | Cloud | Pre-prod validation |
| Production | Production cluster | Production | Production | Smoke tests |

---

## CI/CD Pipeline

```yaml
# .github/workflows/integration-tests.yml
name: Integration Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  integration-tests:
    runs-on: ubuntu-latest

    services:
      neo4j:
        image: neo4j:5.14.0
        env:
          NEO4J_AUTH: neo4j/testpassword
        ports:
          - 7687:7687
          - 7474:7474

      qdrant:
        image: qdrant/qdrant:v1.7.0
        ports:
          - 6333:6333

      redis:
        image: redis:7-alpine
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-test.txt

      - name: Run Phase 1-2 Integration Tests
        run: |
          pytest tests/integration/test_phase1_to_phase2.py -v --cov

      - name: Run Phase 2-3 Integration Tests
        run: |
          pytest tests/integration/test_phase2_to_phase3.py -v --cov

      - name: Run Full Pipeline Tests
        run: |
          pytest tests/integration/test_full_pipeline.py -v --cov --timeout=300

      - name: Run Event Bus Tests
        run: |
          pytest tests/integration/test_event_bus.py -v --cov

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Test Isolation Strategy

```python
# tests/integration/utils/isolation.py

import uuid
from contextlib import contextmanager

@contextmanager
def isolated_test_scope(prefix: str = "test"):
    """Create isolated scope for integration test."""
    scope_id = f"{prefix}-{uuid.uuid4().hex[:8]}"

    try:
        yield scope_id
    finally:
        # Cleanup all test data with this scope
        cleanup_queries = [
            f"MATCH (n) WHERE n.trace_id STARTS WITH '{scope_id}' DETACH DELETE n",
            f"MATCH (n) WHERE n.pattern_id STARTS WITH '{scope_id}' DETACH DELETE n",
            f"MATCH (n) WHERE n.experiment_id STARTS WITH '{scope_id}' DETACH DELETE n",
        ]
        for query in cleanup_queries:
            neo4j_query(query)
```

---

## Success Criteria

| Test Category | Target | Current |
|---------------|--------|---------|
| Phase 1-2 Integration | 15 tests passing | 0 |
| Phase 2-3 Integration | 15 tests passing | 0 |
| Full Pipeline | 5 tests passing | 0 |
| Event Bus | 10 tests passing | 0 |
| Schema Migration | 5 tests passing | 0 |
| **Total** | **50 tests** | **0** |

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | AI Assistant | Initial integration test strategy |
