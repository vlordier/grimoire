# Disaster Recovery Specification

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: All Grimoire Services and Data Stores  
**Status**: Specification

---

## Overview

This document defines the comprehensive disaster recovery (DR) strategy for Grimoire to ensure business continuity in the face of:

1. **Infrastructure failures** - Hardware, network, or data center outages
2. **Data corruption** - Logical or physical data corruption
3. **Human error** - Accidental deletion or misconfiguration
4. **Security incidents** - Ransomware, breaches requiring restoration
5. **Natural disasters** - Regional outages requiring geo-failover

**Recovery Objectives**:

- **RPO (Recovery Point Objective)**: 1 hour (max data loss)
- **RTO (Recovery Time Objective)**: 4 hours (max downtime)
- **RTO (Critical path)**: 30 minutes (core ingestion)

---

## Backup Strategy

### Backup Types

| Type | Frequency | Retention | Purpose |
|------|-----------|-----------|---------|
| **Full Neo4j** | Daily | 30 days | Complete graph restore |
| **Incremental Neo4j** | Hourly | 7 days | Point-in-time recovery |
| **Qdrant Snapshots** | Daily | 14 days | Vector index restore |
| **Redis Persistence** | Continuous | 7 days | Event bus recovery |
| **Configuration** | On change | 90 days | Infrastructure restore |
| **Audit Logs** | Real-time | 7 years | Compliance, forensics |

### Neo4j Backup

```bash
#!/bin/bash
# scripts/backup/neo4j_backup.sh

set -e

NEO4J_HOST="${NEO4J_HOST:-localhost}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD}"
BACKUP_DIR="${BACKUP_DIR:-/backups/neo4j}"
S3_BUCKET="${S3_BUCKET:-grimoire-backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="neo4j_backup_${DATE}"

echo "Starting Neo4j backup: ${BACKUP_NAME}"

# Create backup using neo4j-admin
neo4j-admin database dump neo4j \
    --to-path="${BACKUP_DIR}/${BACKUP_NAME}.dump" \
    --verbose

# Compress
gzip "${BACKUP_DIR}/${BACKUP_NAME}.dump"

# Calculate checksum
CHECKSUM=$(sha256sum "${BACKUP_DIR}/${BACKUP_NAME}.dump.gz" | awk '{print $1}')
echo "Backup checksum: ${CHECKSUM}"

# Upload to S3 with encryption
aws s3 cp "${BACKUP_DIR}/${BACKUP_NAME}.dump.gz" \
    "s3://${S3_BUCKET}/neo4j/${BACKUP_NAME}.dump.gz" \
    --server-side-encryption AES256 \
    --metadata "checksum=${CHECKSUM},timestamp=${DATE}"

# Verify upload
aws s3api head-object \
    --bucket "${S3_BUCKET}" \
    --key "neo4j/${BACKUP_NAME}.dump.gz"

# Cleanup old backups (keep last 30)
aws s3 ls "s3://${S3_BUCKET}/neo4j/" | \
    sort | \
    head -n -30 | \
    awk '{print $4}' | \
    xargs -I {} aws s3 rm "s3://${S3_BUCKET}/neo4j/{}"

# Log backup
neo4j "CREATE (b:Backup {
    backup_id: '${BACKUP_NAME}',
    timestamp: datetime(),
    checksum: '${CHECKSUM}',
    size_bytes: $(stat -f%z "${BACKUP_DIR}/${BACKUP_NAME}.dump.gz"),
    location: 's3://${S3_BUCKET}/neo4j/${BACKUP_NAME}.dump.gz',
    status: 'completed'
})"

echo "Backup completed: ${BACKUP_NAME}"
```

### Qdrant Backup

