# API Versioning & Contract Evolution Specification

**Version**: 1.0  
**Date**: February 13, 2026  
**Scope**: All Grimoire APIs  
**Status**: Specification

---

## Overview

This document defines the API versioning strategy for Grimoire, ensuring stable client integrations while allowing the API to evolve. It covers URL versioning, deprecation policies, backward compatibility rules, and migration guides.

**Versioning Scheme**: URL-based (`/v1/`, `/v2/`)  
**Breaking Changes**: Handled via version increments  
**Deprecation Period**: 6 months minimum

---

## Versioning Strategy

### Versioning Scheme

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      API VERSIONING SCHEME                                │
└─────────────────────────────────────────────────────────────────────────┘

URL Path: https://api.grimoire.ai/v1/patterns

┌──────────────────────────────────────────────────────────────────────────┐
│  Version │ Status      │ Released   │ Deprecated │ Sunset    │ Support   │
├──────────┼─────────────┼────────────┼────────────┼───────────┼──────────┤
│  v1      │ ACTIVE      │ 2026-01-01 │ TBD        │ TBD       │ Full     │
│  v2      │ BETA        │ 2026-06-01 │ -          │ -         │ Full     │
│  v1alpha │ DEPRECATED  │ 2025-06-01 │ 2026-01-01 │ 2026-07-01│ Limited  │
└──────────┴─────────────┴────────────┴────────────┴───────────┴──────────┘

URL Structure:
/v1/                          → Production stable (v1.x.x)
/v2/                          → Production stable (v2.x.x)
/v1beta/                      → Beta (v1.0.0-beta.x)
/v1alpha/                     → Alpha (experimental)
/v1/patterns                  → Resource path
/v1/patterns/{id}             → Resource with ID
/v1/patterns:action           → Custom action (colon syntax)
```

### Version Lifecycle

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                      VERSION LIFECYCLE                                    │
└─────────────────────────────────────────────────────────────────────────┘

       ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
       │  ALPHA   │────▶│  BETA    │────▶│ STABLE   │────▶│DEPRECATED│
       └──────────┘     └──────────┘     └──────────┘     └──────────┘
            │                │                │                │
            │                │                │                │
       Experimental      Preview         Production      Maintenance
            │                │                │                │
       - Unstable API      - Stable        - Fully          - Security
       - May change       - Feature       supported        - Critical bugs
         without notice     complete       - Backward         only
                                              compatible    - 6 month
                                                             window
```

---

## API Versioning Implementation

### Version Middleware

