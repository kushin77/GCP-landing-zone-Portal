# Portal Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Portal Application                        │
├──────────────────────┬──────────────────────────────────────┤
│  Frontend (React)    │        Backend (FastAPI)             │
│  - Dashboard         │        - REST APIs                   │
│  - Cost Reports      │        - Data Processing             │
│  - Compliance View   │        - Hub Integration             │
│  - Settings          │        - Pub/Sub Listeners           │
└──────────────────────┴──────────────────────────────────────┘
                 ↓
    ┌────────────────────────┐
    │   Cloud Run            │
    │  (Serverless)          │
    │  Auto-scaling          │
    │  Regional              │
    └────────────────────────┘
                 ↓
    ┌────────────────────────┐
    │   Identity-Aware Proxy │
    │  OAuth 2.0 + MFA       │
    │  TLS 1.3               │
    │  Cloud Armor DDoS      │
    └────────────────────────┘
                 ↓
        ┌────────┴────────┐
        ↓                 ↓
   ┌─────────┐        ┌──────────┐
   │ Firestore│       │ BigQuery │
   │ (NoSQL)  │       │ (Analytics)
   │ Real-time│       │ Hub costs│
   │ Audit log│       │ Resources│
   └─────────┘        └──────────┘
        ↓                 ↓
   ┌─────────────────────────┐
   │  GCP Projects (Hub)     │
   │  - Compute              │
   │  - Storage              │
   │  - Networking           │
   │  - Databases            │
   └─────────────────────────┘
```

## Components

### Frontend (React + TypeScript)

**Responsibilities:**
- User interface for Portal features
- OAuth authentication with IAP
- Real-time dashboard updates via TanStack Query
- Responsive design (desktop, tablet, mobile)
- Accessibility (WCAG 2.1 AAA)

**Technology Stack:**
- React 18 — UI framework
- TypeScript — Type safety
- Vite — Build tool (<5 min dev build)
- Tailwind CSS + shadcn/ui — Styling
- TanStack Query — State management + caching
- Zustand — Global client state
- Vitest + React Testing Library — Testing

**Key Features:**
- Dashboard with real-time cost updates
- Cost reports with filtering and exports
- Compliance status and violation tracking
- Resource inventory
- Settings and user preferences
- Dark mode support

**Deployment:**
- Build: `npm run build` → static bundle
- Hosting: Cloud Run container
- CDN: Cloud CDN for assets
- Cache: Client-side caching via TanStack Query

### Backend (FastAPI + Python)

**Responsibilities:**
- REST API endpoints for Portal UI
- Data integration from Hub
- Cost analytics and forecasting
- Compliance status aggregation
- Pub/Sub event listeners

**Technology Stack:**
- FastAPI — Web framework (async, auto-docs)
- Python 3.11 — Runtime
- Pydantic — Data validation
- Firestore Admin SDK — Database
- Google Cloud Python libraries — GCP integration
- Pytest — Testing

**Key Endpoints:**
- `GET /api/v1/costs/summary` — Monthly cost overview
- `GET /api/v1/costs/daily` — Daily cost breakdown
- `GET /api/v1/resources` — Resource inventory
- `GET /api/v1/compliance/status` — Compliance posture
- `POST /api/v1/compliance/violations/acknowledge` — Acknowledge violations

**Data Sources:**
- BigQuery (Hub cost data, resource inventory)
- Cloud Logging (audit trails)
- Pub/Sub (real-time events)
- Firestore (caching, metadata)

### Infrastructure (Terraform)

**Components:**

#### Cloud Run
- Frontend service (React SPA)
- Backend service (FastAPI REST API)
- Auto-scaling: 0-100 instances
- Memory: 1 GB (frontend), 2 GB (backend)
- CPU: 2vCPU (both)
- Regional deployment (us-central1, us-east1)

#### Identity-Aware Proxy (IAP)
- OAuth 2.0 authentication
- MFA enforcement
- TLS 1.3 encryption
- Cloud Armor DDoS protection
- Access logging

#### Networking
- VPC (custom, no internet egress)
- Cloud NAT (for outbound connections)
- Private VPC connectors (to Firestore, BigQuery)
- No public IPs

#### Security
- Service accounts (Workload Identity)
- Custom IAM roles (least privilege)
- KMS keys (CMEK for secrets)
- Firewall rules (ingress from IAP only)
- VPC Flow Logs (network monitoring)

#### Observability
- Cloud Logging (application logs, audit trails)
- Cloud Monitoring (metrics, dashboards)
- Error Reporting (exception tracking)
- Trace Agent (distributed tracing)

### Database (Firestore)

**Collections:**

#### `/users/{userId}`
```json
{
  "email": "user@example.com",
  "name": "John Doe",
  "role": "viewer",
  "preferences": {
    "dashboard_widgets": [...],
    "dark_mode": true
  },
  "created": "2026-01-01T10:00:00Z",
  "last_active": "2026-01-15T14:30:00Z"
}
```

#### `/portal_metrics/{metric_id}`
```json
{
  "date": "2026-01-15",
  "cost": 12543.21,
  "forecast": 15000.00,
  "resource_count": 234,
  "compliance_score": 99.1,
  "violations_count": 3,
  "created": "2026-01-15T00:00:00Z"
}
```

#### `/cache/{cache_key}`
```json
{
  "data": {...},
  "ttl": 300,
  "expires_at": "2026-01-15T15:10:00Z",
  "created": "2026-01-15T15:05:00Z"
}
```

**Indexes:**
- Composite: `(date, metric_type, status)`
- Composite: `(user_id, created)`
- Single: `email` (for user lookup)

**Retention:**
- User data: 7 years (compliance requirement)
- Metrics: 2 years rolling (older archived to BigQuery)
- Cache: 24 hours (auto-expire via TTL)

## Integration with Hub

### Data Flow

**1. Real-time Metrics** (via Pub/Sub)
```
Hub Cost Service → Pub/Sub Topic → Portal Subscriber → Firestore
     (hourly)         "portal-events"    (async)       (cache)
                                                            ↓
                                                       Portal UI
