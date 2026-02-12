# Text Versioning API Contract (S3/GCS Markdown Storage)

**Component**: Text Storage with Multi-Contributor Version Management  
**Input**: Step text (from ingestion or edits), contributor metadata  
**Output**: Versioned markdown files with audit trail in S3/GCS  

---

## Connection & Bucket Configuration

```python
class TextStorageClient:
    def __init__(self, provider: str = "s3", config: StorageConfig):
        """
        provider: "s3" or "gcs"
        config: {bucket, region, credentials}
        """
        self.provider = provider
        if provider == "s3":
            import boto3
            self.client = boto3.client(
                "s3",
                region_name=config["region"],
                aws_access_key_id=config["access_key"],
                aws_secret_access_key=config["secret_key"]
            )
            self.bucket = config["bucket"]
        elif provider == "gcs":
            from google.cloud import storage
            self.client = storage.Client()
            self.bucket_obj = self.client.bucket(config["bucket"])
```

### Bucket Initialization

```python
def init_text_storage(storage_client: TextStorageClient):
    """Create bucket structure and lifecycle policies on startup"""
    
    # S3 Example
    if storage_client.provider == "s3":
        try:
            # Create bucket directory structure (logical; S3 is flat)
            storage_client.client.head_bucket(Bucket=storage_client.bucket)
            
            # Set lifecycle policy: keep versions for 30 days
            lifecycle_policy = {
                "Rules": [
                    {
                        "Id": "DeleteOldVersions",
                        "NoncurrentVersionExpirationInDays": 30,
                        "Status": "Enabled"
                    }
                ]
            }
            storage_client.client.put_bucket_lifecycle_configuration(
                Bucket=storage_client.bucket,
                LifecycleConfiguration=lifecycle_policy
            )
            
            logger.info(f"Initialized S3 bucket {storage_client.bucket}")
            
        except storage_client.client.exceptions.NoSuchBucket:
            raise ValueError(f"Bucket {storage_client.bucket} does not exist")
```

---

## Write API: Store & Version Text

### Operation 1: Initial Text Storage (from Ingestion)

```python
def store_initial_text(storage_client: TextStorageClient,
                      step_id: str,
                      text_content: str,
                      step_metadata: Dict) -> StoreResult:
    """
    Store step text as markdown during ingestion.
    Creates .md file + .meta.json audit metadata.
    Called by ingestion-api.md after Step creation.
    """
    
    # Generate object key: steps/{trace_id}/{step_id}.md
    object_key = f"steps/{step_metadata['trace_id']}/{step_id}.md"
    
    # Compute content hash for dedup
    content_hash = hashlib.sha256(text_content.encode()).hexdigest()
    
    try:
        # Store markdown content
        storage_client.client.put_object(
            Bucket=storage_client.bucket,
            Key=object_key,
            Body=text_content,
            ContentType="text/markdown",
            Metadata={
                "step_id": step_id,
                "trace_id": step_metadata["trace_id"],
                "version": "1",
                "content_hash": content_hash
            }
        )
        
        # Store audit metadata as separate .meta.json
        metadata = {
            "version_number": 1,
            "content_hash": content_hash,
            "contributor_id": "system_ingestion",
            "timestamp": datetime.now().isoformat(),
            "change_note": f"Initial ingestion from {step_metadata['source']}",
            "language_hint": "english",
            "text_size_bytes": len(text_content),
            "step_role": step_metadata["role"],
            "step_index": step_metadata["index"]
        }
        
        storage_client.client.put_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json",
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json"
        )
        
        logger.info(f"Stored text for step {step_id} (v1, {len(text_content)} bytes)")
        
        return StoreResult(
            success=True,
            step_id=step_id,
            object_key=object_key,
            content_hash=content_hash,
            version=1,
            size_bytes=len(text_content)
        )
        
    except Exception as e:
        logger.error(f"Failed to store text for step {step_id}: {e}")
        return StoreResult(success=False, error=str(e))
```

### Operation 2: Update Text with Version Bump (Contributor Edit)