```python
# core/api_versioning.py
from typing import Optional, Dict, Callable
from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class APIVersion(str, Enum):
    """Supported API versions."""
    V1 = "v1"
    V1BETA = "v1beta"
    V1ALPHA = "v1alpha"
    V2 = "v2"


class VersionStatus(str, Enum):
    """Version lifecycle status."""
    ACTIVE = "active"
    BETA = "beta"
    ALPHA = "alpha"
    DEPRECATED = "deprecated"
    SUNSET = "sunset"


class APIVersionInfo(BaseModel):
    """Information about an API version."""
    version: str
    status: VersionStatus
    released_at: datetime
    deprecated_at: Optional[datetime] = None
    sunset_at: Optional[datetime] = None
    docs_url: str
    changelog_url: str

    class Config:
        use_enum_values = True


class VersionConfig:
    """Configuration for API versioning."""

    # Version registry
    VERSIONS: Dict[str, APIVersionInfo] = {
        "v1": APIVersionInfo(
            version="v1",
            status=VersionStatus.ACTIVE,
            released_at=datetime(2026, 1, 1),
            docs_url="https://docs.grimoire.ai/v1",
            changelog_url="https://docs.grimoire.ai/v1/changelog"
        ),
        "v1beta": APIVersionInfo(
            version="v1beta",
            status=VersionStatus.BETA,
            released_at=datetime(2026, 6, 1),
            docs_url="https://docs.grimoire.ai/v1beta",
            changelog_url="https://docs.grimoire.ai/v1beta/changelog"
        ),
        "v1alpha": APIVersionInfo(
            version="v1alpha",
            status=VersionStatus.DEPRECATED,
            released_at=datetime(2025, 6, 1),
            deprecated_at=datetime(2026, 1, 1),
            sunset_at=datetime(2026, 7, 1),
            docs_url="https://docs.grimoire.ai/v1alpha",
            changelog_url="https://docs.grimoire.ai/v1alpha/changelog"
        ),
    }

    # Default version for clients not specifying
    DEFAULT_VERSION = "v1"

    # Supported versions (excludes sunset)
    SUPPORTED_VERSIONS = ["v1", "v1beta"]

    # Deprecation settings
    DEPRECATION_WARNING_HEADER = "Deprecation"
    DEPRECATION_SUNSET_HEADER = "Sunset"
    DEPRECATION_LINK_HEADER = "Link"


class VersionMiddleware:
    """Middleware to handle API version extraction and validation."""

    def __init__(self, app, config: VersionConfig):
        self.app = app
        self.config = config

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Extract version from path
        path = scope.get("path", "/")
        version = self._extract_version(path)

        # Validate version
        if version and version not in self.config.VERSIONS:
            await self._send_error(send, "Unsupported API version")
            return

        # Add version to scope for handlers
        scope["api_version"] = version or self.config.DEFAULT_VERSION

        # Process request
        await self.app(scope, receive, send)

    def _extract_version(self, path: str) -> Optional[str]:
        """Extract version from URL path."""
        parts = path.strip("/").split("/")
        if parts and parts[0].startswith("v"):
            return parts[0]
        return None

    async def _send_error(self, send, message: str, status: int = 400):
        """Send error response."""
        # Implementation for error response
        pass


class VersionedRouter:
    """Router that supports multiple API versions."""

    def __init__(self, prefix: str = "", config: VersionConfig = None):
        self.prefix = prefix
        self.config = config or VersionConfig()
        self.routers: Dict[str, APIRouter] = {}

        # Create router for each version
        for version in self.config.SUPPORTED_VERSIONS:
            self.routers[version] = APIRouter(prefix=f"/{version}{prefix}")

    def add_route(
        self,
        path: str,
        endpoint: Callable,
        methods: List[str] = ["GET"],
        version: str = None
    ):
        """Add route to specified version(s)."""
        versions = [version] if version else self.config.SUPPORTED_VERSIONS

        for v in versions:
            if v in self.routers:
                self.routers[v].add_api_route(path, endpoint, methods=methods)

    def get_router(self, version: str) -> APIRouter:
        """Get router for specific version."""
        return self.routers.get(version, self.routers[self.config.DEFAULT_VERSION])
```

---

## Deprecation Policy

### Deprecation Types