```python
# scripts/backup/qdrant_backup.py

import qdrant_client
import boto3
from datetime import datetime
import json

class QdrantBackup:
    """Qdrant vector store backup manager."""

    def __init__(self, qdrant_host: str, s3_bucket: str):
        self.client = qdrant_client.QdrantClient(host=qdrant_host)
        self.s3 = boto3.client('s3')
        self.bucket = s3_bucket

    def backup_collection(self, collection_name: str) -> dict:
        """Create snapshot of Qdrant collection."""

        # Create snapshot
        snapshot_info = self.client.create_snapshot(
            collection_name=collection_name,
            wait=True
        )

        snapshot_path = snapshot_info.snapshot_path

        # Upload to S3
        s3_key = f"qdrant/{collection_name}/{datetime.utcnow().isoformat()}.snapshot"

        self.s3.upload_file(
            snapshot_path,
            self.bucket,
            s3_key,
            ExtraArgs={
                'ServerSideEncryption': 'AES256',
                'Metadata': {
                    'collection': collection_name,
                    'created': datetime.utcnow().isoformat(),
                    'qdrant_version': snapshot_info.version
                }
            }
        )

        return {
            "collection": collection_name,
            "s3_key": s3_key,
            "snapshot_path": snapshot_path,
            "timestamp": datetime.utcnow().isoformat()
        }

    def backup_all_collections(self) -> List[dict]:
        """Backup all Qdrant collections."""
        collections = self.client.get_collections().collections

        backups = []
        for collection in collections:
            backup = self.backup_collection(collection.name)
            backups.append(backup)

        return backups

    def restore_collection(self, collection_name: str, s3_key: str):
        """Restore collection from S3."""

        # Download from S3
        local_path = f"/tmp/{collection_name}.snapshot"
        self.s3.download_file(self.bucket, s3_key, local_path)

        # Delete existing collection if exists
        try:
            self.client.delete_collection(collection_name)
        except:
            pass

        # Restore from snapshot
        self.client.recover_snapshot(
            collection_name=collection_name,
            snapshot_path=local_path,
            wait=True
        )

        return {"status": "restored", "collection": collection_name}
```

### Redis Backup

```bash
#!/bin/bash
# scripts/backup/redis_backup.sh

REDIS_HOST="${REDIS_HOST:-localhost}"
BACKUP_DIR="${BACKUP_DIR:-/backups/redis}"
S3_BUCKET="${S3_BUCKET:-grimoire-backups}"
DATE=$(date +%Y%m%d_%H%M%S)

echo "Starting Redis backup"

# Trigger BGSAVE
redis-cli -h "${REDIS_HOST}" BGSAVE

# Wait for save to complete
while redis-cli -h "${REDIS_HOST}" LASTSAVE | grep -q "save"; do
    sleep 1
done

# Copy dump file
DUMP_FILE="/var/lib/redis/dump.rdb"
BACKUP_FILE="${BACKUP_DIR}/redis_${DATE}.rdb"
cp "${DUMP_FILE}" "${BACKUP_FILE}"

# Compress
gzip "${BACKUP_FILE}"

# Upload to S3
aws s3 cp "${BACKUP_FILE}.gz" \
    "s3://${S3_BUCKET}/redis/" \
    --server-side-encryption AES256

# Cleanup local backups (keep last 7)
ls -t "${BACKUP_DIR}"/redis_*.rdb.gz | tail -n +8 | xargs rm -f

echo "Redis backup completed"
```

---

## Recovery Procedures

### Neo4j Recovery

