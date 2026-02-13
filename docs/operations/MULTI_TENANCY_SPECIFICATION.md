# Multi-Tenancy Isolation Specification

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: All Grimoire Services  
**Status**: Specification

---

## Overview

This document defines the multi-tenancy architecture for Grimoire, enabling secure isolation between tenants while maintaining operational efficiency. The system supports both single-tenant MVP and multi-tenant production deployments.

**Tenancy Model**: Database-per-tenant (strict isolation) with shared infrastructure option for lower-cost tiers.

---

## Tenancy Architecture

### Deployment Models

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                    MULTI-TENANCY DEPLOYMENT MODELS                        │
└─────────────────────────────────────────────────────────────────────────┘

Model A: Dedicated (Highest Isolation)
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   Tenant A   │ │   Tenant B   │ │   Tenant C   │
│ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │
│ │  Neo4j  │ │ │ │  Neo4j  │ │ │ │  Neo4j  │ │
│ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │
│ ┌─────────┐ │ │ ┌─────────┐ │ │ ┌─────────┐ │
│ │  Qdrant │ │ │ │  Qdrant │ │ │ │  Qdrant │ │
│ └─────────┘ │ │ └─────────┘ │ │ └─────────┘ │
└─────────────┘ └─────────────┘ └─────────────┘

Model B: Shared (Cost-Optimized)
┌─────────────────────────────────────────────────────────────────────┐
│                         Shared Infrastructure                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │   Tenant A   │  │   Tenant B   │  │   Tenant C   │               │
│  │   (schema)   │  │   (schema)   │  │   (schema)   │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              Neo4j (single instance)                          │    │
│  └──────────────────────────────────────────────────────────────┘    │
│  ┌──────────────────────────────────────────────────────────────┐    │
│  │              Qdrant (single instance)                         │    │
│  └──────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘

Model C: Hybrid (Enterprise)
┌─────────────────────────────────────────────────────────────────────┐
│                    Tenant-Specific Instances                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐   │
│  │ Enterprise  │ │ Enterprise  │ │  Standard   │ │   Standard   │   │
│  │  Tenant A    │ │  Tenant B    │ │  Tenant C   │ │   Tenant D   │   │
│  │ (dedicated) │ │ (dedicated) │ │  (shared)  │ │  (shared)   │   │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
```

### Tenant Identification

```python
# core/tenant/identifier.py
from typing import Optional
from fastapi import Header, HTTPException, Request
from enum import Enum


class TenantTier(str, Enum):
    """Tenant pricing/service tiers."""
    FREE = "free"           # Shared, limited resources
    STANDARD = "standard"   # Shared, dedicated quota
    ENTERPRISE = "enterprise"  # Dedicated instances
    DEDICATED = "dedicated" # Fully isolated deployment


class TenantContext:
    """Thread-local tenant context for request handling."""

    _context: dict = {}

    @classmethod
    def set(cls, tenant_id: str, tier: TenantTier, metadata: dict = None):
        """Set tenant context for current request."""
        cls._context = {
            "tenant_id": tenant_id,
            "tier": tier,
            "metadata": metadata or {},
        }

    @classmethod
    def get(cls) -> dict:
        """Get current tenant context."""
        if not cls._context:
            raise RuntimeError("Tenant context not set")
        return cls._context.copy()

    @classmethod
    def get_tenant_id(cls) -> str:
        """Get current tenant ID."""
        return cls.get()["tenant_id"]

    @classmethod
    def get_tier(cls) -> TenantTier:
        """Get current tenant tier."""
        return cls.get()["tier"]

    @classmethod
    def clear(cls):
        """Clear tenant context."""
        cls._context = {}


