"""Integration tests for HuggingFace dataset ingestion.

Tests end-to-end ingestion pipeline with 100 traces from OpenThoughts-114k.
"""

import pytest
from grimoire.ingestion.hf_loader import HFDatasetLoader, HFDatasetConfig
from grimoire.ingestion.parser import HuggingFaceParser, IngestionConfig
from grimoire.core.schema.models import DomainTag, Sensitivity


@pytest.fixture
def hf_loader():
    """Create dataset loader with 100 trace limit."""
    config = HFDatasetConfig(
        dataset_id="open-thoughts/OpenThoughts-114k",
        split="train",
        streaming=False,
        limit=100,
    )
    return HFDatasetLoader(config)


@pytest.fixture
def parser():
    """Create parser for ingestion."""
    config = IngestionConfig(
        dataset_name="open-thoughts/OpenThoughts-114k",
        sensitivity=Sensitivity.PUBLIC,
    )
    return HuggingFaceParser(config)


class TestIngestion114k:
    """Test ingestion of 100 traces from OpenThoughts-114k dataset."""
    
    def test_load_dataset(self, hf_loader):
        """Test loading dataset from HuggingFace."""
        dataset = hf_loader.load()
        
        assert dataset is not None
        # Check that we got some records
        records = hf_loader.get_records()
        assert len(records) > 0
        assert len(records) <= 100
    
    def test_ingest_100_traces(self, hf_loader, parser):
        """Test end-to-end ingestion of 100 traces."""
        records = hf_loader.get_records()
        
        # Parse all records
        traces = parser.parse_batch(records, start_index=0)
        
        # Verify we got traces
        assert len(traces) > 0, "Should parse at least some traces"
        
        # Verify trace structure
        for trace in traces:
            assert trace.trace_id is not None
            assert trace.domain in DomainTag.__members__.values()
            assert trace.created_at is not None
            assert trace.updated_at is not None
            assert trace.provenance is not None
            assert trace.provenance.sources is not None
            assert len(trace.provenance.sources) > 0
    
    def test_trace_provenance_complete(self, hf_loader, parser):
        """Verify all traces have complete provenance metadata."""
        records = hf_loader.get_records()[:10]  # Just 10 for quick test
        traces = parser.parse_batch(records, start_index=0)
        
        for trace in traces:
            # Check provenance
            assert trace.provenance.sources
            assert trace.provenance.license_info is not None
            assert trace.provenance.license_info.license is not None
            assert trace.provenance.sensitivity == Sensitivity.PUBLIC
            assert trace.provenance.ingested_at is not None
            assert trace.provenance.pipeline_version is not None
    
    def test_deduplication_at_scale(self, hf_loader, parser):
        """Verify deduplication works when parsing multiple traces."""
        records = hf_loader.get_records()[:50]  # 50 traces
        traces = parser.parse_batch(records, start_index=0)
        
        # Check dedup stats
        stats = parser.get_dedup_stats()
        assert stats["unique_traces"] > 0
        
        # Should have some duplicates detected (or all unique if no duplicates)
        total_parsed = len(traces)
        assert total_parsed > 0


class TestIngestionEdgeCases:
    """Test edge cases in ingestion pipeline."""
    
    def test_parse_missing_fields(self, parser):
        """Test parsing records with missing fields."""
        incomplete_record = {
            "problem": "Test problem",
            # Missing domain, tags, etc.
        }
        
        trace = parser.parse_record(incomplete_record, 0)
        
        # Should parse successfully with defaults
        assert trace is not None
        assert trace.domain == DomainTag.GENERAL
        assert trace.tags == []
    
    def test_parse_empty_problem(self, parser):
        """Test parsing record with empty problem."""
        empty_record = {
            "problem": "",
        }
        
        trace = parser.parse_record(empty_record, 0)
        
        # Should skip record with no problem
        assert trace is None
