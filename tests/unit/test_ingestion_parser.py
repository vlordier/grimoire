"""Unit tests for HuggingFace dataset parser.

Tests verify:
- Trace ID generation with deduplication
- Schema validation for edge cases
- Parsing of various record formats
- Dedup detection accuracy
- Provenance metadata in results
"""

import pytest
from datetime import datetime
from grimoire.ingestion.parser import HuggingFaceParser, IngestionConfig
from grimoire.core.schema.models import (
    DomainTag,
    Sensitivity,
    LicenseType,
    SourceType,
)


@pytest.fixture
def parser():
    """Create parser instance for testing."""
    return HuggingFaceParser()


@pytest.fixture
def sample_record():
    """Sample HuggingFace dataset record."""
    return {
        "problem": "How to implement binary search in Python?",
        "domain": "SOFTWARE",
        "tags": ["algorithm", "python", "search"],
        "title": "Binary Search Implementation",
        "steps": [
            {
                "role": "GOAL",
                "text": "Implement efficient binary search",
                "actor": "user",
            },
            {
                "role": "PLAN",
                "text": "Use two pointers approach",
                "actor": "assistant",
            },
            {
                "role": "ACTION",
                "text": "def binary_search(arr, target):...",
                "actor": "assistant",
            },
        ],
        "outcome": {"success": True, "complexity": "O(log n)"},
    }


class TestTraceIDGeneration:
    """Test trace ID generation and deduplication."""
    
    def test_deterministic_trace_id(self, parser):
        """Same problem should generate same deterministic base."""
        problem = "Test problem"
        domain = "GENERAL"
        tags = ["test", "123"]
        
        trace_id_1, hash_1 = parser.generate_trace_id(problem, domain, tags)
        trace_id_2, hash_2 = parser.generate_trace_id(problem, domain, tags)
        
        # Content hash should be identical (deterministic)
        assert hash_1 == hash_2
        # Deterministic base should match (first 12 chars)
        assert trace_id_1[:12] == trace_id_2[:12]
        # ULIDs will differ (uniqueness)
        assert trace_id_1[-8:] != trace_id_2[-8:]
    
    def test_different_problems_different_hashes(self, parser):
        """Different problems should have different content hashes."""
        problem_1 = "What is machine learning?"
        problem_2 = "What is deep learning?"
        domain = "GENERAL"
        tags = ["ml"]
        
        _, hash_1 = parser.generate_trace_id(problem_1, domain, tags)
        _, hash_2 = parser.generate_trace_id(problem_2, domain, tags)
        
        assert hash_1 != hash_2


class TestRecordParsing:
    """Test parsing of individual records."""
    
    def test_parse_valid_record(self, parser, sample_record):
        """Parse a valid record successfully."""
        trace = parser.parse_record(sample_record, 0)
        
        assert trace is not None
        assert trace.trace_id is not None
        assert trace.title == "Binary Search Implementation"
        assert trace.domain == DomainTag.SOFTWARE
        assert len(trace.tags) == 3
        assert trace.n_steps == 3
        assert trace.provenance_license == LicenseType.APACHE_2_0
        assert trace.is_duplicate is False
    
    def test_parse_missing_problem(self, parser, sample_record):
        """Handle record with missing problem statement."""
        del sample_record["problem"]
        del sample_record["question"]
        sample_record["text"] = ""  # or missing entirely
        
        trace = parser.parse_record(sample_record, 0)
        assert trace is None  # Should skip record
    
    def test_parse_missing_domain_defaults_to_general(self, parser, sample_record):
        """Missing domain should default to GENERAL."""
        del sample_record["domain"]
        
        trace = parser.parse_record(sample_record, 0)
        assert trace is not None
        assert trace.domain == DomainTag.GENERAL
    
    def test_parse_tags_as_string(self, parser, sample_record):
        """Parse tags from comma-separated string."""
        sample_record["tags"] = "ai,ml,data"
        
        trace = parser.parse_record(sample_record, 0)
        assert trace is not None
        assert len(trace.tags) == 3
        assert "ai" in trace.tags
    
    def test_parse_provenance_metadata(self, parser, sample_record):
        """Verify provenance metadata is captured."""
        trace = parser.parse_record(sample_record, 42)
        
        assert trace is not None
        assert len(trace.provenance_sources) == 1
        assert trace.provenance_sources[0].source_type == SourceType.HUGGINGFACE
        assert trace.provenance_sources[0].record_id == "42"
        assert trace.provenance_ingested_at is not None
        assert trace.provenance_pipeline_version == parser.config.pipeline_version


class TestDeduplication:
    """Test deduplication detection."""
    
    def test_dedup_detection(self, parser, sample_record):
        """Second identical record should be marked as duplicate."""
        # Parse first record
        trace_1 = parser.parse_record(sample_record, 0)
        assert trace_1 is not None
        assert trace_1.is_duplicate is False
        
        # Parse identical record
        trace_2 = parser.parse_record(sample_record, 1)
        assert trace_2 is not None
        assert trace_2.is_duplicate is True
        assert trace_2.duplicate_of == trace_1.trace_id
    
    def test_dedup_stats(self, parser, sample_record):
        """Track dedup statistics."""
        parser.parse_record(sample_record, 0)
        parser.parse_record(sample_record, 1)
        
        # Modify and parse different record
        sample_record["problem"] = "Different problem"
        parser.parse_record(sample_record, 2)
        
        stats = parser.get_dedup_stats()
        assert stats["unique_traces"] == 2


class TestBatchParsing:
    """Test batch parsing functionality."""
    
    def test_parse_batch(self, parser, sample_record):
        """Parse multiple records in a batch."""
        batch = [sample_record] * 3
        traces = parser.parse_batch(batch, start_index=0)
        
        assert len(traces) >= 1  # At least first one parses
        assert all(trace.n_steps == 3 for trace in traces)


class TestConfigurationVariants:
    """Test parser with different configurations."""
    
    def test_custom_embedding_model(self):
        """Parser should accept custom embedding model."""
        config = IngestionConfig(
            embedding_model="sentence-transformers/all-mpnet-base-v2"
        )
        parser = HuggingFaceParser(config)
        
        assert parser.config.embedding_model == "sentence-transformers/all-mpnet-base-v2"
    
    def test_custom_sensitivity_level(self):
        """Parser should respect sensitivity configuration."""
        config = IngestionConfig(sensitivity=Sensitivity.INTERNAL)
        parser = HuggingFaceParser(config)
        
        sample = {
            "problem": "Test",
            "steps": [],
        }
        trace = parser.parse_record(sample, 0)
        
        assert trace is not None
        assert trace.provenance_sensitivity == Sensitivity.INTERNAL
