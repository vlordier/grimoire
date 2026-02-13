# Authentication & Authorization Specification

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: All Grimoire Services (Phases 1-3)  
**Status**: Specification

---

## Overview

This document defines the unified authentication and authorization strategy for all Grimoire services. It ensures:

1. **Consistent security** across all 8 features
2. **Service-to-service communication** is authenticated
3. **Role-based access control** (RBAC) for different user types
4. **Audit trail** for all security events

**Auth Method**: API Key + JWT Hybrid (MVP) → OAuth2 + mTLS (Production)

---

## Authentication Architecture

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                         AUTHENTICATION FLOW                              │
└─────────────────────────────────────────────────────────────────────────┘

Client Request
      │
      ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   API        │────▶│   Auth       │────▶│   Service    │
│   Gateway    │     │   Middleware │     │   Handler    │
│              │     │              │     │              │
│ - Rate limit │     │ - Validate   │     │ - Business   │
│ - Route      │     │   API key    │     │   logic      │
│ - Log        │     │ - Decode JWT │     │ - RBAC check │
└──────────────┘     └──────────────┘     └──────────────┘
                                                 │
                                                 ▼
                                          ┌──────────────┐
                                          │   Response   │
                                          │   + Audit    │
                                          └──────────────┘
```

---

## Authentication Methods

### Method 1: API Key (Service-to-Service)

**Use Case**: Internal microservices communication

```http
GET /v1/ingest/status
Host: api.grimoire.local
X-API-Key: grimoire_sk_live_51H8x...j2K9
```

**Implementation**:

```python
# shared/auth/api_key.py

import hashlib
import secrets
from datetime import datetime, timedelta
from pydantic import BaseModel

class APIKey(BaseModel):
    """API key model."""

    key_id: str                    # "pk_live_xxx"
    key_hash: str                  # bcrypt hash of full key
    name: str                      # "ingestion-service"
    scopes: List[str]              # ["ingest:read", "ingest:write"]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used_at: Optional[datetime]
    is_active: bool
    owner: str                     # Service or user identifier

class APIKeyAuth:
    """API key authentication handler."""

    HEADER_NAME = "X-API-Key"
    PREFIX = "grimoire_"

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self._cache = {}  # In-memory cache

    def generate_key(self, name: str, scopes: List[str], 
                     owner: str, ttl_days: int = 365) -> tuple[str, APIKey]:
        """Generate new API key. Returns (full_key, key_record)."""

        # Generate cryptographically secure key
        key_id = f"pk_{secrets.token_urlsafe(16)}"
        secret = secrets.token_urlsafe(32)
        full_key = f"{self.PREFIX}{key_id}_{secret}"

        # Hash for storage
        key_hash = hashlib.sha256(full_key.encode()).hexdigest()

        # Create record
        api_key = APIKey(
            key_id=key_id,
            key_hash=key_hash,
            name=name,
            scopes=scopes,
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(days=ttl_days),
            is_active=True,
            owner=owner
        )

        # Store in Redis
        self.redis.hset(f"apikey:{key_id}", mapping=api_key.dict())

        return full_key, api_key

    async def validate_key(self, request: Request) -> Optional[APIKey]:
        """Validate API key from request header."""

        header_key = request.headers.get(self.HEADER_NAME)
        if not header_key:
            return None

        # Check format
        if not header_key.startswith(self.PREFIX):
            return None

        # Extract key_id
        try:
            key_id = header_key.split("_")[1]
        except IndexError:
            return None

        # Check cache
        if key_id in self._cache:
            api_key = self._cache[key_id]
        else:
            # Load from Redis
            data = self.redis.hgetall(f"apikey:{key_id}")
            if not data:
                return None
            api_key = APIKey(**{k.decode(): v.decode() for k, v in data.items()})
            self._cache[key_id] = api_key

        # Validate
        if not api_key.is_active:
            return None

        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            return None

        # Verify hash
        key_hash = hashlib.sha256(header_key.encode()).hexdigest()
        if not secrets.compare_digest(key_hash, api_key.key_hash):
            return None

        # Update last used (async, don't block)
        asyncio.create_task(self._update_last_used(key_id))

        return api_key

    async def _update_last_used(self, key_id: str):
        """Update last used timestamp."""
        self.redis.hset(f"apikey:{key_id}", "last_used_at", 
                        datetime.utcnow().isoformat())
```

### Method 2: JWT (User Authentication)

**Use Case**: User-facing APIs, dashboard access

```http
GET /v1/patterns
Host: api.grimoire.local
Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Implementation**:

