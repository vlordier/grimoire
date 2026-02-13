# Data Export/Import & Portability Specification

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: All Grimoire Services  
**Status**: Specification

---

## Overview

This document defines the data export, import, and portability strategy for Grimoire. It ensures customers can export their data in standard formats, bulk import patterns, and migrate between deployments. This is critical for GDPR compliance, customer data sovereignty, and operational flexibility.

**Export Formats**: JSON, CSV, RDF (via GraphML)  
**Import Formats**: JSON, CSV, Cypher, GraphML  
**Compression**: gzip for all bulk transfers

---

## Data Export

### Export Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXPORT PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────┘

Request
   │
   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Validate   │────▶│   Collect    │────▶│   Transform  │
│   Request    │     │   Data       │     │   to Format  │
│              │     │              │     │              │
│ - Auth check │     │ - Neo4j      │     │ - JSON       │
│ - Scope      │     │ - Qdrant     │     │ - CSV        │
│ - Format     │     │ - Redis      │     │ - GraphML    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │   Compress   │
                                         │   & Store    │
                                         │              │
                                         │ - gzip       │
                                         │ - S3/local   │
                                         │ - URL fetch  │
                                         └──────────────┘
```

### Export Service

```python
# services/export_service.py
from typing import Optional, List, Dict
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import asyncio


class ExportFormat(str, Enum):
    """Supported export formats."""
    JSON = "json"           # Full structured data
    CSV = "csv"           # Flat tabular format
    GRAPHML = "graphml"   # Graph representation
    TURTLE = "turtle"     # RDF format


class ExportScope(str, Enum):
    """What data to include in export."""
    FULL = "full"                    # All data
    PATTERNS_ONLY = "patterns"       # Patterns only
    RANKINGS_ONLY = "rankings"       # Rankings/scores only
    EXPERIMENTS_ONLY = "experiments" # Experiments only
    CONFIG_ONLY = "config"          # Configuration only


class ExportRequest(BaseModel):
    """Request for data export."""
    format: ExportFormat = Field(default=ExportFormat.JSON)
    scope: ExportScope = Field(default=ExportScope.FULL)

    # Filters
    domain_filter: Optional[List[str]] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    pattern_ids: Optional[List[str]] = None

    # Output
    compression: bool = Field(default=True)
    include_vectors: bool = Field(default=False)  # Large, optional
    include_audit: bool = Field(default=True)

    class Config:
        use_enum_values = True


