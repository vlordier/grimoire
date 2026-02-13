"""HuggingFace dataset ingestion parser.

This module provides functionality to parse reasoning traces from HuggingFace datasets
(specifically OpenThoughts-114k and OpenThoughts3-1.2M) into the canonical Pydantic schema.

Key features:
- Deterministic trace_id generation (content hash + ULID)
- Deduplication detection via content hashing
- Configurable embedding model
- Schema validation per Constitution Principle VI

References:
- Spec: specs/001-canonical-schema-implementation/spec.md
- Plan: specs/001-canonical-schema-implementation/plan.md
- Constitution Principle VI: Canonical Schema Contract
"""

import hashlib
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from ulid import ULID

from datasets import load_dataset
from pydantic import ValidationError

from grimoire.core.schema.models import (
    Trace,
    Step,
    StepRole,
    DomainTag,
    Sensitivity,
    LicenseType,
    SourceType,
   SourceRef,
)


class IngestionConfig:
    """Configuration for dataset ingestion.
   
    Attributes:
        dataset_name: HuggingFace dataset identifier
        embedding_model: Model ID for embeddings (default: all-MiniLM-L6-v2)
        pipeline_version: Version string for provenance tracking 
        sensitivity: Default sensitivity level for ingested traces
    """
    
    def __init__(
        self,
        dataset_name: str = "open-thoughts/Open Thoughts-114k",
        embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2",
        pipeline_version: str = "0.1.0-alpha",
        sensitivity: Sensitivity = Sensitivity.PUBLIC,
    ):
        self.dataset_name = dataset_name
        self.embedding_model = embedding_model
        self.pipeline_version = pipeline_version
        self.sensitivity = sensitivity