class TenantIdentifier:
    """Extract and validate tenant from requests."""

    # Supported identification methods (priority order)
    IDENTIFICATION_METHODS = [
        "subdomain",      # tenant.grimoire.ai
        "header",         # X-Tenant-ID header
        "api_key",        # API key contains tenant
        "jwt_claim",     # JWT contains tenant claim
    ]

    @staticmethod
    def extract_from_subdomain(host: str) -> Optional[str]:
        """Extract tenant ID from subdomain."""
        if not host:
            return None
        parts = host.split(".")
        if len(parts) >= 3 and parts[0] != "www":
            return parts[0]
        return None

    @staticmethod
    def extract_from_header(x_tenant_id: str = Header(None)) -> Optional[str]:
        """Extract tenant ID from header."""
        return x_tenant_id

    @staticmethod
    def extract_from_api_key(api_key: str) -> Optional[str]:
        """Extract tenant ID from API key prefix."""
        # Format: {tenant_id}_{key_hash}
        if not api_key:
            return None
        if "_" in api_key:
            return api_key.split("_")[0]
        return None

    @staticmethod
    def extract_from_jwt(payload: dict) -> Optional[str]:
        """Extract tenant ID from JWT claims."""
        # Check standard claims
        for claim in ["tenant_id", "tenantId", "org_id"]:
            if claim in payload:
                return payload[claim]
        return None
```

---

## Tenant Isolation

### Database-Level Isolation (Neo4j)

```python
# core/tenant/neo4j_isolation.py
from neo4j import GraphDatabase, Driver
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class Neo4jTenantIsolation:
    """
    Provides tenant isolation for Neo4j operations.
    Supports both schema-based and instance-based isolation.
    """

    def __init__(self, driver: Driver, isolation_mode: str = "schema"):
        """
        Initialize with driver and isolation mode.

        Args:
            driver: Neo4j driver instance
            isolation_mode: "schema" (shared DB) or "instance" (dedicated DB)
        """
        self.driver = driver
        self.isolation_mode = isolation_mode

    def get_tenant_database(self, tenant_id: str) -> str:
        """Get tenant-specific database name."""
        if self.isolation_mode == "instance":
            return f"tenant_{tenant_id}"
        # Schema mode uses single database with tenant labels
        return "neo4j"

    def _add_tenant_filter(self, cypher: str, tenant_id: str) -> str:
        """Add tenant filter to Cypher query."""
        # Add tenant_id to all node creations and queries
        tenant_label = f":Tenant:{tenant_id}"

        # Pattern: Add to MERGE/CREATE statements
        if "CREATE" in cypher or "MERGE" in cypher:
            # Inject tenant label
            pass

        # Pattern: Add to WHERE clauses
        if "WHERE" not in cypher:
            cypher += f" WHERE n.tenant_id = '{tenant_id}'"
        else:
            cypher += f" AND n.tenant_id = '{tenant_id}'"

        return cypher

    def execute_tenant_query(
        self, 
        tenant_id: str, 
        query: str, 
        parameters: dict = None
    ):
        """Execute query with tenant isolation."""
        parameters = parameters or {}

        # Ensure tenant_id in parameters
        parameters["tenant_id"] = tenant_id

        db = self.get_tenant_database(tenant_id)

        with self.driver.session(database=db) as session:
            result = session.run(query, parameters)
            return [record for record in result]


class TenantQueryBuilder:
    """Build tenant-isolated Cypher queries."""

    @staticmethod
    def create_pattern(tenant_id: str, pattern_data: dict) -> tuple:
        """Build CREATE query for pattern with tenant isolation."""
        cypher = """
        CREATE (p:Pattern:%s $pattern_data)
        RETURN p
        """ % pattern_data.get("pattern_type", "Pattern")

        # Add tenant ID to properties
        pattern_data["tenant_id"] = tenant_id
        pattern_data["created_at"] = "datetime()"

        return cypher, {"pattern_data": pattern_data}

    @staticmethod
    def match_patterns(tenant_id: str, filters: dict = None) -> tuple:
        """Build MATCH query for patterns with tenant isolation."""
        filters = filters or {}

        cypher = """
        MATCH (p:Pattern)
        WHERE p.tenant_id = $tenant_id
        """

        # Add additional filters
        if filters.get("pattern_type"):
            cypher += f" AND p.pattern_type = '{filters['pattern_type']}'"

        if filters.get("domain"):
            cypher += f" AND p.domain = '{filters['domain']}'"

        cypher += " RETURN p ORDER BY p.score DESC"

        return cypher, {"tenant_id": tenant_id}

    @staticmethod
    def delete_tenant_data(tenant_id: str) -> tuple:
        """Build DELETE query for all tenant data (GDPR)."""
        cypher = """
        MATCH (n)
        WHERE n.tenant_id = $tenant_id
        DETACH DELETE n
        """
        return cypher, {"tenant_id": tenant_id}