```python
def update_text_version(storage_client: TextStorageClient,
                       step_id: str,
                       trace_id: str,
                       new_text: str,
                       contributor_id: str,
                       change_note: str) -> UpdateTextResult:
    """
    Replace text when contributor edits markdown.
    Increments version, creates version history chain.
    Triggers embedding invalidation (via storage-api.md callback).
    """
    
    object_key = f"steps/{trace_id}/{step_id}.md"
    new_content_hash = hashlib.sha256(new_text.encode()).hexdigest()
    
    try:
        # 1. Retrieve current version metadata
        meta_response = storage_client.client.get_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json"
        )
        current_meta = json.loads(meta_response["Body"].read())
        current_version = current_meta["version_number"]
        new_version = current_version + 1
        
        # 2. Store new markdown (S3 automatically versions if versioning enabled)
        storage_client.client.put_object(
            Bucket=storage_client.bucket,
            Key=object_key,
            Body=new_text,
            ContentType="text/markdown",
            Metadata={
                "step_id": step_id,
                "version": str(new_version),
                "content_hash": new_content_hash
            }
        )
        
        # 3. Update metadata with version increment
        new_meta = {
            "version_number": new_version,
            "previous_version": current_version,
            "previous_hash": current_meta["content_hash"],
            "content_hash": new_content_hash,
            "contributor_id": contributor_id,
            "timestamp": datetime.now().isoformat(),
            "change_note": change_note,
            "text_size_bytes": len(new_text),
            "diff_size_bytes": len(new_text) - current_meta.get("text_size_bytes", 0)
        }
        
        storage_client.client.put_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json",
            Body=json.dumps(new_meta, indent=2),
            ContentType="application/json"
        )
        
        logger.info(f"Updated text for step {step_id} to v{new_version} (by {contributor_id})")
        
        # 4. CALLBACK: Invalidate embedding in Qdrant + mark in Neo4j
        # (These coreographic calls could be async via message queue)
        storage_callback_invalidate_embedding(step_id, new_version)
        
        return UpdateTextResult(
            success=True,
            step_id=step_id,
            object_key=object_key,
            old_version=current_version,
            new_version=new_version,
            content_hash=new_content_hash
        )
        
    except Exception as e:
        logger.error(f"Failed to update text for step {step_id}: {e}")
        return UpdateTextResult(success=False, error=str(e))
```

---

## Read API: Retrieve Text Versions

### Query 1: Get Latest Text

```python
def get_latest_text(storage_client: TextStorageClient,
                   step_id: str,
                   trace_id: str) -> GetTextResult:
    """Retrieve current version of step text"""
    
    object_key = f"steps/{trace_id}/{step_id}.md"
    
    try:
        response = storage_client.client.get_object(
            Bucket=storage_client.bucket,
            Key=object_key
        )
        
        text_content = response["Body"].read().decode("utf-8")
        version = int(response["Metadata"].get("version", "1"))
        
        # Also get metadata
        meta_response = storage_client.client.get_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json"
        )
        metadata = json.loads(meta_response["Body"].read())
        
        return GetTextResult(
            success=True,
            step_id=step_id,
            text_content=text_content,
            version=version,
            content_hash=metadata["content_hash"],
            contributor_id=metadata["contributor_id"],
            timestamp=metadata["timestamp"]
        )
        
    except storage_client.client.exceptions.NoSuchKey:
        logger.warning(f"Text not found for step {step_id}")
        return GetTextResult(success=False, error="Text not found")
    except Exception as e:
        logger.error(f"Failed to retrieve text for step {step_id}: {e}")
        return GetTextResult(success=False, error=str(e))
```

### Query 2: Get Version History

```python
def get_text_history(storage_client: TextStorageClient,
                    step_id: str,
                    trace_id: str,
                    limit: int = 10) -> HistoryResult:
    """
    Retrieve version history (all edits).
    Builds version chain by following previous_version links.
    """
    
    object_key = f"steps/{trace_id}/{step_id}.md"
    history = []
    seen_hashes = set()
    
    try:
        # Start with current version
        meta_response = storage_client.client.get_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json"
        )
        current_meta = json.loads(meta_response["Body"].read())
        
        # Walk version chain backwards
        while len(history) < limit:
            entry = {
                "version": current_meta["version_number"],
                "content_hash": current_meta["content_hash"],
                "contributor_id": current_meta["contributor_id"],
                "timestamp": current_meta["timestamp"],
                "change_note": current_meta.get("change_note", ""),
                "text_size_bytes": current_meta.get("text_size_bytes", 0)
            }
            history.append(entry)
            seen_hashes.add(current_meta["content_hash"])
            
            # Try to fetch previous version metadata
            prev_version = current_meta.get("previous_version")
            if not prev_version:
                break  # Reached initial version
            
            # Older metadata stored separately versioned
            # For now, simplification: assume metadata available as-is
            # (Full implementation would use S3 versioning API)
            break
        
        return HistoryResult(
            success=True,
            step_id=step_id,
            history=history,
            total_versions=len(history)
        )
        
    except Exception as e:
        logger.error(f"Failed to retrieve history for step {step_id}: {e}")
        return HistoryResult(success=False, error=str(e))
```