class HuggingFaceParser:
    """Parser for HuggingFace OpenThoughts datasets.
   
    Converts raw dataset records into canonical Trace + Step structures
    with full provenance metadata and deduplication support.
    """
    
    def __init__(self, config: Optional[IngestionConfig] = None):
        """Initialize parser with configuration.
       
        Args:
            config: Ingestion configuration (uses defaults if None)
        """
        self.config = config or IngestionConfig()
        self._dedup_cache: Dict[str, str] = {}  # content_hash -> canonical_trace_id
       
    def generate_trace_id(self, problem: str, domain: str, tags: List[str]) -> tuple[str, str]:
        """Generate composite trace_id with content hash + ULID.
       
        Per clarification Q3 from spec: Deterministic base enables dedup detection;
        ULID suffix guarantees uniqueness for different solution attempts.
       
        Args:
            problem: Problem statement text
            domain: Domain tag
            tags: List of tag strings
           
        Returns:
            Tuple of (trace_id, content_hash) where:
                trace_id = base58(SHA256(problem+domain+tags))[:12] + "-" + ULID[:8]
                content_hash = full SHA256 hex digest for dedup lookup
        """
        # Create deterministic content signature
        content = json.dumps({
            "problem": problem,
            "domain": domain,
            "tags": sorted(tags),  # Sort for determinism
        }, sort_keys=True)
       
        # SHA256 hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
       
        # Base58 encode first 12 chars (simplified: using hex for MVP)
        # Production would use proper base58 encoding
        deterministic_base = content_hash[:12]
       
        # Generate ULID for uniqueness
        ulid_suffix = str(ULID())[:8]
       
        trace_id = f"{deterministic_base}-{ulid_suffix}"
       
        return trace_id, content_hash
   
    def parse_record(self, record: Dict[str, Any], record_index: int) -> Optional[Trace]:
        """Parse a single dataset record into a Trace with Steps.
       
        Args:
            record: Raw HuggingFace dataset record
            record_index: Sequential index in dataset (for debugging)
           
        Returns:
            Parsed Trace object if valid, None if validation fails
        """
        try:
            # Extract problem statement (assuming 'problem' or 'question' field)
            problem = record.get("problem") or record.get("question") or record.get("text", "")
            if not problem:
                print(f"Warning: Record {record_index} missing problem statement, skipping")
                return None
           
            # Extract domain (default to GENERAL if not specified)
            domain_str = record.get("domain", "GENERAL").upper()
            try:
                domain = DomainTag[domain_str]
            except KeyError:
                domain = DomainTag.GENERAL
           
            # Extract tags
            tags = record.get("tags", [])
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",")]
           
            # Generate trace_id with deduplication tracking
            trace_id, content_hash = self.generate_trace_id(problem, domain_str, tags)
           
            # Check for duplicates
            is_duplicate = False
            duplicate_of = None
            if content_hash in self._dedup_cache:
                is_duplicate = True
                duplicate_of = self._dedup_cache[content_hash]
            else:
                self._dedup_cache[content_hash] = trace_id
           
            # Parse steps (assuming 'steps' field with list of step dicts)
            steps_data = record.get("steps", [])
            if isinstance(steps_data, str):
                # Sometimes steps might be JSON string
                try:
                    steps_data = json.loads(steps_data)
                except json.JSONDecodeError:
                    steps_data = []
           
            n_steps = len(steps_data)
           
            # Create provenance source reference
            source_ref = SourceRef(
                source_type=SourceType.HUGGINGFACE,
                source_id=self.config.dataset_name,
                record_id=str(record_index),
            )
           
            # Build Trace object
            now = datetime.utcnow()
            trace = Trace(
                trace_id=trace_id,
                title=record.get("title") or problem[:100],  # Truncate title if needed
                domain=domain,
                tags=tags,
                problem=problem[:5000] if len(problem) > 5000 else problem,  # Truncate per plan
                created_at=now,
                updated_at=now,
                status="ingested",
                trace_version=1,
                n_steps=n_steps,
                outcome=record.get("outcome"),
                provenance_sources=[source_ref],
                provenance_license=LicenseType.APACHE_2_0,  # OpenThoughts uses Apache 2.0
                provenance_license_url="https://www.apache.org/licenses/LICENSE-2.0",
                provenance_attribution=f"OpenThoughts dataset: {self.config.dataset_name}",
                provenance_sensitivity=self.config.sensitivity,
                provenance_ingested_at=now,
                provenance_pipeline_version=self.config.pipeline_version,
                provenance_schema_version="v1",
                content_hash=content_hash,
                is_duplicate=is_duplicate,
                duplicate_of=duplicate_of,
            )
           
            return trace
           
        except ValidationError as e:
            print(f"Validation error for record {record_index}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error parsing record {record_index}: {e}")
            return None
   
    def load_dataset(self, split: str = "train", streaming: bool = False) -> Any:
        """Load HuggingFace dataset.
       
        Args:
            split: Dataset split to load (default: "train")
            streaming: Use streaming mode for large datasets
           
        Returns:
            Dataset object from HuggingFace datasets library
        """
        print(f"Loading dataset: {self.config.dataset_name} (split={split}, streaming={streaming})")
        dataset = load_dataset(
            self.config.dataset_name,
            split=split,
            streaming=streaming,
        )
        return dataset
   
    def parse_batch(
        self,
        records: List[Dict[str, Any]],
        start_index: int = 0,
    ) -> List[Trace]:
        """Parse a batch of records.
       
        Args:
            records: List of raw dataset records
            start_index: Starting index for record numbering
           
        Returns:
            List of successfully parsed Trace objects
        """
        traces = []
        for idx, record in enumerate(records):
            trace = self.parse_record(record, start_index + idx)
            if trace:
                traces.append(trace)
        return traces
   
    def get_dedup_stats(self) -> Dict[str, int]:
        """Get deduplication statistics.
       
        Returns:
            Dict with 'total_seen' and 'unique_traces' counts
        """
        return {
            "unique_traces": len(self._dedup_cache),
            "duplicates_detected": sum(
                1 for trace_id in self._dedup_cache.values()
                if trace_id != self._dedup_cache.get(hashlib.sha256(trace_id.encode()).hexdigest())
            ),
        }