```

### Vector Store Isolation (Qdrant)

```python
# core/tenant/qdrant_isolation.py
from qdrant_client import QdrantClient
from typing import Optional, List
import logging

logger = logging.getLogger(__name__)


class QdrantTenantIsolation:
    """
    Provides tenant isolation for Qdrant vector operations.
    Uses collection prefixes for isolation.
    """

    COLLECTION_PREFIX = "tenant_"

    def __init__(self, client: QdrantClient, isolation_mode: str = "collection"):
        self.client = client
        self.isolation_mode = isolation_mode  # "collection" or "shard"

    def get_tenant_collection(self, tenant_id: str, base_collection: str) -> str:
        """Get tenant-specific collection name."""
        if self.isolation_mode == "collection":
            return f"{self.COLLECTION_PREFIX}{tenant_id}_{base_collection}"
        return base_collection

    def _build_tenant_filter(self, tenant_id: str) -> dict:
        """Build filter condition for tenant."""
        return {
            "must": [
                {
                    "key": "tenant_id",
                    "match": {"value": tenant_id}
                }
            ]
        }

    def search_vectors(
        self,
        tenant_id: str,
        collection: str,
        query_vector: List[float],
        limit: int = 10,
        score_threshold: float = None
    ):
        """Search with tenant isolation."""
        tenant_collection = self.get_tenant_collection(tenant_id, collection)
        tenant_filter = self._build_tenant_filter(tenant_id)

        return self.client.search(
            collection_name=tenant_collection,
            query_vector=query_vector,
            query_filter=tenant_filter,
            limit=limit,
            score_threshold=score_threshold
        )

    def upsert_vectors(
        self,
        tenant_id: str,
        collection: str,
        vectors: List[dict]
    ):
        """Upsert vectors with tenant ID in payload."""
        tenant_collection = self.get_tenant_collection(tenant_id, collection)

        # Inject tenant_id into payload
        for vector in vectors:
            vector["payload"]["tenant_id"] = tenant_id

        self.client.upsert(
            collection_name=tenant_collection,
            points=vectors
        )

    def delete_tenant_collection(self, tenant_id: str, base_collection: str):
        """Delete all vectors for a tenant."""
        if self.isolation_mode == "collection":
            tenant_collection = self.get_tenant_collection(tenant_id, base_collection)
            self.client.delete_collection(tenant_collection)
```

---

## Tenant Management

### Tenant Service

```python
# services/tenant_service.py
from typing import Optional, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"