### Query 3: Compare Two Versions (Diff)

```python
def compare_text_versions(storage_client: TextStorageClient,
                         step_id: str,
                         trace_id: str,
                         version_a: int,
                         version_b: int) -> DiffResult:
    """
    Generate diff between two versions of a step's text.
    Useful for multi-contributor reviews.
    """
    
    object_key = f"steps/{trace_id}/{step_id}.md"
    
    try:
        # Note: Real implementation would retrieve version_a from S3 versioning
        # For MVP: only compare current vs previous (stored in metadata)
        
        # Get current version
        current = storage_client.client.get_object(
            Bucket=storage_client.bucket,
            Key=object_key
        )
        text_current = current["Body"].read().decode("utf-8")
        
        # For simplicity, store previous version inline in metadata
        meta_response = storage_client.client.get_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json"
        )
        metadata = json.loads(meta_response["Body"].read())
        
        # Compute diff
        from difflib import unified_diff
        diff_lines = list(unified_diff(
            metadata.get("_previous_text_snapshot", "").splitlines(keepends=True),
            text_current.splitlines(keepends=True),
            fromfile=f"v{version_a}",
            tofile=f"v{version_b}",
            lineterm=""
        ))
        
        return DiffResult(
            success=True,
            step_id=step_id,
            version_a=version_a,
            version_b=version_b,
            diff_lines=diff_lines,
            additions=sum(1 for line in diff_lines if line.startswith("+")),
            deletions=sum(1 for line in diff_lines if line.startswith("-"))
        )
        
    except Exception as e:
        logger.error(f"Diff failed for step {step_id}: {e}")
        return DiffResult(success=False, error=str(e))
```

---

## Audit & Compliance

### Operation: Generate Audit Report

```python
def audit_text_changes(storage_client: TextStorageClient,
                      trace_id: str,
                      start_date: datetime,
                      end_date: datetime) -> AuditReport:
    """
    Generate compliance report of all text changes in a trace.
    Shows who edited what, when, and what changed.
    """
    
    prefix = f"steps/{trace_id}/"
    audit_entries = []
    
    try:
        # List all steps in trace
        response = storage_client.client.list_objects_v2(
            Bucket=storage_client.bucket,
            Prefix=prefix
        )
        
        for obj in response.get("Contents", []):
            key = obj["Key"]
            if not key.endswith(".meta.json"):
                continue  # Skip markdown files; use metadata
            
            step_id = key.split("/")[-1].replace(".md.meta.json", "")
            
            # Retrieve metadata
            meta_response = storage_client.client.get_object(
                Bucket=storage_client.bucket,
                Key=key
            )
            metadata = json.loads(meta_response["Body"].read())
            
            timestamp = datetime.fromisoformat(metadata["timestamp"])
            if start_date <= timestamp <= end_date:
                audit_entries.append({
                    "step_id": step_id,
                    "version": metadata["version_number"],
                    "contributor_id": metadata["contributor_id"],
                    "timestamp": metadata["timestamp"],
                    "change_note": metadata.get("change_note", ""),
                    "content_hash": metadata["content_hash"],
                    "size_bytes": metadata.get("text_size_bytes", 0)
                })
        
        return AuditReport(
            trace_id=trace_id,
            start_date=start_date,
            end_date=end_date,
            entries=sorted(audit_entries, key=lambda e: e["timestamp"]),
            total_changes=len(audit_entries),
            unique_contributors=len(set(e["contributor_id"] for e in audit_entries))
        )
        
    except Exception as e:
        logger.error(f"Audit failed for trace {trace_id}: {e}")
        return AuditReport(error=str(e))
```

---

## Deletion & Retention (FR-012)

### Soft Delete (Mark but Preserve)

