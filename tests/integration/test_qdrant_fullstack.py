"""Integration tests for Qdrant storage.

Tests end-to-end Qdrant embedding persistence and search.
"""

import pytest
from grimoire.storage.qdrant_client import QdrantStorage, QdrantStorageException


@pytest.fixture
def qdrant_storage():
    """Create Qdrant storage instance (local test instance).
    
    Note: Requires Qdrant running on localhost:6333
    """
    try:
        storage = QdrantStorage(url="http://localhost:6333", embedding_dim=384)
        storage.create_collections()
        yield storage
    except Exception as e:
        pytest.skip(f"Qdrant not available: {e}")


class TestQdrantEmbeddings:
    """Test Qdrant embedding storage and search."""
    
    def test_insert_step_embedding(self, qdrant_storage):
        """Test inserting a step embedding."""
        step_id = "test-step-001"
        embedding = [0.1] * 384  # Mock 384-dim vector
        payload = {
            "trace_id": "trace-001",
            "domain": "software",
            "role": "PLAN",
        }
        
        result = qdrant_storage.insert_step_embedding(step_id, embedding, payload)
        assert result is True
    
    def test_batch_insert_embeddings(self, qdrant_storage):
        """Test batch inserting embeddings."""
        embeddings = [
            (
                f"step-{i:03d}",
                [0.1 * (i + 1)] * 384,
                {"trace_id": f"trace-{i}", "domain": "software"},
            )
            for i in range(5)
        ]
        
        inserted = qdrant_storage.batch_insert_embeddings(embeddings)
        assert inserted == 5
    
    def test_search_similar_steps(self, qdrant_storage):
        """Test semantic search."""
        # Insert some test embeddings
        embeddings = [
            ("step-1", [0.1] * 384, {"trace_id": "trace-1", "domain": "software"}),
            ("step-2", [0.1] * 384, {"trace_id": "trace-2", "domain": "ml"}),
            ("step-3", [0.2] * 384, {"trace_id": "trace-3", "domain": "software"}),
        ]
        qdrant_storage.batch_insert_embeddings(embeddings)
        
        # Search with similar vector
        query = [0.1] * 384
        results = qdrant_storage.search_similar_steps(query, limit=2)
        
        # Should return results
        assert len(results) > 0
        assert all("score" in r and "payload" in r for r in results)
    
    def test_search_with_filter(self, qdrant_storage):
        """Test filtered search."""
        # Insert test embeddings
        embeddings = [
            ("step-1", [0.1] * 384, {"trace_id": "trace-1", "domain": "software"}),
            ("step-2", [0.1] * 384, {"trace_id": "trace-2", "domain": "ml"}),
            ("step-3", [0.1] * 384, {"trace_id": "trace-3", "domain": "software"}),
        ]
        qdrant_storage.batch_insert_embeddings(embeddings)
        
        # Search with filter for software domain
        query = [0.1] * 384
        results = qdrant_storage.search_with_filter(
            query,
            filter_dict={"domain": "software"},
            limit=10,
        )
        
        # All results should have software domain
        if results:
            assert all(r["payload"]["domain"] == "software" for r in results)
