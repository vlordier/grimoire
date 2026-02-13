"""Integration tests for Neo4j storage.

Tests end-to-end Neo4j persistence with constraints and transactions.
"""

import pytest
from datetime import datetime, timezone
from grimoire.core.schema.models import (
    Trace,
    Step,
    StepRole,
    DomainTag,
    Sensitivity,
    LicenseType,
    Provenance,
    LicenseInfo,
    SourceRef,
    SourceType,
)
from grimoire.storage.neo4j import Neo4jStorage, Neo4jStorageException


@pytest.fixture
def neo4j_storage():
    """Create Neo4j storage instance (local test instance).
    
    Note: Requires Neo4j running on localhost:7687
    """
    try:
        storage = Neo4jStorage(
            uri="bolt://localhost:7687",
            auth=("neo4j", "password"),
        )
        # Setup
        storage.create_constraints()
        storage.create_indexes()
        yield storage
        # Teardown
        storage.close()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")


def create_sample_trace() -> Trace:
    """Create a sample Trace with provenance."""
    now = datetime.now(timezone.utc)
    
    source = SourceRef(
        source_type=SourceType.HUGGINGFACE,
        source_id="open-thoughts/OpenThoughts-114k",
        record_id="test-001",
    )
    
    license_info = LicenseInfo(license=LicenseType.APACHE_2)
    
    provenance = Provenance(
        sources=[source],
        license_info=license_info,
        sensitivity=Sensitivity.PUBLIC,
        ingested_at=now,
        pipeline_version="0.1.0",
        schema_version="v1",
    )
    
    return Trace(
        trace_id="test-trace-001",
        title="Test Trace",
        domain=DomainTag.SOFTWARE,
        tags=["test", "python"],
        problem="How to solve test problem?",
        created_at=now,
        updated_at=now,
        n_steps=2,
        provenance=provenance,
    )


def create_sample_step(trace_id: str, index: int) -> Step:
    """Create a sample Step."""
    now = datetime.now(timezone.utc)
    
    return Step(
        step_id=f"step-{index:03d}",
        trace_id=trace_id,
        index=index,
        actor="assistant",
        role=StepRole.PLAN,
        text=f"Step {index}: Test step content",
        created_at=now,
    )


class TestNeo4jPersistence:
    """Test Neo4j persistence operations."""
    
    def test_insert_trace(self, neo4j_storage):
        """Test inserting a trace."""
        trace = create_sample_trace()
        
        result = neo4j_storage.insert_trace(trace)
        assert result is True
        
        # Retrieve and verify
        retrieved = neo4j_storage.get_trace(trace.trace_id)
        assert retrieved is not None
        assert retrieved["trace_id"] == trace.trace_id
        assert retrieved["title"] == trace.title
    
    def test_insert_step(self, neo4j_storage):
        """Test inserting a step."""
        # First insert trace
        trace = create_sample_trace()
        neo4j_storage.insert_trace(trace)
        
        # Insert step
        step = create_sample_step(trace.trace_id, 0)
        result = neo4j_storage.insert_step(step)
        assert result is True
    
    def test_get_trace_steps(self, neo4j_storage):
        """Test retrieving steps for a trace."""
        trace = create_sample_trace()
        neo4j_storage.insert_trace(trace)
        
        # Insert multiple steps
        steps = [create_sample_step(trace.trace_id, i) for i in range(3)]
        for step in steps:
            neo4j_storage.insert_step(step)
        
        # Retrieve
        retrieved_steps = neo4j_storage.get_trace_steps(trace.trace_id)
        assert len(retrieved_steps) == 3
        
        # Verify order
        for i, step in enumerate(retrieved_steps):
            assert step["index"] == i
    
    def test_batch_insert_traces(self, neo4j_storage):
        """Test batch inserting multiple traces."""
        traces = [
            create_sample_trace(),
            create_sample_trace(),
            create_sample_trace(),
        ]
        # Make unique IDs
        for i, t in enumerate(traces):
            t.trace_id = f"batch-trace-{i:03d}"
        
        inserted = neo4j_storage.batch_insert_traces(traces)
        assert inserted == 3