```bash
#!/bin/bash
# scripts/recovery/neo4j_restore.sh

set -e

BACKUP_S3_PATH="${1}"
NEO4J_DATA_DIR="${NEO4J_DATA_DIR:-/var/lib/neo4j/data}"

echo "Restoring Neo4j from: ${BACKUP_S3_PATH}"

# Stop Neo4j
systemctl stop neo4j

# Download backup
aws s3 cp "${BACKUP_S3_PATH}" /tmp/neo4j_restore.dump.gz
gunzip /tmp/neo4j_restore.dump.gz

# Verify checksum (if available)
if [ -n "${EXPECTED_CHECKSUM}" ]; then
    ACTUAL_CHECKSUM=$(sha256sum /tmp/neo4j_restore.dump | awk '{print $1}')
    if [ "${EXPECTED_CHECKSUM}" != "${ACTUAL_CHECKSUM}" ]; then
        echo "ERROR: Checksum mismatch!"
        exit 1
    fi
fi

# Backup current data (if any)
if [ -d "${NEO4J_DATA_DIR}/databases/neo4j" ]; then
    mv "${NEO4J_DATA_DIR}/databases/neo4j" \
       "${NEO4J_DATA_DIR}/databases/neo4j.backup.$(date +%s)"
fi

# Restore from dump
neo4j-admin database load neo4j \
    --from-path=/tmp/neo4j_restore.dump \
    --verbose

# Start Neo4j
systemctl start neo4j

# Verify
sleep 5
neo4j status

echo "Neo4j restore completed"
```

### Point-in-Time Recovery

```python
# scripts/recovery/point_in_time_recovery.py

from datetime import datetime, timedelta
import subprocess

class PointInTimeRecovery:
    """Point-in-time recovery for Neo4j."""

    def __init__(self, s3_bucket: str):
        self.s3_bucket = s3_bucket

    def find_closest_backup(self, target_time: datetime) -> dict:
        """Find closest backup to target time."""

        # List all backups
        result = subprocess.run(
            ["aws", "s3", "ls", f"s3://{self.s3_bucket}/neo4j/"],
            capture_output=True,
            text=True
        )

        backups = []
        for line in result.stdout.split('\n'):
            if 'neo4j_backup_' in line:
                parts = line.split()
                date_str = parts[-1].replace('neo4j_backup_', '').replace('.dump.gz', '')
                backup_time = datetime.strptime(date_str, '%Y%m%d_%H%M%S')
                backups.append({
                    'time': backup_time,
                    'key': parts[-1]
                })

        # Find closest
        closest = min(backups, key=lambda x: abs(x['time'] - target_time))
        return closest

    def recover_to_point(self, target_time: datetime):
        """Recover database to specific point in time."""

        # Find closest backup
        backup = self.find_closest_backup(target_time)
        print(f"Using backup from: {backup['time']}")

        # Restore full backup
        s3_path = f"s3://{self.s3_bucket}/neo4j/{backup['key']}"
        subprocess.run(['./scripts/recovery/neo4j_restore.sh', s3_path], check=True)

        # Apply incremental logs if needed
        if backup['time'] < target_time:
            self._apply_incremental_logs(backup['time'], target_time)

        return {'status': 'recovered', 'target_time': target_time}

    def _apply_incremental_logs(self, from_time: datetime, to_time: datetime):
        """Apply incremental transaction logs."""
        # Implementation depends on Neo4j incremental backup setup
        pass
```

---

## High Availability Architecture

### Multi-Region Setup

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         MULTI-REGION ARCHITECTURE                        │
└─────────────────────────────────────────────────────────────────────────┘

Primary Region (us-east-1)          Secondary Region (us-west-2)
┌─────────────────────────┐         ┌─────────────────────────┐
│  Neo4j Cluster          │◄───────►│  Neo4j Replica          │
│  - 3 Core nodes         │  Sync   │  - Async replica       │
│  - 2 Read replicas      │         │  - Lag < 5 seconds     │
└─────────────────────────┘         └─────────────────────────┘
┌─────────────────────────┐         ┌─────────────────────────┐
│  Qdrant Cluster         │◄───────►│  Qdrant Replica        │
│  - 3 nodes              │  Snap   │  - Daily snapshots      │
└─────────────────────────┘         └─────────────────────────┘
┌─────────────────────────┐         ┌─────────────────────────┐
│  Redis Sentinel         │◄───────►│  Redis Replica          │
│  - 3 sentinels          │  Async  │  - Read replica         │
└─────────────────────────┘         └─────────────────────────┘