```python
# core/deprecation.py
from typing import Optional, List
from enum import Enum
from datetime import datetime, timedelta


class DeprecationType(str, Enum):
    """Types of deprecation."""
    ENDPOINT = "endpoint"           # Entire endpoint
    FIELD = "field"                  # Request/response field
    PARAMETER = "parameter"          # Query parameter
    RESPONSE_CODE = "response_code" # HTTP status code
    AUTH_METHOD = "auth_method"      # Authentication method
    FORMAT = "format"               # Request/response format


class DeprecationSeverity(str, Enum):
    """Severity of deprecation impact."""
    LOW = "low"       # Informational, no action needed
    MEDIUM = "medium" # Plan to migrate within 3 months
    HIGH = "high"    # Migrate within 1 month
    CRITICAL = "critical"  # Immediate migration required


class DeprecationInfo(BaseModel):
    """Information about a deprecation."""
    id: str
    type: DeprecationType
    severity: DeprecationSeverity

    # What is deprecated
    endpoint: Optional[str] = None
    field: Optional[str] = None
    parameter: Optional[str] = None

    # Timeline
    announced_at: datetime
    deprecated_at: datetime
    sunset_at: datetime

    # Migration guidance
    replacement: Optional[str] = None
    migration_guide_url: Optional[str] = None
    alternative: Optional[str] = None

    class Config:
        use_enum_values = True


class DeprecationManager:
    """Manage API deprecations and communicate to clients."""

    def __init__(self, config: VersionConfig):
        self.config = config
        self.deprecations: Dict[str, DeprecationInfo] = {}

    def register_deprecation(self, deprecation: DeprecationInfo):
        """Register a new deprecation."""
        self.deprecations[deprecation.id] = deprecation

    def get_active_deprecations(self) -> List[DeprecationInfo]:
        """Get all currently active deprecations."""
        now = datetime.utcnow()
        return [
            d for d in self.deprecations.values()
            if d.deprecated_at <= now < d.sunset_at
        ]

    def check_deprecation(
        self,
        version: str,
        endpoint: str,
        field: str = None,
        parameter: str = None
    ) -> Optional[DeprecationInfo]:
        """Check if something is deprecated."""
        for deprecation in self.get_active_deprecations():
            if deprecation.endpoint == endpoint:
                if field and deprecation.field == field:
                    return deprecation
                if parameter and deprecation.parameter == parameter:
                    return deprecation
                return deprecation
        return None

    def get_deprecation_headers(
        self,
        deprecation: DeprecationInfo
    ) -> dict:
        """Generate deprecation headers per RFC 8594."""
        now = datetime.utcnow()
        days_until_sunset = (deprecation.sunset_at - now).days

        return {
            "Deprecation": f" {deprecation.endpoint}",
            "Sunset": deprecation.sunset_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
            "Link": f'<{deprecation.migration_guide_url}>; rel="deprecation"',
            "Warning": f'299 - "{deprecation.endpoint} is deprecated. Migrate by {deprecation.sunset_at.strftime("%Y-%m-%d")}"'
        }
```

---

## Breaking vs Non-Breaking Changes

### Classification Rules