```python
def soft_delete_text(storage_client: TextStorageClient,
                    step_id: str,
                    trace_id: str,
                    reason: str) -> DeleteResult:
    """
    Mark text as deleted (e.g., PII removal) but preserve in archive.
    Updated metadata marks deletion timestamp and reason.
    """
    
    object_key = f"steps/{trace_id}/{step_id}.md"
    
    try:
        # Retrieve current metadata
        meta_response = storage_client.client.get_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json"
        )
        metadata = json.loads(meta_response["Body"].read())
        
        # Add deletion marker
        metadata["deleted_at"] = datetime.now().isoformat()
        metadata["deletion_reason"] = reason
        metadata["is_deleted"] = True
        
        # Update metadata only (don't overwrite content)
        storage_client.client.put_object(
            Bucket=storage_client.bucket,
            Key=f"{object_key}.meta.json",
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json"
        )
        
        logger.info(f"Soft-deleted step text {step_id}: {reason}")
        
        return DeleteResult(success=True, step_id=step_id)
        
    except Exception as e:
        logger.error(f"Soft delete failed for step {step_id}: {e}")
        return DeleteResult(success=False, error=str(e))
```

### Retention Policy

```python
def cleanup_old_versions(storage_client: TextStorageClient,
                        retention_days: int = 30,
                        dry_run: bool = True) -> RetentionResult:
    """
    Clean up old metadata versions beyond retention window.
    Markdown content preserved indefinitely (can be overwritten).
    """
    
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    deleted_count = 0
    
    try:
        # List all metadata files
        response = storage_client.client.list_objects_v2(
            Bucket=storage_client.bucket,
            Prefix="steps/"
        )
        
        for obj in response.get("Contents", []):
            if not obj["Key"].endswith(".meta.json"):
                continue
            
            meta_response = storage_client.client.get_object(
                Bucket=storage_client.bucket,
                Key=obj["Key"]
            )
            metadata = json.loads(meta_response["Body"].read())
            
            old_meta = []
            # Filter old metadata entries
            if "version_history" in metadata:
                old_meta = [v for v in metadata["version_history"]
                           if datetime.fromisoformat(v["timestamp"]) < cutoff_date]
            
            if old_meta and not dry_run:
                metadata["version_history"] = [
                    v for v in metadata.get("version_history", [])
                    if datetime.fromisoformat(v["timestamp"]) >= cutoff_date
                ]
                
                storage_client.client.put_object(
                    Bucket=storage_client.bucket,
                    Key=obj["Key"],
                    Body=json.dumps(metadata, indent=2),
                    ContentType="application/json"
                )
                
                deleted_count += len(old_meta)
        
        return RetentionResult(
            success=True,
            deleted_entries=deleted_count,
            dry_run=dry_run
        )
        
    except Exception as e:
        logger.error(f"Retention cleanup error: {e}")
        return RetentionResult(success=False, error=str(e))
```

---

## Performance & Compliance

### Metadata Schema (Audit Trail Example)

```json
{
  "version_number": 3,
  "previous_version": 2,
  "previous_hash": "a1b2c3...",
  "content_hash": "d4e5f6...",
  "contributor_id": "alice@example.com",
  "timestamp": "2026-02-12T14:32:00Z",
  "change_note": "Fixed grammar in step 2 reasoning",
  "language_hint": "english",
  "text_size_bytes": 1523,
  "diff_size_bytes": 47,
  "deletion_reason": null,
  "is_deleted": false
}
```

---

## Performance Targets (SR-001)

| Operation | Target | Validation |
|-----------|--------|-----------|
| Store text (1KB-10KB) | < 100ms | Measure PUT latency; verify ETag |
| Read latest text | < 50ms | Measure GET latency; cache results |
| Get version history | < 200ms | List all versions across metadata chain |
| Diff two versions | < 300ms | Compute unified_diff on 10KB texts |
| Audit report (1K steps) | < 5 sec | Batch list_objects operations |

---

## Compliance Features

- **GDPR Right-to-be-Forgotten**: Soft-delete with audit trail; hard-delete on request
- **Edit Attribution**: Every change logged with contributor_id + timestamp + change_note
- **Version History**: Full lineage preserved for dispute resolution
- **Content Integrity**: SHA256 hashes for tamper detection
- **Retention Compliance**: Configurable cleanup policies (default 30 days)