Failover Trigger:
- Primary region down > 2 minutes
- Automatic DNS failover
- Manual promotion of secondary
```

### Neo4j Cluster Configuration

```cypher
// Configure causal cluster
CALL dbms.cluster.setCausalClusteringConfig({
    "dbms.cluster.discovery.resolver_type": "DNS",
    "dbms.cluster.discovery.endpoints": "neo4j-core-1:5000,neo4j-core-2:5000,neo4j-core-3:5000",
    "dbms.cluster.minimum_core_cluster_size_at_formation": "3",
    "dbms.cluster.minimum_core_cluster_size_at_runtime": "2"
});

// Set up read replicas
CALL dbms.cluster.addReadReplica("neo4j-read-1", "neo4j-core-1:5000");
CALL dbms.cluster.addReadReplica("neo4j-read-2", "neo4j-core-1:5000");
```

---

## Disaster Recovery Runbook

### Scenario 1: Neo4j Primary Failure

```bash
# 1. Detect failure
neo4j_status=$(neo4j status 2>&1)
if [[ $neo4j_status == *"not running"* ]]; then
    echo "Neo4j failure detected"
fi

# 2. Promote read replica to primary
# (Automatic in causal cluster, manual in single instance)

# 3. Update connection strings
# Update service discovery / load balancer

# 4. Verify
neo4j "MATCH (n) RETURN count(n) as node_count"

# 5. Alert
# Send notification to ops team
```

### Scenario 2: Complete Data Center Failure

```bash
#!/bin/bash
# scripts/dr/failover_to_secondary.sh

set -e

echo "INITIATING DISASTER RECOVERY FAILOVER"

# 1. Confirm primary is down
if ! ping -c 3 primary-neo4j.grimoire.local; then
    echo "Primary confirmed down"
else
    echo "Primary still responding! Aborting."
    exit 1
fi

# 2. Promote secondary Neo4j
ssh secondary-neo4j "neo4j-admin cluster promote-to-primary"

# 3. Update DNS
aws route53 change-resource-record-sets \
    --hosted-zone-id Z123456789 \
    --change-batch '{
        "Changes": [{
            "Action": "UPSERT",
            "ResourceRecordSet": {
                "Name": "neo4j.grimoire.local",
                "Type": "CNAME",
                "TTL": 60,
                "ResourceRecords": [{"Value": "secondary-neo4j.grimoire.local"}]
            }
        }]
    }'

# 4. Verify secondary
sleep 30
neo4j -h secondary-neo4j.grimoire.local "MATCH (n) RETURN count(n)"

# 5. Notify
curl -X POST https://alerts.grimoire.local/dr \
    -d '{"event": "failover_complete", "from": "primary", "to": "secondary"}'

echo "FAILOVER COMPLETE"
```

### Scenario 3: Data Corruption

```python
# scripts/dr/corruption_recovery.py

class CorruptionRecovery:
    """Handle data corruption scenarios."""

    def detect_corruption(self) -> dict:
        """Run corruption detection checks."""
        checks = {
            'orphaned_nodes': self._check_orphaned_nodes(),
            'broken_relationships': self._check_broken_relationships(),
            'invalid_properties': self._check_invalid_properties(),
            'schema_violations': self._check_schema_violations()
        }

        return {
            'corruption_detected': any(checks.values()),
            'details': checks
        }

    def _check_orphaned_nodes(self) -> bool:
        """Check for nodes without required relationships."""
        result = neo4j_query("""
            MATCH (s:Step)
            WHERE NOT (s)<-[:CONTAINS]-(:Trace)
            RETURN count(s) as orphaned
        """)
        return result['orphaned'] > 0

    def repair_corruption(self, corruption_report: dict):
        """Attempt to repair corruption."""

        if corruption_report['details']['orphaned_nodes']:
            # Option 1: Delete orphaned nodes
            # Option 2: Reconnect to dummy trace
            # Option 3: Restore from backup
            pass

        if corruption_report['details']['broken_relationships']:
            # Repair relationships
            pass

    def restore_from_backup(self, backup_time: datetime):
        """Full restore from backup."""
        # Stop services
        # Restore Neo4j
        # Restore Qdrant
        # Verify
        # Resume services
        pass