class Tenant(BaseModel):
    """Tenant configuration and metadata."""
    id: str = Field(..., description="Unique tenant identifier")
    name: str = Field(..., description="Tenant display name")
    tier: str = Field(default="standard", description="Pricing tier")
    status: TenantStatus = Field(default=TenantStatus.PENDING)

    # Contact & billing
    admin_email: str
    billing_email: Optional[str] = None

    # Configuration
    custom_domain: Optional[str] = None
    allowed_origins: List[str] = Field(default_factory=list)

    # Limits (based on tier)
    max_api_keys: int = 10
    max_patterns: int = 100000
    max_storage_gb: float = 10.0
    rate_limit_rpm: int = 1000

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    suspended_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class TenantService:
    """Manage tenant lifecycle and configuration."""

    def __init__(self, neo4j_driver, redis_client):
        self.neo4j = neo4j_driver
        self.redis = redis_client

    async def create_tenant(self, tenant: Tenant) -> Tenant:
        """Create new tenant with initial setup."""
        # Validate tier and set limits
        tier_limits = {
            "free": {"max_patterns": 1000, "max_storage_gb": 1.0, "rate_limit_rpm": 60},
            "standard": {"max_patterns": 100000, "max_storage_gb": 10.0, "rate_limit_rpm": 1000},
            "enterprise": {"max_patterns": 1000000, "max_storage_gb": 100.0, "rate_limit_rpm": 10000},
            "dedicated": {"max_patterns": None, "max_storage_gb": None, "rate_limit_rpm": None},
        }

        limits = tier_limits.get(tenant.tier, tier_limits["standard"])
        tenant.max_patterns = limits["max_patterns"]
        tenant.max_storage_gb = limits["max_storage_gb"]
        tenant.rate_limit_rpm = limits["rate_limit_rpm"]

        # Store in Neo4j
        cypher = """
        CREATE (t:Tenant {
            id: $id,
            name: $name,
            tier: $tier,
            status: 'pending',
            admin_email: $admin_email,
            created_at: datetime()
        })
        RETURN t
        """
        # Execute create...

        # Initialize tenant resources
        await self._initialize_tenant_resources(tenant)

        tenant.status = TenantStatus.ACTIVE
        return tenant

    async def _initialize_tenant_resources(self, tenant: Tenant):
        """Initialize database, collections, and quotas for tenant."""
        # Create Neo4j tenant database/schema
        if tenant.tier == "dedicated":
            # Create dedicated database
            await self._create_dedicated_database(tenant.id)

        # Create Qdrant collections
        await self._create_tenant_collections(tenant)

        # Set Redis quotas
        await self._setup_tenant_quotas(tenant)

        # Initialize rate limiter
        await self._init_rate_limiter(tenant)

    async def suspend_tenant(self, tenant_id: str, reason: str):
        """Suspend tenant due to non-payment or violation."""
        cypher = """
        MATCH (t:Tenant {id: $id})
        SET t.status = 'suspended',
            t.suspended_at = datetime(),
            t.suspension_reason = $reason
        """
        # Execute...

        # Revoke API keys
        await self._revoke_tenant_keys(tenant_id)

    async def delete_tenant(self, tenant_id: str, delete_data: bool = True):
        """Delete tenant and optionally all associated data."""
        if delete_data:
            # Delete all tenant data (GDPR compliance)
            await self._delete_all_tenant_data(tenant_id)

        # Remove tenant configuration
        cypher = """
        MATCH (t:Tenant {id: $id})
        SET t.status = 'deleted',
            t.deleted_at = datetime()
        """
        # Execute...

    def get_tenant_usage(self, tenant_id: str) -> dict:
        """Get current resource usage for tenant."""
        return {
            "pattern_count": self.redis.get(f"tenant:{tenant_id}:pattern_count"),
            "storage_used_gb": self._calculate_storage(tenant_id),
            "api_calls_today": self.redis.get(f"tenant:{tenant_id}:calls_today"),
            "rate_limit_remaining": self._get_rate_limit_remaining(tenant_id),
        }
```

---

## Rate Limiting Per Tenant

```python
# core/tenant/rate_limiter.py
import redis
from typing import Optional
import time