```text
┌─────────────────────────────────────────────────────────────────────────┐
│                 BREAKING VS NON-BREAKING CHANGES                        │
└─────────────────────────────────────────────────────────────────────────┘

NON-BREAKING (Can ship in minor version):
┌────────────────────────────────────────────────────────────────────────┐
│ ✓ Adding new optional parameters                                       │
│ ✓ Adding new response fields                                           │
│ ✓ Adding new endpoints                                                │
│ ✓ Adding new enum values (client ignores unknown)                     │
│ ✓ Changing field order in response                                    │
│ ✓ Adding new headers                                                  │
│ ✓ Removing undocumented fields                                        │
│ ✓ Fixing validation errors (more permissive)                         │
│ ✓ Adding pagination to existing endpoints                             │
│ ✓ Adding new query parameters                                         │
└────────────────────────────────────────────────────────────────────────┘

BREAKING (Requires major version bump):
┌────────────────────────────────────────────────────────────────────────┐
│ ✗ Removing or renaming endpoints                                      │
│ ✗ Removing or renaming fields                                          │
│ ✗ Removing or renaming parameters                                     │
│ ✗ Changing response format (JSON to XML)                              │
│ ✗ Changing field types (string to int)                               │
│ ✗ Changing required to optional                                       │
│ ✗ Adding required parameters                                           │
│ ✗ Removing enum values                                                 │
│ ✗ Changing authentication requirements                                │
│ ✗ Changing error response codes                                        │
│ ✗ Reducing rate limits                                                 │
│ ✗ Changing URL structure                                               │
└────────────────────────────────────────────────────────────────────────┘

POTENTIALLY BREAKING (Review carefully):
┌────────────────────────────────────────────────────────────────────────┐
│ ⚠ Changing validation rules (stricter)                                │
│ ⚠ Changing default values                                             │
│ ⚠ Changing field length limits                                        │
│ ⚠ Adding new required header                                          │
│ ⚠ Changing rate limits                                                │
│ ⚠ Adding new authentication requirement                                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## Response Headers

### Version Information Headers

```python
# middleware/version_headers.py
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class VersionHeadersMiddleware(BaseHTTPMiddleware):
    """Add API version headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        # Add version header
        version = request.scope.get("api_version", "v1")
        response.headers["X-API-Version"] = version
        response.headers["X-API-Version-Latest"] = "v1"

        # Add deprecation warnings if applicable
        deprecation = getattr(request.state, "deprecation", None)
        if deprecation:
            response.headers["Deprecation"] = f"true"
            response.headers["Sunset"] = deprecation.sunset_at.isoformat()

        return response


# Example headers in response:
#
# X-API-Version: v1
# X-API-Version-Latest: v1
# X-RateLimit-Limit: 1000
# X-RateLimit-Remaining: 999
# Deprecation: true
# Sunset: 2026-07-01T00:00:00Z
# Link: <https://docs.grimoire.ai/v2/migration>; rel="deprecation"
# Warning: 299 - "GET /v1/patterns/rank is deprecated"
```

---

## Version Negotiation

### Client Version Selection

```python
# core/version_negotiation.py
from typing import Optional, List
from fastapi import Header, HTTPException


class VersionNegotiator:
    """Handle client version selection."""

    # Priority order for version selection
    # 1. Path (most explicit)
    # 2. Accept-Version header
    # 3. Default to latest stable

    @staticmethod
    def negotiate_version(
        accept_version: Optional[str] = Header(None, alias="Accept-Version"),
        api_version: Optional[str] = None
    ) -> str:
        """
        Negotiate API version with client.

        Client can specify version via:
        1. URL path: /v1/patterns
        2. Accept-Version header: Accept-Version: v1
        """
        # Path takes precedence
        if api_version:
            return api_version

        # Accept-Version header
        if accept_version:
            # Handle version ranges
            if accept_version.startswith("v"):
                # Validate and return
                if accept_version in ["v1", "v1beta", "v1alpha", "v2"]:
                    return accept_version
                # Handle loose matching
                if accept_version.startswith("v1"):
                    return "v1"

        # Default
        return "v1"


def version_availability_header(supported_versions: List[str]) -> dict:
    """Generate Availability-Version header."""
    return {
        "Accept-Patch": "application/json",
        "Accept-Version": "; ".join(supported_versions),
        "X-API-Versions-Available": ", ".join(supported_versions),
    }
```

---

## Changelog & Documentation

### Changelog Format

```markdown
# API Changelog

## v1.3.0 - 2026-02-01 (Unreleased)

### Added
- `GET /v1/patterns/{id}/versions` - Get pattern version history
- `POST /v1/patterns/bulk` - Bulk pattern operations

### Changed
- `GET /v1/patterns` - Added pagination support
- Response now includes `total_count` for list endpoints

### Deprecated (will be removed in v2.0)
- `GET /v1/patterns/rank` → Use `POST /v1/rank`
- Field `score` → Use `ranking_score`

### Fixed
- Fixed race condition in pattern creation

---

## v1.2.0 - 2026-01-15

### Added
- `GET /v1/health` - Health check endpoint
- Rate limit headers on all responses

### Changed
- Increased rate limit from 100 to 1000 req/min

---

## v1.1.0 - 2026-01-01

### Added
- Initial production release
```

### Version Discovery Endpoint

```python
# routes/versionDiscovery.py
@router.get("/versions")
async def get_api_versions():
    """
    Get all available API versions.

    Returns:
        - supported: List of actively supported versions
        - deprecated: List of deprecated versions (still functional)
        - sunset: List of sunset versions (removed)
    """
    return {
        "supported": [
            {
                "version": "v1",
                "status": "active",
                "released": "2026-01-01",
                "docs_url": "https://docs.grimoire.ai/v1"
            },
            {
                "version": "v1beta",
                "status": "beta", 
                "released": "2026-06-01",
                "docs_url": "https://docs.grimoire.ai/v1beta"
            }
        ],
        "deprecated": [
            {
                "version": "v1alpha",
                "status": "deprecated",
                "deprecated": "2026-01-01",
                "sunset": "2026-07-01",
                "docs_url": "https://docs.grimoire.ai/v1alpha",
                "migration_guide": "https://docs.grimoire.ai/v1beta/migration"
            }
        ],
        "current_stable": "v1",
        "default_version": "v1"
    }
```

---

## Migration Guide

### v1 to v2 Migration

````markdown
# Migration Guide: v1 → v2

## Breaking Changes

### 1. Response Format Changes

**Before (v1)**:
```json
{
  "patterns": [...],
  "total": 100
}
````

**After (v2)**:

```json
{
  "data": [...],
  "pagination": {
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "meta": {
    "version": "v2"
  }
}
```

### 2. Field Renames

| v1 Field | v2 Field | Migration |
|----------|----------|-----------|
| `score` | `ranking_score` | Automatic alias in v1 |
| `total` | `pagination.total` | Use `pagination.total` |
| `id` | `pattern_id` | Field renamed |
| `domain` | `problem_domain` | Field renamed |

### 3. Endpoint Changes

| v1 Endpoint | v2 Endpoint | Notes |
|-------------|--------------|-------|
| `GET /v1/patterns/rank` | `POST /v2/rank` | POST required |
| `GET /v1/patterns/{id}` | `GET /v2/patterns/{id}` | Same method |
| `POST /v1/patterns` | `POST /v2/patterns` | Same |

### 4. Authentication Changes

| v1 | v2 |
|----|----|
| API Key header: `X-API-Key` | `Authorization: Bearer {key}` |
| JWT optional | JWT required for write operations |

## Migration Steps

1. **Update headers**:

   ```python
   # Before
   headers = {"X-API-Key": "your-key"}

   # After  
   headers = {"Authorization": "Bearer your-key"}
   ```

2. **Update response parsing**:

   ```python
   # Before
   patterns = response["patterns"]
   total = response["total"]

   # After
   patterns = response["data"]
   pagination = response["pagination"]
   total = pagination["total"]
   ```

3. **Update field names**:

   ```python
   # Before
   pattern["score"]

   # After
   pattern["ranking_score"]
   ```

## Compatibility Mode

v1 requests with header `Accept-Version: v1.0-compat` will receive v1-style responses:

```http
GET /v2/patterns Accept-Version: v1.0-compat

Response:
{
  "patterns": [...],  // v1 format
  "total": 100       // v1 format
}
```

**Compat mode available for 6 months after v2 release.**

```text

---

## Error Handling

### Versioning Error Responses

```python
# middleware/version_errors.py
from fastapi import HTTPException


class VersioningErrors:
    """Standard error responses for versioning issues."""

    @staticmethod
    def unsupported_version(supported: List[str]) -> HTTPException:
        """Version not supported."""
        return HTTPException(
            status_code=400,
            detail={
                "error": "UnsupportedVersion",
                "message": f"API version not supported. Supported: {', '.join(supported)}",
                "supported_versions": supported,
                "discovery_url": "/v1/versions"
            },
            headers={
                "Accept-Patch": "application/json",
                "Accept-Version": "; ".join(supported)
            }
        )

    @staticmethod
    def version_deprecated(deprecation: DeprecationInfo) -> HTTPException:
        """Endpoint is deprecated."""
        return HTTPException(
            status_code=410,  # Gone
            detail={
                "error": "EndpointDeprecated",
                "message": f"This endpoint is deprecated. {deprecation.alternative}",
                "deprecated_at": deprecation.deprecated_at.isoformat(),
                "sunset_at": deprecation.sunset_at.isoformat(),
                "migration_guide": deprecation.migration_guide_url
            },
            headers={
                "Deprecation": f'"{deprecation.endpoint}"',
                "Sunset": deprecation.sunset_at.strftime("%a, %d %b %Y %H:%M:%S GMT"),
                "Link": f'<{deprecation.migration_guide_url}>; rel="deprecation"; type="text/html"'
            }
        )

    @staticmethod
    def version_sunset(deprecation: DeprecationInfo) -> HTTPException:
        """Version has been sunset."""
        return HTTPException(
            status_code=410,
            detail={
                "error": "VersionSunset",
                "message": "This API version has been sunset and is no longer available.",
                "sunset_at": deprecation.sunset_at.isoformat(),
                "current_version": "v1"
            }
        )
```

---

## Testing

### Versioning Tests

```python
# tests/unit/test_api_versioning.py
import pytest
from unittest.mock import Mock


class TestAPIVersioning:
    """Test API versioning functionality."""

    def test_extract_version_from_path(self):
        """Verify version extraction from URL."""
        negotiator = VersionNegotiator()

        assert negotiator.negotiate_version(api_version="v1") == "v1"
        assert negotiator.negotiate_version(api_version="v2") == "v2"

    def test_version_negotiation_accept_header(self):
        """Verify Accept-Version header parsing."""
        negotiator = VersionNegotiator()

        assert negotiator.negotiate_version(accept_version="v1") == "v1"
        assert negotiator.negotiate_version(accept_version="v1beta") == "v1beta"

    def test_default_version(self):
        """Verify default version when none specified."""
        negotiator = VersionNegotiator()

        assert negotiator.negotiate_version() == "v1"

    def test_deprecation_headers(self):
        """Verify deprecation headers are correct."""
        manager = DeprecationManager(VersionConfig())

        deprecation = DeprecationInfo(
            id="dep_001",
            type=DeprecationType.ENDPOINT,
            severity=DeprecationSeverity.MEDIUM,
            endpoint="/v1/patterns/rank",
            announced_at=datetime(2026, 1, 1),
            deprecated_at=datetime(2026, 2, 1),
            sunset_at=datetime(2026, 7, 1),
            replacement="/v1/rank",
            migration_guide_url="https://docs.grimoire.ai/v1/rank-migration"
        )

        headers = manager.get_deprecation_headers(deprecation)

        assert "Deprecation" in headers
        assert "Sunset" in headers
        assert "Link" in headers
        assert "rel=\"deprecation\"" in headers["Link"]

    def test_breaking_change_detection(self):
        """Verify breaking changes are correctly classified."""
        changes = [
            ("add_field", False),       # Non-breaking
            ("remove_endpoint", True),  # Breaking
            ("add_required_param", True),  # Breaking
            ("change_type", True),      # Breaking
            ("add_optional_param", False),  # Non-breaking
        ]

        for change, expected_break in changes:
            # Test classification logic
            pass


class TestVersionNegotiation:
    """Test version negotiation scenarios."""

    def test_path_version_priority(self):
        """Path version takes precedence over header."""
        negotiator = VersionNegotiator()

        result = negotiator.negotiate_version(
            accept_version="v1",
            api_version="v2"
        )

        assert result == "v2"

    def test_unsupported_version_error(self):
        """Verify error for unsupported version."""
        with pytest.raises(HTTPException) as exc_info:
            raise VersioningErrors.unsupported_version(["v1", "v2"])

        assert exc_info.value.status_code == 400
        assert "UnsupportedVersion" in exc_info.value.detail["error"]
```

---

## Implementation Checklist

- [ ] Version middleware with path extraction
- [ ] Version registry with lifecycle status
- [ ] Deprecation registration and tracking
- [ ] Deprecation headers (Deprecation, Sunset, Link)
- [ ] Version discovery endpoint (`GET /versions`)
- [ ] Accept-Version header negotiation
- [ ] Backward compatibility layer
- [ ] Changelog format and automation
- [ ] Migration guide documentation
- [ ] Version-specific error responses
- [ ] Unit tests for all scenarios
- [ ] Integration tests for version transitions