```

**2. Historical Data** (via BigQuery)
```
Hub BigQuery    → Portal Query    → Aggregate    → Firestore
(daily batch)     (backend API)    (analytics)    (metrics)
                                                        ↓
                                                   Dashboard
```

**3. Audit Logs** (via Cloud Logging)
```
Hub Audit Logs → Portal Query → Compliance → Portal UI
(real-time)      (backend)     Aggregation  (reports)
```

## Security Architecture

### Authentication Flow
```
User Browser
    ↓
    └→ OAuth Login (Google)
       ↓
    IAP Intercepts Request
       ↓
    OAuth Token Verified
       ↓
    Workload Identity (backend)
    Service Account Federation
       ↓
    Portal APIs (authenticated)
```

### Data Protection
- **At Rest**: CMEK encryption (Cloud KMS)
- **In Transit**: TLS 1.3 (enforced by IAP)
- **In Use**: Memory isolation (GCP)
- **Access Control**: Least privilege IAM roles

### Network Isolation
- Private VPC (no internet routing)
- Cloud NAT (outbound only, no inbound)
- Private VPC connectors (Firestore, BigQuery)
- Firewall rules (allow IAP only)
- Cloud Armor WAF (DDoS protection)

## Performance Targets

| Metric | Target | Monitoring |
|--------|--------|-----------|
| Dashboard Load | <2s | Lighthouse |
| API P95 | <100ms | Cloud Trace |
| API P99 | <500ms | Cloud Monitoring |
| Error Rate | <0.1% | Error Reporting |
| Uptime | 99.9% | Cloud Monitoring SLO |
| Cache Hit Rate | >80% | Application Metrics |

## Deployment Architecture

### Staging Environment
- Cloud Run (auto-scaling 0-50)
- Firestore (shared data, isolated by namespace)
- BigQuery (read-only access to Hub staging)
- Regional (us-central1)
- Rollback: Previous revision auto-preserved (7 days)

### Production Environment
- Cloud Run (auto-scaling 0-100)
- Firestore (geo-replicated)
- BigQuery (read-only access to Hub prod)
- Multi-regional (us-central1 + us-east1)
- Traffic split (gradual rollout)
- Blue-green deployment

## Scaling Architecture

### Horizontal Scaling
- Cloud Run: Auto-scales instances (0-100)
- Connection pooling: BigQuery + Firestore SDKs
- CDN: Cloud CDN for static assets
- Load balancing: GCP managed

### Vertical Scaling
- Database: Firestore auto-scales (pay-per-request)
- Memory: Cloud Run 1-8 GB configurable
- CPU: Cloud Run 2-8 vCPU configurable

### Caching Strategy
- Client: TanStack Query (5-minute cache)
- Browser: Service Worker (offline support)
- CDN: Static assets (1-day cache)
- Server: Firestore (hourly metrics cache)

## Disaster Recovery

- **RTO** (Recovery Time Objective): 1 hour
- **RPO** (Recovery Point Objective): 30 minutes
- **Backup**: Daily automated to GCS (Terraform-managed)
- **Failover**: Multi-region Cloud Run (automatic)
- **Database**: Geo-replicated Firestore
- **Runbook**: See [Incident Response](../operations/incident-response.md)

---

**Last Updated**: 2026-01-18
**Architecture Version**: 1.0