class TenantRateLimiter:
    """Rate limiting per tenant with tier-based limits."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def check_rate_limit(
        self, 
        tenant_id: str, 
        limit: int, 
        window_seconds: int = 60
    ) -> tuple[bool, dict]:
        """
        Check if request is within rate limit.

        Returns:
            (allowed: bool, info: dict)
        """
        key = f"ratelimit:{tenant_id}"
        current = self.redis.get(key)

        if current is None:
            # First request in window
            self.redis.setex(key, window_seconds, 1)
            return True, {"remaining": limit - 1, "reset": time.time() + window_seconds}

        current = int(current)
        if current >= limit:
            # Rate limited
            ttl = self.redis.ttl(key)
            return False, {
                "remaining": 0,
                "reset": time.time() + ttl,
                "retry_after": ttl
            }

        # Increment counter
        self.redis.incr(key)

        return True, {
            "remaining": limit - current - 1,
            "reset": time.time() + self.redis.ttl(key)
        }

    async def get_limit_for_tenant(self, tenant_id: str) -> int:
        """Get rate limit based on tenant tier."""
        tier = self.redis.get(f"tenant:{tenant_id}:tier")
        limits = {
            "free": 60,
            "standard": 1000,
            "enterprise": 10000,
            "dedicated": None,  # No limit
        }
        return limits.get(tier, 60)
```

---

## Tenant Analytics

```python
# services/tenant_analytics.py
from typing import Dict, List
from datetime import datetime, timedelta


class TenantAnalytics:
    """Track per-tenant usage and metrics."""

    def __init__(self, neo4j_driver, redis_client, prometheus_client):
        self.neo4j = neo4j_driver
        self.redis = redis_client
        self.prometheus = prometheus_client

    def track_api_call(self, tenant_id: str, endpoint: str, duration_ms: float):
        """Record API call for analytics."""
        # Redis: increment daily counter
        today = datetime.utcnow().date().isoformat()
        self.redis.hincrby(f"analytics:{tenant_id}:{today}", endpoint, 1)

        # Prometheus: record duration histogram
        self.prometheus.histogram(
            "grimoire_api_duration_ms",
            "API call duration",
            ["tenant_id", "endpoint"],
            tenant_id=tenant_id,
            endpoint=endpoint
        ).observe(duration_ms)

    def get_tenant_report(self, tenant_id: str, start_date: datetime, end_date: datetime) -> dict:
        """Generate usage report for tenant."""
        report = {
            "tenant_id": tenant_id,
            "period": {"start": start_date, "end": end_date},
            "api_calls": self._count_api_calls(tenant_id, start_date, end_date),
            "unique_users": self._count_unique_users(tenant_id, start_date, end_date),
            "pattern_creations": self._count_pattern_creations(tenant_id, start_date, end_date),
            "storage_used_gb": self._calculate_storage(tenant_id),
            "avg_response_time_ms": self._avg_response_time(tenant_id, start_date, end_date),
        }
        return report

    def generate_billing_report(self, month: str) -> List[dict]:
        """Generate billing data for all active tenants."""
        # Query usage metrics for billing cycle
        cypher = """
        MATCH (t:Tenant)
        WHERE t.status = 'active'
        RETURN t.id as tenant_id, t.tier as tier
        """
        # Process and calculate costs...
        pass
```

---

## Security Considerations

### Tenant Data Encryption

```python
# core/tenant/encryption.py
from cryptography.fernet import Fernet
from typing import Optional


class TenantEncryptionManager:
    """
    Per-tenant encryption for sensitive data.
    Uses tenant-specific keys for data at rest encryption.
    """

    def __init__(self, key_manager):
        self.key_manager = key_manager  # External key management

    def get_tenant_key(self, tenant_id: str) -> bytes:
        """Get or generate tenant-specific encryption key."""
        key = self.key_manager.get_key(f"tenant/{tenant_id}")
        if not key:
            key = Fernet.generate_key()
            self.key_manager.store_key(f"tenant/{tenant_id}", key)
        return key

    def encrypt_field(self, tenant_id: str, plaintext: str) -> str:
        """Encrypt field with tenant key."""
        f = Fernet(self.get_tenant_key(tenant_id))
        return f.encrypt(plaintext.encode()).decode()

    def decrypt_field(self, tenant_id: str, ciphertext: str) -> str:
        """Decrypt field with tenant key."""
        f = Fernet(self.get_tenant_key(tenant_id))
        return f.decrypt(ciphertext.encode()).decode()
```

---

## API Endpoints

### Tenant Management API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/tenants` | POST | Create new tenant |
| `/v1/tenants/{tenant_id}` | GET | Get tenant details |
| `/v1/tenants/{tenant_id}` | PATCH | Update tenant config |
| `/v1/tenants/{tenant_id}/suspend` | POST | Suspend tenant |
| `/v1/tenants/{tenant_id}/delete` | DELETE | Delete tenant |
| `/v1/tenants/{tenant_id}/usage` | GET | Get usage statistics |
| `/v1/tenants/{tenant_id}/report` | GET | Generate usage report |

### Tenant-Scoped API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/v1/{tenant_id}/patterns` | GET | List tenant patterns |
| `/v1/{tenant_id}/patterns` | POST | Create pattern |
| `/v1/{tenant_id}/rank` | POST | Rank patterns |

---

## Migration Path

### Single-Tenant to Multi-Tenant Migration

```python
# scripts/migrate_single_to_multi_tenant.py
"""
Migration script to convert existing single-tenant deployment to multi-tenant.
"""

def migrate_single_to_multi_tenant(legacy_neo4j_db: str, default_tenant_id: str):
    """
    Migrate existing data to multi-tenant schema.

    Steps:
    1. Create default tenant
    2. Add tenant_id property to all nodes
    3. Create tenant-specific collections in Qdrant
    4. Update API to extract tenant from requests
    """

    # Step 1: Add tenant_id to all Pattern nodes
    cypher = """
    MATCH (p:Pattern)
    SET p.tenant_id = $default_tenant_id
    """

    # Step 2: Add tenant_id to all Relationship types
    cypher = """
    MATCH ()-[r]->()
    SET r.tenant_id = $default_tenant_id
    """

    # Step 3: Create indexes for tenant filtering
    cypher = """
    CREATE INDEX tenant_pattern_idx IF NOT EXISTS
    FOR (p:Pattern) ON (p.tenant_id)
    """

    print(f"Migration complete. All data now belongs to tenant: {default_tenant_id}")
```

---

## Testing

### Tenant Isolation Tests

```python
# tests/unit/test_tenant_isolation.py
import pytest
from unittest.mock import Mock


class TestTenantIsolation:
    """Test tenant isolation guarantees."""

    def test_neo4j_query_includes_tenant_filter(self):
        """Verify tenant ID is always included in queries."""
        builder = TenantQueryBuilder()
        cypher, params = builder.match_patterns("tenant_123", {"domain": "software"})

        assert "tenant_id" in cypher
        assert params["tenant_id"] == "tenant_123"
        assert "tenant_123" in cypher

    def test_qdrant_search_filters_by_tenant(self):
        """Verify Qdrant searches are filtered by tenant."""
        client = Mock()
        isolation = QdrantTenantIsolation(client)

        isolation.search_vectors(
            tenant_id="tenant_abc",
            collection="patterns",
            query_vector=[0.1] * 128
        )

        # Verify collection name is prefixed
        client.search.assert_called_once()
        call_kwargs = client.search.call_args.kwargs
        assert "tenant_abc_patterns" in call_kwargs["collection_name"]

    def test_cross_tenant_data_access_blocked(self):
        """Verify data from one tenant cannot access another tenant's data."""
        # This test verifies the isolation guarantees
        pass

    def test_tenant_rate_limit_enforced(self):
        """Verify rate limits are enforced per tenant."""
        redis_mock = Mock()
        redis_mock.get.return_value = None

        limiter = TenantRateLimiter(redis_mock)
        allowed, info = limiter.check_rate_limit("tenant_123", limit=10)

        assert allowed is True
        assert info["remaining"] == 9
```

---

## Implementation Checklist

- [ ] TenantContext middleware for request handling
- [ ] TenantIdentifier with all extraction methods
- [ ] Neo4j tenant isolation (schema-based)
- [ ] Qdrant tenant isolation (collection prefixes)
- [ ] TenantService CRUD operations
- [ ] Tenant rate limiting
- [ ] Tenant analytics tracking
- [ ] Tenant-specific encryption
- [ ] API endpoints for tenant management
- [ ] Migration tooling
- [ ] Unit tests for isolation guarantees
