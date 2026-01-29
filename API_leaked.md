# Portal API Reference

## Overview

The GCP Landing Zone Portal provides a unified control plane for infrastructure, governance, and monitoring across GCP organizations and projects. This document describes the public API surface, versioning strategy, and integration patterns.

## API Endpoints

### Authentication Service

**Base URL:** `https://portal.example.com/api/v1/auth`

#### Login
- **Method**: `POST /login`
- **Description**: Authenticate user and receive JWT token
- **Request**:
  ```json
  {
    "email": "user@example.com",
    "password": "secure_password"
  }
  ```
- **Response**:
  ```json
  {
    "token": "eyJhbGciOiJIUzI1NiIs...",
    "expires_in": 3600,
    "user": {
      "id": "user-123",
      "email": "user@example.com",
      "roles": ["viewer", "editor"]
    }
  }
  ```
- **Status Codes**: `200` (success), `401` (invalid credentials), `429` (rate limited)

#### Logout
- **Method**: `POST /logout`
- **Description**: Revoke JWT token
- **Headers**: `Authorization: Bearer <token>`
- **Response**: `204 No Content`

### Health Check

**Base URL:** `https://portal.example.com/api/v1`

#### System Health
- **Method**: `GET /health`
- **Description**: Check system health status
- **Response**:
  ```json
  {
    "status": "healthy",
    "timestamp": "2026-01-19T12:00:00Z",
    "components": {
      "database": "healthy",
      "cache": "healthy",
      "compute": "healthy"
    }
  }
  ```

### Projects API

**Base URL:** `https://portal.example.com/api/v1/projects`

#### List Projects
- **Method**: `GET /`
- **Description**: List all projects accessible to authenticated user
- **Query Parameters**:
  - `page` (integer, default: 1): Pagination offset
  - `limit` (integer, default: 10): Items per page
  - `filter` (string): Optional filter expression
- **Response**:
  ```json
  {
    "data": [
      {
        "id": "proj-001",
        "name": "Production Network",
        "organization_id": "org-123",
        "created_at": "2025-01-01T00:00:00Z",
        "status": "active"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 10,
      "total": 42
    }
  }
  ```

#### Get Project Details
- **Method**: `GET /{projectId}`
- **Description**: Retrieve specific project with full details
- **Response**:
  ```json
  {
    "id": "proj-001",
    "name": "Production Network",
    "organization_id": "org-123",
    "labels": {
      "environment": "prod",
      "team": "platform",
      "cost_center": "eng-ops"
    },
    "status": "active",
    "created_at": "2025-01-01T00:00:00Z",
    "updated_at": "2026-01-19T10:30:00Z"
  }
  ```

### Resources API

**Base URL:** `https://portal.example.com/api/v1/resources`

#### List Resources
- **Method**: `GET /`
- **Description**: List infrastructure resources (VPCs, VMs, databases, etc.)
- **Query Parameters**:
  - `type` (string): Filter by resource type (vpc, instance, database)
  - `project_id` (string): Filter by project
  - `status` (string): Filter by status (active, stopped, error)

#### Get Resource Details
- **Method**: `GET /{resourceId}`
- **Response**: Detailed resource information including metrics and dependencies

## Authentication

### JWT Token Structure

Tokens are signed JWTs containing user identity and permissions:

```
Header:  {
  "alg": "HS256",
  "typ": "JWT"
}

Payload: {
  "sub": "user-123",
  "email": "user@example.com",
  "roles": ["viewer"],
  "iat": 1234567890,
  "exp": 1234571490
}
```

### Authorization

Include token in request headers:
```
Authorization: Bearer <token>
```

### Token Refresh

Tokens expire after 1 hour. Refresh endpoints:
- **Method**: `POST /auth/refresh`
- **Headers**: `Authorization: Bearer <expired_token>`

## API Versioning Strategy

### Version Format

APIs use semantic versioning: `v{major}.{minor}`

- **v1**: Current stable version
- **v1.x**: Backward-compatible feature additions
- **v2**: Breaking changes (separate endpoint)

### Deprecation Policy

Deprecated endpoints follow sunset procedure:
1. **Announcement**: 6-month advance notice via changelog
2. **Deprecation**: Endpoint returns `Deprecation` header
3. **Sunset**: Original endpoint removed, clients must use replacement
4. **Example**:
   ```
   Deprecation: true
   Sunset: Wed, 21 Dec 2025 23:59:59 GMT
   Link: </api/v2/projects>; rel="successor-version"
   ```

### Backward Compatibility

- Response schemas are additive only (no breaking field removal)
- Optional fields may be added without version bump
- Field ordering not guaranteed
- Pagination and filtering may change between versions

## Error Handling

### Standard Error Response

```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid",
    "details": [
      {
        "field": "email",
        "issue": "Invalid email format"
      }
    ],
    "request_id": "req-abc123"
  }
}
```

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| `200` | Success | API call completed successfully |
| `201` | Created | Resource created |
| `204` | No Content | Success with no response body |
| `400` | Bad Request | Invalid request parameters |
| `401` | Unauthorized | Missing or invalid token |
| `403` | Forbidden | User lacks permission |
| `404` | Not Found | Resource doesn't exist |
| `429` | Rate Limited | Too many requests |
| `500` | Server Error | Internal server error |

## Rate Limiting

- **Limit**: 1000 requests per hour per user
- **Headers**:
  ```
  X-RateLimit-Limit: 1000
  X-RateLimit-Remaining: 987
  X-RateLimit-Reset: 1234567890
  ```

## Integration Examples

### Python Client

```python
import requests
from datetime import datetime, timedelta

class PortalClient:
    def __init__(self, base_url, email, password):
        self.base_url = base_url
        self.session = requests.Session()
        self.token = None
        self.token_expires = None
        self.login(email, password)
    
    def login(self, email, password):
        resp = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            json={"email": email, "password": password}
        )
        data = resp.json()
        self.token = data['token']
        self.token_expires = datetime.now() + timedelta(seconds=data['expires_in'])
        self.session.headers['Authorization'] = f"Bearer {self.token}"
    
    def get_projects(self):
        return self.session.get(f"{self.base_url}/api/v1/projects").json()

# Usage
client = PortalClient("https://portal.example.com", "user@example.com", "password")
projects = client.get_projects()
```

### cURL Examples

```bash
# Login
TOKEN=$(curl -s -X POST https://portal.example.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}' \
  | jq -r '.token')

# List projects
curl -s -X GET https://portal.example.com/api/v1/projects \
  -H "Authorization: Bearer $TOKEN" | jq '.'

# Get health
curl -s https://portal.example.com/api/v1/health | jq '.'
```

## Support & Documentation

- **API Docs**: https://portal.example.com/docs
- **Status Page**: https://status.example.com
- **Support**: api-support@example.com
- **Issues**: https://github.com/kushin77/GCP-landing-zone-Portal/issues

---

**Version**: 1.0  
**Last Updated**: 2026-01-19  
**Status**: Production