```python
# shared/auth/jwt_auth.py

import jwt
from datetime import datetime, timedelta
from typing import Optional

class JWTAuth:
    """JWT authentication handler."""

    ALGORITHM = "RS256"
    ACCESS_TOKEN_EXPIRE = timedelta(minutes=15)
    REFRESH_TOKEN_EXPIRE = timedelta(days=7)

    def __init__(self, private_key: str, public_key: str):
        self.private_key = private_key
        self.public_key = public_key

    def create_access_token(self, user_id: str, scopes: List[str]) -> str:
        """Create JWT access token."""

        payload = {
            "sub": user_id,                    # Subject (user ID)
            "iss": "grimoire",                  # Issuer
            "aud": "grimoire-api",              # Audience
            "iat": datetime.utcnow(),           # Issued at
            "exp": datetime.utcnow() + self.ACCESS_TOKEN_EXPIRE,
            "scope": " ".join(scopes),          # Scopes
            "type": "access"
        }

        return jwt.encode(payload, self.private_key, algorithm=self.ALGORITHM)

    def validate_token(self, token: str) -> Optional[dict]:
        """Validate and decode JWT."""

        try:
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM],
                audience="grimoire-api",
                issuer="grimoire"
            )
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
```

### Method 3: Mutual TLS (Production)

**Use Case**: High-security production environment

```python
# Production: mTLS configuration
# nginx.conf or envoy proxy

server {
    listen 443 ssl;

    ssl_certificate /etc/ssl/certs/server.crt;
    ssl_certificate_key /etc/ssl/private/server.key;
    ssl_client_certificate /etc/ssl/certs/ca.crt;
    ssl_verify_client on;  # Require client certificate

    location / {
        # Client cert info passed to backend
        proxy_set_header X-SSL-Client-S-DN $ssl_client_s_dn;
        proxy_set_header X-SSL-Client-I-DN $ssl_client_i_dn;
        proxy_set_header X-SSL-Client-Serial $ssl_client_serial;
        proxy_set_header X-SSL-Client-Verify $ssl_client_verify;

        proxy_pass http://backend;
    }
}
```

---

## Authorization (RBAC)

### Role Definitions

