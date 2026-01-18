# Landing Zone Portal

> Control plane for infrastructure self-service, cost transparency, and compliance management.

Enterprise-grade user-facing application for the GCP Landing Zone. Independent deployment, secure integration with Hub infrastructure.

## Quick Start

```bash
./run.sh              # Interactive menu
./run.sh dev          # Start local development
./run.sh test         # Run all tests
./run.sh security     # Run security scans
./run.sh deploy       # Deploy to staging
```

## What Is This?

The Landing Zone Portal is a **separate Spoke repository** that provides:

- **Dashboard** — Real-time cost, compliance status, resource overview
- **Resource Browser** — Search/filter VPCs, projects, service accounts
- **Self-Service Forms** — Request VMs, projects, database instances
- **Admin Console** — Cost controls, compliance policies, approvals
- **Audit Logs** — Complete action trail for compliance audits

## Architecture

```
User (OAuth 2.0 + MFA via IAP)
    ↓
Frontend (React) + Backend (FastAPI)
    ↓ (Workload Identity)
Hub Services (read-only)
├─ APIs, BigQuery, Pub/Sub, Secrets
└─ No Infrastructure changes from Portal
```

**Key**: Portal is **read-only** to Hub infrastructure. All requests go through approval workflows.

## Quick Links

- **[API.md](docs/API.md)** — REST endpoints & authentication
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** — System design & diagrams
- **[DEPLOYMENT.md](docs/DEPLOYMENT.md)** — How to deploy
- **[RUNBOOKS.md](docs/RUNBOOKS.md)** — Operational procedures
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Development guide
- **[SECURITY.md](SECURITY.md)** — Security policies

## Technology Stack

| Layer    | Technology                       |
| -------- | -------------------------------- |
| Frontend | React 18 + TypeScript + Vite     |
| Backend  | FastAPI (Python)                 |
| Database | Firestore (NoSQL)                |
| Hosting  | Cloud Run (serverless)           |
| Auth     | OAuth 2.0 + Identity-Aware Proxy |
| Secrets  | Secret Manager + Cloud KMS       |
| CI/CD    | Cloud Build                      |

## Folder Structure

```
gcp-landing-zone-portal/
├── frontend/                  (React web app)
├── backend/                   (FastAPI API server)
├── terraform/                 (Portal infrastructure)
├── scripts/                   (Automation & deployment)
├── docs/                      (Documentation)
├── run.sh                     (Entry point)
├── pmo.yaml                   (Project metadata)
└── cloudbuild.yaml           (CI/CD pipeline)
```

## Development

### Prerequisites

- Node.js 20+ (frontend)
- Python 3.11+ (backend)
- Terraform 1.7+ (infrastructure)
- Docker (for local testing)
- GCP Project with Portal SA credentials

### Local Setup

```bash
# Clone
git clone https://github.com/kushin77/GCP-landing-zone-Portal.git
cd GCP-landing-zone-Portal

# Start everything
./run.sh dev

# Frontend runs: http://localhost:5173
# Backend API: http://localhost:8000
# Docs: http://localhost:8000/docs (Swagger)
```

### Testing

```bash
./run.sh test
# Runs frontend unit tests + backend pytest
# Target: >80% code coverage
```

## Deployment

### Staging

```bash
./run.sh deploy
# Deploys to Cloud Run (staging)
# Automatically runs E2E tests
```

### Production

```bash
# Merge to main branch
git push origin main
# Cloud Build automatically:
# 1. Tests + security scans
# 2. Deploys to staging
# 3. E2E tests
# 4. Waits for manual approval
# 5. Deploys to production
```

## Security

✅ **Authentication**: OAuth 2.0 + MFA (IAP)
✅ **Encryption**: CMEK (Cloud KMS), TLS 1.3
✅ **Identity**: Workload Identity (no service account keys)
✅ **Network**: VPC Service Controls (isolated from Hub)
✅ **Audit Trail**: Cloud Logging (immutable, 7-year retention)

See [SECURITY.md](SECURITY.md) for details.

## Support

- **Issues**: GitHub Issues
- **Questions**: #portal-dev Slack
- **On-Call**: PagerDuty (see SECURITY.md)

## Compliance

- **NIST Controls**: IA-2, AC-2, SC-7, SC-28, AU-2, SI-4
- **FedRAMP**: Pre-authorization ready
- **Cost Tracking**: Via PMO labels
- **Audit**: Complete action trail

See [docs/compliance/](docs/compliance/) for more.

## Status

| Metric          | Status                                           |
| --------------- | ------------------------------------------------ |
| **Uptime**      | 99.9% SLO                                        |
| **Coverage**    | >80% code                                        |
| **Security**    | 0 critical issues                                |
| **Status Page** | [status.example.com](https://status.example.com) |

## License

Apache 2.0 — See LICENSE file

---

**Owner**: Platform Engineering
**Repo**: https://github.com/kushin77/GCP-landing-zone-Portal
**Status**: Active Development
**Last Updated**: 2026-01-18