```

---

## Testing

### DR Drill Schedule

| Drill Type | Frequency | Scope | Duration |
|------------|-----------|-------|----------|
| Backup verification | Weekly | Automated restore test | 1 hour |
| Failover test | Monthly | Neo4j primary failure | 2 hours |
| Full DR drill | Quarterly | Complete region failure | 4 hours |
| Chaos engineering | Monthly | Random component failure | Ongoing |

### Backup Verification Test

```python
# tests/dr/test_backup_restore.py

import pytest
from datetime import datetime

class TestBackupRestore:
    """Test disaster recovery procedures."""

    def test_neo4j_backup_integrity(self):
        """Verify Neo4j backup can be restored."""
        # Create test data
        test_data = create_test_data()

        # Take backup
        backup_path = neo4j_backup()

        # Corrupt current data (simulate failure)
        neo4j_query("MATCH (n:Test) DELETE n")

        # Restore from backup
        neo4j_restore(backup_path)

        # Verify data restored
        restored = neo4j_query("MATCH (n:Test) RETURN count(n) as count")
        assert restored['count'] == len(test_data)

    def test_qdrant_snapshot_restore(self):
        """Verify Qdrant snapshot restore."""
        # Create collection
        collection = "test_collection"
        create_test_vectors(collection)

        # Create snapshot
        snapshot = qdrant_backup(collection)

        # Delete collection
        qdrant_client.delete_collection(collection)

        # Restore
        qdrant_restore(snapshot)

        # Verify
        assert qdrant_client.collection_exists(collection)

    def test_failover_procedure(self):
        """Test automated failover."""
        # Simulate primary failure
        stop_neo4j_primary()

        # Wait for failover
        time.sleep(60)

        # Verify secondary promoted
        new_primary = get_neo4j_primary()
        assert new_primary != original_primary

        # Verify services responding
        response = requests.get("http://api.grimoire.local/health")
        assert response.status_code == 200
```

---

## Monitoring

### DR Metrics

```python
# Prometheus metrics for DR
BACKUP_AGE = Gauge(
    'grimoire_backup_age_seconds',
    'Age of last successful backup',
    ['store']  # neo4j, qdrant, redis
)

BACKUP_SIZE = Gauge(
    'grimoire_backup_size_bytes',
    'Size of last backup',
    ['store']
)

REPLICATION_LAG = Gauge(
    'grimoire_replication_lag_seconds',
    'Replication lag to secondary',
    ['store']
)

FAILOVER_TIME = Histogram(
    'grimoire_failover_duration_seconds',
    'Time to complete failover',
    ['scenario']
)

RTO_VIOLATIONS = Counter(
    'grimoire_rto_violations_total',
    'Recovery time objective violations'
)
```

### Alert Rules

```yaml
# alerts/dr-alerts.yml
groups:
  - name: disaster-recovery
    rules:
      - alert: BackupStale
        expr: grimoire_backup_age_seconds > 90000  # 25 hours
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Backup is stale (>25 hours)"

      - alert: ReplicationLagHigh
        expr: grimoire_replication_lag_seconds > 300  # 5 minutes
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Replication lag > 5 minutes"

      - alert: DRDrillOverdue
        expr: time() - grimoire_last_dr_drill_timestamp > 7776000  # 90 days
        for: 0m
        labels:
          severity: warning
        annotations:
          summary: "DR drill overdue (>90 days)"
```

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | AI Assistant | Initial disaster recovery specification |