```python
# shared/auth/rbac.py

from enum import Enum
from typing import List, Set

class Role(str, Enum):
    """User roles."""

    ADMIN = "admin"                    # Full access
    DATA_ENGINEER = "data_engineer"    # Ingestion, querying
    SAFETY_ENGINEER = "safety_engineer" # Danger classification, guards
    RESEARCHER = "researcher"          # Pattern extraction, ranking
    OPERATOR = "operator"              # Monitoring, dashboards
    SERVICE = "service"                # Internal services
    READONLY = "readonly"              # View-only access

# Permission matrix
PERMISSIONS = {
    Role.ADMIN: {"*"},  # All permissions

    Role.DATA_ENGINEER: {
        "ingest:read", "ingest:write",
        "retrieve:read",
        "storage:read", "storage:write",
        "trace:read", "trace:write"
    },

    Role.SAFETY_ENGINEER: {
        "classify:read", "classify:write",
        "guard:read", "guard:write",
        "danger:read", "danger:write",
        "trace:read"
    },

    Role.RESEARCHER: {
        "pattern:read", "pattern:write",
        "rank:read", "rank:write",
        "feedback:read",
        "experiment:read", "experiment:write",
        "trace:read"
    },

    Role.OPERATOR: {
        "monitoring:read",
        "drift:read",
        "guard:read",
        "experiment:read"
    },

    Role.SERVICE: {
        "ingest:write",
        "classify:write",
        "guard:write",
        "pattern:write",
        "rank:write",
        "feedback:write",
        "internal:*"
    },

    Role.READONLY: {
        "trace:read",
        "pattern:read",
        "rank:read",
        "guard:read"
    }
}

def has_permission(role: Role, permission: str) -> bool:
    """Check if role has permission."""
    perms = PERMISSIONS.get(role, set())
    return permission in perms or "*" in perms

def require_permission(permission: str):
    """Decorator for FastAPI endpoints."""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current user from request context
            request = kwargs.get('request')
            user = request.state.user

            if not has_permission(user.role, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### Service-to-Service Permissions

| Service | API Key Scope | Can Call |
|---------|--------------|----------|
| Ingestion | `ingest:write` | Storage, Retrieval |
| Danger Classifier | `classify:write` | Storage |
| FSM Router | `route:write` | Storage |
| Guards | `guard:write` | Storage |
| Pattern Extraction | `pattern:write` | Storage, Ranking |
| Pattern Ranking | `rank:write` | Storage |
| Optimization Loop | `feedback:write` | Ranking, Storage |

---

## FastAPI Integration

```python
# shared/auth/dependencies.py

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Dependency to get current authenticated user."""

    token = credentials.credentials

    # Try JWT first
    jwt_payload = jwt_auth.validate_token(token)
    if jwt_payload:
        return User(
            id=jwt_payload["sub"],
            role=Role(jwt_payload.get("role", "readonly")),
            scopes=jwt_payload.get("scope", "").split()
        )

    # Try API key
    api_key = await api_key_auth.validate_key(request)
    if api_key:
        return User(
            id=api_key.owner,
            role=Role.SERVICE,
            scopes=api_key.scopes
        )

    raise HTTPException(status_code=401, detail="Invalid authentication")

async def require_scope(scope: str):
    """Dependency factory for scope requirements."""
    async def checker(user: User = Depends(get_current_user)):
        if scope not in user.scopes:
            raise HTTPException(
                status_code=403,
                detail=f"Missing required scope: {scope}"
            )
        return user
    return checker

# Usage in endpoints
@app.post("/v1/ingest")
async def ingest(
    request: IngestionRequest,
    user: User = Depends(require_scope("ingest:write"))
):
    """Ingest traces (requires ingest:write scope)."""
    ...

@app.get("/v1/admin/users")
async def list_users(
    user: User = Depends(get_current_user)
):
    """List users (requires admin role)."""
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403)
    ...
```

---

## API Specifications by Feature

### Phase 1: Ingestion API

```yaml
authentication:
  methods:
    - API Key (service)
    - JWT (user dashboard)

  scopes:
    ingest:write: Submit traces for ingestion
    ingest:read: View ingestion status

  rate_limits:
    api_key: 1000/min
    jwt: 100/min
```

### Phase 2: Classification APIs

```yaml
authentication:
  methods:
    - API Key (service-to-service)

  scopes:
    classify:read: Read danger scores
    classify:write: Submit for classification
    route:read: Read FSM routes
    route:write: Submit for routing
    guard:read: Read guard decisions
    guard:write: Submit for guard check

  rate_limits:
    classify: 2000/min
    route: 2000/min
    guard: 5000/min
```

### Phase 3: Learning APIs

```yaml
authentication:
  methods:
    - API Key (service)
    - JWT (researchers)

  scopes:
    pattern:read: View patterns
    pattern:write: Create/modify patterns
    rank:read: View rankings
    rank:write: Request ranking
    feedback:write: Submit feedback
    experiment:read: View A/B tests
    experiment:write: Create experiments

  rate_limits:
    pattern: 500/min
    rank: 1000/min
    feedback: 10000/min (buffered)
```

---

## Audit Logging

```python
# shared/auth/audit.py

class AuditLogger:
    """Security audit logging."""

    def log_auth_event(
        self,
        event_type: str,           # "login", "access_denied", "api_key_created"
        user_id: str,
        resource: str,
        action: str,
        success: bool,
        metadata: dict = None
    ):
        """Log authentication/authorization event."""

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            "user_id": user_id,
            "resource": resource,
            "action": action,
            "success": success,
            "ip_address": metadata.get("ip_address"),
            "user_agent": metadata.get("user_agent"),
            "request_id": metadata.get("request_id"),
            "reason": metadata.get("reason") if not success else None
        }

        # Write to append-only audit log
        self._write_to_audit_log(audit_entry)

        # Alert on suspicious activity
        if not success and event_type in ["login", "access_denied"]:
            self._alert_security_team(audit_entry)

    def _write_to_audit_log(self, entry: dict):
        """Write to immutable audit store (separate DB/table)."""
        # Neo4j: Create AuditEvent node
        # Or: Write to separate audit database
        pass

# Usage
@router.post("/v1/classify")
async def classify(
    request: ClassifierRequest,
    user: User = Depends(get_current_user)
):
    # Check permission
    if not has_permission(user.role, "classify:write"):
        audit_logger.log_auth_event(
            event_type="access_denied",
            user_id=user.id,
            resource="/v1/classify",
            action="POST",
            success=False,
            metadata={"reason": "insufficient_permissions"}
        )
        raise HTTPException(status_code=403)

    # Process request
    result = await classifier.classify(request)

    # Log success
    audit_logger.log_auth_event(
        event_type="api_access",
        user_id=user.id,
        resource="/v1/classify",
        action="POST",
        success=True
    )

    return result
```

---

## Security Headers

```python
# middleware/security_headers.py

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Prevent XSS
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # CSP
        response.headers["Content-Security-Policy"] = "default-src 'self'"

        # HSTS (HTTPS only)
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Remove server info
        response.headers.pop("Server", None)

        return response
```

---

## Implementation Roadmap

### Phase 1: MVP (Week 1)

- [ ] API key generation/validation
- [ ] Basic RBAC (admin, service, readonly)
- [ ] Security headers middleware
- [ ] Audit logging

### Phase 2: Enhanced (Week 2-3)

- [ ] JWT support for user auth
- [ ] Fine-grained permissions
- [ ] Rate limiting by key/user
- [ ] API key rotation

### Phase 3: Production (Week 4)

- [ ] mTLS for service mesh
- [ ] OAuth2 integration
- [ ] Security monitoring dashboard
- [ ] Automated threat detection

---

## Security Checklist

| Check | Status | Notes |
|-------|--------|-------|
| API keys use cryptographically secure random | ⬜ | Use `secrets.token_urlsafe()` |
| Keys hashed with bcrypt/Argon2 | ⬜ | Currently SHA256, upgrade needed |
| Rate limiting per key/user | ⬜ | Redis-based sliding window |
| JWT uses RS256 (asymmetric) | ⬜ | Private key on server only |
| Token expiration enforced | ⬜ | 15 min access, 7 day refresh |
| Audit logs immutable | ⬜ | Separate database, append-only |
| Sensitive data encrypted at rest | ⬜ | Neo4j encryption enabled |
| HTTPS only (no HTTP) | ⬜ | HSTS header, redirect |
| Security headers present | ⬜ | CSP, X-Frame-Options, etc. |
| Regular key rotation | ⬜ | 90-day policy |

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-13 | AI Assistant | Initial authentication specification |