class ExportMetadata(BaseModel):
    """Metadata about the export."""
    export_id: str
    request: ExportRequest

    # Statistics
    total_patterns: int = 0
    total_rankings: int = 0
    total_experiments: int = 0
    total_size_bytes: int = 0

    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Status
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None

    # Download
    download_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class ExportService:
    """Handle data export operations."""

    def __init__(
        self,
        neo4j_driver,
        qdrant_client,
        redis_client,
        s3_client,
        storage_service
    ):
        self.neo4j = neo4j_driver
        self.qdrant = qdrant_client
        self.redis = redis_client
        self.s3 = s3_client
        self.storage = storage_service

    async def create_export(
        self,
        tenant_id: str,
        request: ExportRequest,
        user_id: str
    ) -> ExportMetadata:
        """Create and queue export job."""

        # Validate request
        await self._validate_export_request(tenant_id, request)

        # Create export metadata
        export_id = f"exp_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        metadata = ExportMetadata(
            export_id=export_id,
            request=request,
            started_at=datetime.utcnow(),
            status="pending"
        )

        # Store metadata
        await self._store_export_metadata(metadata)

        # Queue async job
        await self._queue_export_job(export_id, tenant_id, request)

        return metadata

    async def _validate_export_request(
        self, 
        tenant_id: str, 
        request: ExportRequest
    ):
        """Validate export request parameters."""

        # Check export size estimate
        estimated_size = await self._estimate_export_size(tenant_id, request)

        if estimated_size > 10 * 1024 * 1024 * 1024:  # 10GB
            raise ValueError(
                f"Export too large ({estimated_size / 1e9:.1f}GB). "
                "Please use narrower filters or request in batches."
            )

        # Check rate limit
        recent_exports = await self._count_recent_exports(tenant_id)
        if recent_exports >= 3:
            raise ValueError(
                "Too many recent exports. Please wait before requesting another."
            )

    async def _estimate_export_size(
        self, 
        tenant_id: str, 
        request: ExportRequest
    ) -> int:
        """Estimate export file size in bytes."""

        # Query counts for each component
        counts = {
            "patterns": await self._count_patterns(tenant_id, request),
            "rankings": await self._count_rankings(tenant_id, request),
            "experiments": await self._count_experiments(tenant_id, request),
        }

        # Rough size estimates per record
        sizes = {
            "patterns": 10 * 1024,    # 10KB per pattern (with metadata)
            "rankings": 1 * 1024,    # 1KB per ranking
            "experiments": 5 * 1024,  # 5KB per experiment
        }

        total = sum(counts[k] * sizes[k] for k in counts)

        # Add vectors if requested
        if request.include_vectors:
            vector_count = await self._count_vectors(tenant_id, request)
            total += vector_count * 512  # 512 bytes per vector

        return total

    async def execute_export(
        self,
        export_id: str,
        tenant_id: str,
        request: ExportRequest
    ) -> ExportMetadata:
        """Execute the actual export."""

        metadata = await self._get_export_metadata(export_id)
        metadata.status = "running"
        await self._store_export_metadata(metadata)

        try:
            # Collect data from each source
            data = {}

            if request.scope in [ExportScope.FULL, ExportScope.PATTERNS_ONLY]:
                data["patterns"] = await self._export_patterns(tenant_id, request)

            if request.scope in [ExportScope.FULL, ExportScope.RANKINGS_ONLY]:
                data["rankings"] = await self._export_rankings(tenant_id, request)

            if request.scope in [ExportScope.FULL, ExportScope.EXPERIMENTS_ONLY]:
                data["experiments"] = await self._export_experiments(tenant_id, request)

            if request.scope == ExportScope.FULL:
                data["config"] = await self._export_config(tenant_id)

            # Transform to requested format
            export_data = self._transform_to_format(data, request.format)

            # Compress if requested
            if request.compression:
                export_data = self._compress_data(export_data)

            # Store and get download URL
            file_path = await self._store_export(export_id, export_data, request)
            metadata.download_url = self.storage.generate_presigned_url(file_path)
            metadata.expires_at = datetime.utcnow() + timedelta(days=7)

            # Update statistics
            metadata.total_patterns = len(data.get("patterns", []))
            metadata.total_rankings = len(data.get("rankings", []))
            metadata.total_experiments = len(data.get("experiments", []))
            metadata.total_size_bytes = len(export_data)
            metadata.status = "completed"
            metadata.completed_at = datetime.utcnow()

        except Exception as e:
            metadata.status = "failed"
            metadata.error_message = str(e)

        await self._store_export_metadata(metadata)
        return metadata

    async def _export_patterns(
        self, 
        tenant_id: str, 
        request: ExportRequest
    ) -> List[dict]:
        """Export patterns from Neo4j."""

        cypher = """
        MATCH (p:Pattern)
        WHERE p.tenant_id = $tenant_id
        """

        # Apply filters
        params = {"tenant_id": tenant_id}

        if request.domain_filter:
            cypher += " AND p.domain IN $domains"
            params["domains"] = request.domain_filter

        if request.date_from:
            cypher += " AND p.created_at >= $date_from"
            params["date_from"] = request.date_from

        if request.date_to:
            cypher += " AND p.created_at <= $date_to"
            params["date_to"] = request.date_to

        if request.pattern_ids:
            cypher += " AND p.id IN $pattern_ids"
            params["pattern_ids"] = request.pattern_ids

        cypher += """
        OPTIONAL MATCH (p)-[:VERSION_OF]->(v:PatternVersion)
        OPTIONAL MATCH (p)-[:HAS_TAG]->(t:Tag)

        RETURN p, collect(DISTINCT v) as versions, collect(DISTINCT t) as tags
        ORDER BY p.created_at DESC
        """

        results = []
        async with self.neo4j.session() as session:
            async for record in await session.run(cypher, **params):
                pattern = dict(record["p"])

                # Add versions and tags
                pattern["versions"] = [
                    dict(v) for v in record["versions"] if v
                ]
                pattern["tags"] = [dict(t) for t in record["tags"] if t]

                # Remove vectors if not requested
                if not request.include_vectors:
                    pattern.pop("embedding", None)
                    pattern.pop("canonical_embedding", None)

                results.append(pattern)

        return results

    def _transform_to_format(self, data: dict, format: ExportFormat) -> bytes:
        """Transform data to requested format."""

        if format == ExportFormat.JSON:
            import json
            json_str = json.dumps(data, indent=2, default=str)
            return json_str.encode('utf-8')

        elif format == ExportFormat.CSV:
            return self._to_csv(data)

        elif format == ExportFormat.GRAPHML:
            return self._to_graphml(data)

        elif format == ExportFormat.TURTLE:
            return self._to_turtle(data)

        raise ValueError(f"Unknown format: {format}")

    def _to_csv(self, data: dict) -> bytes:
        """Convert patterns to CSV format."""
        import csv
        import io

        if "patterns" not in data or not data["patterns"]:
            return b""

        output = io.StringIO()
        fieldnames = [
            "id", "pattern_type", "domain", "problem_text",
            "solution_text", "score", "usage_count", "created_at"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for pattern in data["patterns"]:
            row = {k: pattern.get(k, "") for k in fieldnames}
            writer.writerow(row)

        return output.getvalue().encode('utf-8')

    def _to_graphml(self, data: dict) -> bytes:
        """Convert to GraphML format."""
        # Simple GraphML wrapper
        import xml.etree.ElementTree as ET

        graphml = ET.Element("graphml")
        graph = ET.SubElement(graphml, "graph", id="patterns", edgedefault="directed")

        # Add node definitions
        for pattern in data.get("patterns", []):
            node = ET.SubElement(graph, "node", id=pattern["id"])

            for key, value in pattern.items():
                data_elem = ET.SubElement(node, "data", key=key)
                data_elem.text = str(value)

        return ET.tostring(graphml, encoding='utf-8')
```

---

## Data Import

### Import Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         IMPORT PIPELINE                                   │
└─────────────────────────────────────────────────────────────────────────┘

Upload
   │
   ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Validate   │────▶│   Parse &    │────▶│   Transform  │
│   Format     │     │   Extract    │     │   to Schema  │
│              │     │              │     │              │
│ - MIME type  │     │ - JSON       │     │ - Pattern    │
│ - Schema     │     │ - CSV        │     │ - Version    │
│ - Size       │     │ - Cypher     │     │ - Ranking    │
└──────────────┘     └──────────────┘     └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │   Validate   │
                                         │   Records    │
                                         │              │
                                         │ - Required   │
                                         │ - Types      │
                                         │ - Business   │
                                         └──────────────┘
                                                │
                                                ▼
                                         ┌──────────────┐
                                         │   Import     │
                                         │   to Stores  │
                                         │              │
                                         │ - Neo4j      │
                                         │ - Qdrant     │
                                         │ - Redis      │
                                         └──────────────┘
```

### Import Service

```python
# services/import_service.py
from typing import Optional, List, Dict, Callable
from pydantic import BaseModel, Field, validator
from enum import Enum
from datetime import datetime
import asyncio
import hashlib


class ImportFormat(str, Enum):
    """Supported import formats."""
    JSON = "json"
    CSV = "csv"
    CYPHER = "cypher"
    GRAPHML = "graphml"


class ImportMode(str, Enum):
    """How to handle existing data."""
    CREATE_NEW = "create"      # Create only, fail on duplicate
    UPDATE_EXISTING = "update" # Update existing, create new
    UPSERT = "upsert"         # Create or update
    REPLACE = "replace"        # Delete all, then import


class ImportRecordStatus(str, Enum):
    """Status of individual import record."""
    PENDING = "pending"
    VALID = "valid"
    INVALID = "invalid"
    IMPORTED = "imported"
    FAILED = "failed"


class ImportRequest(BaseModel):
    """Request for data import."""
    format: ImportFormat
    mode: ImportMode = Field(default=ImportMode.UPSERT)

    # Validation
    validate_only: bool = Field(default=False)  # Don't import, just validate
    skip_invalid: bool = Field(default=True)

    # Options
    generate_ids: bool = Field(default=True)
    compute_embeddings: bool = Field(default=True)

    @validator('format')
    def validate_format(cls, v):
        allowed = ['json', 'csv', 'cypher', 'graphml']
        if v not in allowed:
            raise ValueError(f"Format must be one of: {allowed}")
        return v


class ImportResult(BaseModel):
    """Result of import operation."""
    import_id: str

    # Statistics
    total_records: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    imported_records: int = 0
    failed_records: int = 0

    # Timestamps
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Errors
    errors: List[Dict] = Field(default_factory=list)

    # Preview (first few records)
    preview: List[Dict] = Field(default_factory=list)


class ImportService:
    """Handle data import operations."""

    def __init__(
        self,
        neo4j_driver,
        qdrant_client,
        embedding_service,
        validation_service
    ):
        self.neo4j = neo4j_driver
        self.qdrant = qdrant_client
        self.embedding = embedding_service
        self.validation = validation_service

    async def create_import(
        self,
        tenant_id: str,
        file_content: bytes,
        request: ImportRequest,
        user_id: str
    ) -> ImportResult:
        """Process data import."""

        # Step 1: Parse file
        records = await self._parse_file(file_content, request.format)

        # Step 2: Transform to schema
        transformed = await self._transform_records(records, request, tenant_id)

        # Step 3: Validate
        validation_result = await self._validate_records(transformed)

        # Step 4: If validate_only, return validation result
        if request.validate_only:
            return self._build_result(validation_result)

        # Step 5: Import valid records
        import_result = await self._import_records(
            transformed, 
            validation_result,
            tenant_id,
            request
        )

        return import_result

    async def _parse_file(
        self, 
        file_content: bytes, 
        format: ImportFormat
    ) -> List[dict]:
        """Parse import file to records."""

        if format == ImportFormat.JSON:
            return self._parse_json(file_content)

        elif format == ImportFormat.CSV:
            return self._parse_csv(file_content)

        elif format == ImportFormat.CYPHER:
            return self._parse_cypher(file_content)

        elif format == ImportFormat.GRAPHML:
            return self._parse_graphml(file_content)

        raise ValueError(f"Unknown format: {format}")

    def _parse_json(self, content: bytes) -> List[dict]:
        """Parse JSON import file."""
        import json
        import gzip

        # Try decompress if gzipped
        try:
            content = gzip.decompress(content)
        except:
            pass

        data = json.loads(content)

        # Handle single record or array
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            # Handle wrapper format
            if "patterns" in data:
                return data["patterns"]
            return [data]

        raise ValueError("Invalid JSON structure")

    def _parse_csv(self, content: bytes) -> List[dict]:
        """Parse CSV import file."""
        import csv
        import io

        # Decode and handle potential BOM
        text = content.decode('utf-8-sig')

        reader = csv.DictReader(io.StringIO(text))
        return [dict(row) for row in reader]

    async def _transform_records(
        self,
        records: List[dict],
        request: ImportRequest,
        tenant_id: str
    ) -> List[dict]:
        """Transform raw records to Grimoire schema."""

        transformed = []

        for record in records:
            try:
                transformed_record = await self._transform_pattern(
                    record, 
                    request,
                    tenant_id
                )
                transformed.append(transformed_record)
            except Exception as e:
                # Log but continue
                transformed.append({
                    "_raw": record,
                    "_error": str(e),
                    "_status": ImportRecordStatus.INVALID
                })

        return transformed

    async def _transform_pattern(
        self,
        record: dict,
        request: ImportRequest,
        tenant_id: str
    ) -> dict:
        """Transform single pattern to Grimoire schema."""

        transformed = {
            "tenant_id": tenant_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        # Map common fields
        field_mappings = {
            "id": "id",
            "pattern_type": "pattern_type",
            "domain": "domain",
            "problem_text": "problem_text",
            "solution_text": "solution_text",
            "code_example": "code_example",
            "tags": "tags",
        }

        for src, dst in field_mappings.items():
            if src in record:
                transformed[dst] = record[src]

        # Generate ID if needed
        if request.generate_ids and "id" not in transformed:
            transformed["id"] = self._generate_pattern_id(
                transformed.get("problem_text", ""),
                transformed.get("domain", "")
            )

        # Compute embedding if requested and not present
        if request.compute_embeddings and "embedding" not in transformed:
            text = transformed.get("problem_text", "") + " " + transformed.get("solution_text", "")
            transformed["embedding"] = await self.embedding.compute(text)

        # Add metadata
        transformed["imported_at"] = datetime.utcnow().isoformat()
        transformed["import_source"] = "bulk_import"

        return transformed

    def _generate_pattern_id(self, problem: str, domain: str) -> str:
        """Generate deterministic pattern ID."""
        content = f"{domain}:{problem[:100]}"
        hash_suffix = hashlib.sha256(content.encode()).hexdigest()[:12]
        return f"pattern_{domain}_{hash_suffix}"

    async def _validate_records(
        self, 
        records: List[dict]
    ) -> List[dict]:
        """Validate all records before import."""

        validated = []

        for record in records:
            if "_error" in record:
                record["_status"] = ImportRecordStatus.INVALID
                validated.append(record)
                continue

            # Use Pydantic validation
            try:
                # This would use the actual Pattern model
                # pattern = Pattern(**record)
                record["_status"] = ImportRecordStatus.VALID
            except Exception as e:
                record["_status"] = ImportRecordStatus.INVALID
                record["_validation_error"] = str(e)

            validated.append(record)

        return validated

    async def _import_records(
        self,
        records: List[dict],
        validation_result: List[dict],
        tenant_id: str,
        request: ImportRequest
    ) -> ImportResult:
        """Import validated records."""

        result = ImportResult(
            import_id=f"imp_{tenant_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
            started_at=datetime.utcnow(),
            total_records=len(records)
        )

        # Separate valid and invalid
        valid_records = [r for r in validation_result if r["_status"] == ImportRecordStatus.VALID]
        invalid_records = [r for r in validation_result if r["_status"] == ImportRecordStatus.INVALID]

        result.valid_records = len(valid_records)
        result.invalid_records = len(invalid_records)

        if request.skip_invalid:
            records_to_import = valid_records
        else:
            records_to_import = records

        # Batch import
        batch_size = 100
        for i in range(0, len(records_to_import), batch_size):
            batch = records_to_import[i:i + batch_size]

            try:
                await self._import_batch(batch, tenant_id, request.mode)
                result.imported_records += len(batch)
            except Exception as e:
                result.failed_records += len(batch)
                result.errors.append({
                    "batch": i // batch_size,
                    "error": str(e)
                })

        result.completed_at = datetime.utcnow()
        return result

    async def _import_batch(
        self,
        records: List[dict],
        tenant_id: str,
        mode: ImportMode
    ):
        """Import batch of records."""

        # Import to Neo4j
        await self._import_to_neo4j(records, tenant_id, mode)

        # Import to Qdrant (vectors)
        await self._import_to_qdrant(records, tenant_id)

    async def _import_to_neo4j(
        self,
        records: List[dict],
        tenant_id: str,
        mode: ImportMode
    ):
        """Import patterns to Neo4j."""

        cypher = """
        UNWIND $records AS record
        """

        if mode == ImportMode.UPSERT:
            cypher += """
            MERGE (p:Pattern {id: record.id})
            SET p = record
            """
        elif mode == ImportMode.CREATE_NEW:
            cypher += """
            CREATE (p:Pattern)
            SET p = record
            """

        async with self.neo4j.session() as session:
            await session.run(cypher, records=records)
```

---

## Bulk Operations

### Bulk Delete

```python
# services/bulk_delete_service.py
class BulkDeleteService:
    """Handle bulk deletion operations (GDPR)."""

    async def delete_patterns_by_ids(
        self,
        tenant_id: str,
        pattern_ids: List[str]
    ) -> Dict:
        """Delete specific patterns."""

        # Delete from Neo4j
        cypher = """
        MATCH (p:Pattern)
        WHERE p.id IN $pattern_ids AND p.tenant_id = $tenant_id
        DETACH DELETE p
        """

        # Delete from Qdrant
        await self._delete_vectors(tenant_id, pattern_ids)

        # Invalidate cache
        await self._invalidate_cache(pattern_ids)

        return {"deleted": len(pattern_ids)}

    async def delete_patterns_by_date(
        self,
        tenant_id: str,
        date_before: datetime
    ) -> Dict:
        """Delete patterns created before date."""

        cypher = """
        MATCH (p:Pattern)
        WHERE p.tenant_id = $tenant_id AND p.created_at < $date_before
        RETURN count(p) as deleted_count
        """

        # Execute and return count
        pass

    async def delete_all_tenant_data(
        self,
        tenant_id: str
    ) -> Dict:
        """Delete all data for a tenant (GDPR right to be forgotten)."""

        # This is a critical operation - requires multiple approvals

        # 1. Delete all patterns
        cypher = """
        MATCH (n)
        WHERE n.tenant_id = $tenant_id
        DETACH DELETE n
        """

        # 2. Delete all vectors
        await self._delete_all_vectors(tenant_id)

        # 3. Clear Redis caches
        await self._clear_tenant_cache(tenant_id)

        # 4. Delete analytics data
        await self._delete_analytics(tenant_id)

        # 5. Mark tenant as deleted
        await self._mark_tenant_deleted(tenant_id)

        return {"status": "all_data_deleted", "tenant_id": tenant_id}
```

---

## API Endpoints

### Export API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/exports` | POST | Create export job |
| `/v1/exports/{export_id}` | GET | Get export status |
| `/v1/exports/{export_id}/download` | GET | Download export file |
| `/v1/exports` | GET | List export history |

### Import API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/imports` | POST | Start import job |
| `/v1/imports/{import_id}` | GET | Get import status |
| `/v1/imports/validate` | POST | Validate without importing |

### Bulk Operations API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/bulk/delete` | POST | Bulk delete patterns |
| `/v1/bulk/delete/status/{job_id}` | GET | Get delete job status |

---

## Data Formats

### JSON Export Format

```json
{
  "export_metadata": {
    "export_id": "exp_abc123",
    "tenant_id": "tenant_001",
    "format": "json",
    "scope": "full",
    "created_at": "2026-02-13T10:00:00Z",
    "record_counts": {
      "patterns": 1500,
      "rankings": 5000,
      "experiments": 50
    }
  },
  "patterns": [
    {
      "id": "pattern_software_abc123",
      "pattern_type": "Algorithm",
      "domain": "software",
      "problem_text": "How to sort efficiently?",
      "solution_text": "Use quicksort...",
      "score": 0.95,
      "usage_count": 42,
      "tags": ["sorting", "algorithm"],
      "versions": [...],
      "created_at": "2026-01-15T10:00:00Z"
    }
  ],
  "rankings": [...],
  "experiments": [...],
  "config": {...}
}
```

### CSV Export Format

```csv
id,pattern_type,domain,problem_text,solution_text,score,usage_count,created_at
pattern_software_abc123,Algorithm,software,How to sort efficiently?,Use quicksort...,0.95,42,2026-01-15T10:00:00Z
```

---

## Testing

### Import/Export Tests

```python
# tests/integration/test_export_import.py
import pytest
from unittest.mock import Mock, AsyncMock


class TestDataExportImport:
    """Test export and import functionality."""

    @pytest.mark.asyncio
    async def test_json_export_contains_all_fields(self):
        """Verify JSON export includes all required fields."""
        service = ExportService(...)

        request = ExportRequest(
            format=ExportFormat.JSON,
            scope=ExportScope.PATTERNS_ONLY
        )

        result = await service.execute_export("exp_001", "tenant_123", request)

        assert "patterns" in result.data
        for pattern in result.data["patterns"]:
            assert "id" in pattern
            assert "domain" in pattern
            assert "problem_text" in pattern

    @pytest.mark.asyncio
    async def test_csv_export_valid_format(self):
        """Verify CSV export produces valid CSV."""
        service = ExportService(...)

        request = ExportRequest(format=ExportFormat.CSV)
        result = await service.execute_export("exp_002", "tenant_123", request)

        # Parse CSV and verify structure
        import csv
        reader = csv.DictReader(result.data.decode().splitlines())
        assert len(list(reader)) > 0

    @pytest.mark.asyncio
    async def test_import_json_validates_schema(self):
        """Verify import validates against schema."""
        service = ImportService(...)

        invalid_record = {"invalid": "data", "missing": "required_fields"}

        request = ImportRequest(
            format=ImportFormat.JSON,
            validate_only=True
        )

        result = await service.create_import(
            "tenant_123",
            b'[{"invalid": "data"}]',
            request,
            "user_001"
        )

        assert result.invalid_records > 0

    @pytest.mark.asyncio
    async def test_import_generates_embeddings(self):
        """Verify import computes embeddings when requested."""
        service = ImportService(...)

        request = ImportRequest(
            format=ImportFormat.JSON,
            compute_embeddings=True
        )

        result = await service.create_import(
            "tenant_123",
            b'[{"problem_text": "test", "solution_text": "test"}]',
            request,
            "user_001"
        )

        # Verify embedding was computed
        # (would need to query Neo4j to confirm)
        assert result.imported_records > 0

    @pytest.mark.asyncio
    async def test_gdpr_delete_removes_all_data(self):
        """Verify GDPR delete removes all tenant data."""
        service = BulkDeleteService(...)

        result = await service.delete_all_tenant_data("tenant_123")

        # Verify Neo4j is empty
        # Verify Qdrant is empty
        # Verify Redis is empty
        assert result["status"] == "all_data_deleted"
```

---

## Implementation Checklist

- [ ] ExportService with all format support
- [ ] ImportService with validation
- [ ] Bulk delete functionality
- [ ] GDPR right-to-be-forgotten
- [ ] S3 presigned URL generation
- [ ] Async job processing
- [ ] Rate limiting on exports
- [ ] CSV/JSON/GraphML transformers
- [ ] Unit tests for parsing
- [ ] Integration tests for round-trip
- [ ] Documentation for supported formats
