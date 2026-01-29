# Portal API Reference

## Overview

The Landing Zone Portal exposes RESTful APIs for:
- Cost analytics and trend analysis
- Resource inventory and governance
- Compliance status and audit trails
- Policy violations and remediation

All APIs require OAuth 2.0 authentication via Identity-Aware Proxy (IAP).

## Authentication

### Required Headers

```
Authorization: Bearer {oauth_token}
X-GOOG-IAM-AUTHORITY-SELECTOR: googleapis.com
X-GOOG-IAM-AUTHORIZATION-TOKEN: {jwt_token}
```

### Token Acquisition

1. User logs in via Google identity
2. IAP issues OAuth token (valid 1 hour)
3. Token automatically refreshed before expiry
4. Sessions expire after 30 minutes inactivity

### Error Response

```json
{
  "error": {
    "code": 401,
    "message": "Unauthorized",
    "details": "Invalid or expired token"
  }
}
```

## Rate Limiting

- **Default**: 100 requests/minute per authenticated user
- **Burst**: Up to 1000 requests in 1-minute window
- **Backoff**: 429 status code with `Retry-After` header

## Endpoints

### Cost Analytics

#### GET /api/v1/costs/summary
Get current month cost summary.

**Response:**
```json
{
  "current_month": 12543.21,
  "previous_month": 11200.45,
  "trend": 12.0,
  "forecast_end_of_month": 15000.00,
  "budget_status": "on-track",
  "budget_remaining": 4456.79
}
```

#### GET /api/v1/costs/daily
Get daily cost breakdown for current month.

**Query Parameters:**
- `start_date`: YYYY-MM-DD (default: 1st of current month)
- `end_date`: YYYY-MM-DD (default: today)
- `group_by`: "service" | "project" | "team" (default: "service")

**Response:**
```json
{
  "data": [
    {
      "date": "2026-01-15",
      "cost": 425.32,
      "forecast": 450.00,
      "variance": -5.8
    }
  ],
  "period": {
    "start": "2026-01-01",
    "end": "2026-01-31"
  }
}
```

### Resources

#### GET /api/v1/resources
List all GCP resources across Hub projects.

**Query Parameters:**
- `type`: "compute" | "storage" | "database" | "networking" (optional)
- `status`: "active" | "idle" | "unused" (default: "active")
- `project_id`: Filter by project (optional)
- `limit`: Max 1000 (default: 100)
- `offset`: Pagination offset (default: 0)

**Response:**
```json
{
  "resources": [
    {
      "id": "projects/123/zones/us-central1-a/instances/prod-vm-1",
      "name": "prod-vm-1",
      "type": "compute.googleapis.com/Instance",
      "status": "RUNNING",
      "cost_per_month": 45.32,
      "team": "backend",
      "last_modified": "2026-01-15T10:30:00Z"
    }
  ],
  "total": 234,
  "limit": 100,
  "offset": 0
}
```

### Compliance

#### GET /api/v1/compliance/status
Get overall compliance posture.

**Response:**
```json
{
  "compliant": true,
  "compliance_score": 99.1,
  "controls_total": 325,
  "controls_compliant": 322,
  "controls_non_compliant": 3,
  "framework": "NIST 800-53",
  "last_assessed": "2026-01-15T14:30:00Z"
}
```

#### GET /api/v1/compliance/violations
Get list of compliance violations.

**Query Parameters:**
- `severity`: "critical" | "high" | "medium" (optional)
- `status`: "open" | "acknowledged" | "remediated" (default: "open")
- `limit`: Max 1000 (default: 100)

**Response:**
```json
{
  "violations": [
    {
      "id": "violation-456",
      "control": "SC-7",
      "severity": "high",
      "status": "open",
      "resource": "firewall-rule-prod",
      "description": "Public SSH access to production VM detected",
      "remediation": "Remove 0.0.0.0/0 from source ranges",
      "created": "2026-01-14T09:15:00Z",
      "due_date": "2026-01-21T23:59:59Z"
    }
  ],
  "total": 3,
  "critical_count": 0,
  "high_count": 1,
  "medium_count": 2
}
```

## Error Codes

| Code | Meaning | Resolution |
|------|---------|-----------|
| 400 | Bad request | Check request parameters |
| 401 | Unauthorized | Re-authenticate via IAP |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not found | Resource doesn't exist |
| 429 | Rate limit exceeded | Wait 60 seconds, retry |
| 500 | Server error | Contact support |
| 503 | Service unavailable | Service is deploying, retry |

## Pagination

Large result sets use cursor-based pagination:

```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJvZmZzZXQiOiAxMDB9",
    "limit": 100
  }
}
```

To get next page:
```
GET /api/v1/resources?cursor=eyJvZmZzZXQiOiAxMDB9
```

## Webhooks (Future)

Portal will support webhooks for:
- Cost threshold alerts
- Compliance violations
- Resource creation/deletion
- Policy changes

See [Webhook Documentation](./webhooks.md) for details.

## SDK

A TypeScript SDK is available on npm:

```bash
npm install @landing-zone/portal-sdk
```

Example:
```typescript
import { PortalClient } from '@landing-zone/portal-sdk';

const client = new PortalClient({
  endpoint: 'https://portal.landing-zone.io',
  token: process.env.PORTAL_TOKEN
});

const costs = await client.costs.getSummary();
console.log(`Current month: $${costs.current_month}`);
```

## Support

- 📖 [Full API Docs](https://portal-docs.landing-zone.io)
- 🐛 [Report Issues](https://github.com/kushin77/GCP-landing-zone-Portal/issues)
- 💬 Slack: #portal-api
- 📧 Email: api-support@landing-zone-portal.io

---

**API Version**: 1.0
**Last Updated**: 2026-01-18
