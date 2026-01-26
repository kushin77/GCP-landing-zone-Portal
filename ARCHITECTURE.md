# Portal Architecture

## Overview

The GCP Landing Zone Portal is a unified control plane for infrastructure governance, monitoring, and management across GCP organizations. It implements a 5-layer architecture pattern aligned with the enterprise landing zone framework.

## 5-Layer Architecture

### Layer 1: Foundation (01-foundation)

**Purpose**: Bootstrap GCP organization, enable APIs, establish CI/CD pipeline

**Components**:
- GCP Project and Billing Setup
- Organization Policies
- Service Accounts and IAM base roles
- Cloud Build CI/CD pipeline
- Terraform state backend (Cloud Storage)

**Terraform Modules**:
- `modules/gcp-project` - Project creation and configuration
- `modules/service-account` - Service account provisioning
- `modules/billing` - Billing account setup
- `modules/cloud-build` - CI/CD configuration

**Dependencies**: None (first layer)

### Layer 2: Network (02-network)

**Purpose**: Establish secure network infrastructure with VPCs, subnets, and connectivity

**Components**:
- VPC Networks (production, staging, development)
- Subnets and IP allocation
- Cloud Firewall rules and policies
- Cloud NAT for outbound internet access
- Cloud Interconnect (optional for on-premises connectivity)
- DNS zones and records

**Directory Structure**:
```
02-network/
├── vpc/              # VPC definitions
├── firewall/         # Firewall rules
├── nat/              # Cloud NAT configuration
└── dns/              # DNS configuration
```

**Terraform Modules**:
- `modules/network/vpc` - VPC creation
- `modules/network/firewall` - Firewall policies
- `modules/network/nat` - Cloud NAT setup

**Dependencies**: Layer 01 (foundation)

### Layer 3: Security (03-security)

**Purpose**: Implement identity, access control, compliance, and secrets management

**Components**:
- IAM roles and bindings (least-privilege)
- Service accounts for applications
- Secrets Manager for sensitive data
- Cloud Audit Logging
- VPC Service Controls (optional)
- Binary Authorization policies
- Custom Organization Policies

**Directory Structure**:
```
03-security/
├── iam/              # IAM roles and bindings
├── secrets/          # Secrets management
├── compliance/       # Compliance policies
└── audit/            # Audit logging
```

**Terraform Modules**:
- `modules/security/iam` - IAM policies
- `modules/security/secrets` - Secrets Manager
- `modules/security/kms` - Encryption keys

**Dependencies**: Layers 01, 02 (foundation, network)

### Layer 4: Workloads (04-workloads)

**Purpose**: Deploy application infrastructure and services

**Components**:
- Backend API (FastAPI on Cloud Run)
- Frontend SPA (React on Cloud Storage + CDN)
- Databases (Cloud SQL, Firestore)
- Message queues (Pub/Sub)
- Cache layers (Memorystore)

**Directory Structure**:
```
04-workloads/
├── api/              # Backend API service
├── frontend/         # Frontend SPA
├── database/         # Database infrastructure
└── services/         # Supporting services
```

**Terraform Modules**:
- `modules/workloads/cloud-run` - Containerized services
- `modules/workloads/database` - Database setup
- `modules/workloads/pubsub` - Message queues

**Dependencies**: Layers 01, 02, 03 (foundation, network, security)

### Layer 5: Observability (05-observability)

**Purpose**: Monitoring, logging, alerting, and cost tracking

**Components**:
- Cloud Logging (centralized log collection)
- Cloud Monitoring (metrics and dashboards)
- Cloud Trace (distributed tracing)
- Alert policies and notifications
- Cost Management and Billing Analysis
- SLO tracking and error budgets

**Directory Structure**:
```
05-observability/
├── monitoring/       # Dashboards and metrics
├── logging/          # Log collection and processing
├── alerting/         # Alert policies
└── cost-tracking/    # Cost analysis
```

**Terraform Modules**:
- `modules/observability/monitoring` - Cloud Monitoring
- `modules/observability/logging` - Log sinks
- `modules/observability/alerting` - Alert policies

**Dependencies**: Layers 01-04 (all previous layers)

## Component Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│  Frontend (React SPA)  │  Backend (FastAPI API)         │
│  Cloud Storage + CDN   │  Cloud Run + Cloud SQL         │
└──────────┬──────────────────────────┬────────────────────┘
           │                          │
┌──────────▼──────────────────────────▼────────────────────┐
│  Layer 4: Workloads                                      │
│  - Cloud Run, Cloud SQL, Pub/Sub, Memorystore           │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  Layer 5: Observability (Runs parallel to Layer 4)      │
│  - Cloud Logging, Monitoring, Cost Tracking            │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  Layer 3: Security                                       │
│  - IAM, Secrets Manager, KMS, Compliance Policies      │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  Layer 2: Network                                        │
│  - VPC, Firewall, Cloud NAT, DNS                       │
└──────────┬──────────────────────────────────────────────┘
           │
┌──────────▼──────────────────────────────────────────────┐
│  Layer 1: Foundation                                     │
│  - GCP Project, Organization Policies, Cloud Build     │
└──────────────────────────────────────────────────────────┘
```

## Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| **Backend** | Python FastAPI | Type-safe, async, excellent GCP integration |
| **Frontend** | React + TypeScript + Vite | Modern SPA, strong typing, fast builds |
| **Infrastructure** | Terraform | IaC, reproducible, versioned |
| **CI/CD** | Cloud Build | Native GCP integration, serverless |
| **Container Registry** | Artifact Registry | Native GCP, fine-grained access control |
| **Compute** | Cloud Run | Serverless, auto-scaling, cost-efficient |
| **Database** | Cloud SQL | Managed RDBMS, automated backups |
| **Secrets** | Secret Manager | Encrypted, rotatable, audit-logged |
| **Monitoring** | Cloud Logging + Cloud Monitoring | Centralized, integrated, scalable |

## Key Architectural Decisions

### ADR-001: Serverless-First (Cloud Run)

**Decision**: Deploy backend and frontend as serverless workloads on Cloud Run

**Rationale**:
- No infrastructure management overhead
- Auto-scaling based on traffic
- Pay-per-request pricing model
- Native GCP integration
- Simpler deployment pipeline

**Alternatives Considered**:
- GKE: More overhead, better for complex microservices
- Compute Engine: More management burden

### ADR-002: Terraform for IaC

**Decision**: Use Terraform (not gcloud, Deployment Manager, or Pulumi)

**Rationale**:
- Multi-cloud capability
- Mature ecosystem and community
- State management and planning
- Module reusability

### ADR-003: 5-Layer Separation of Concerns

**Decision**: Organize Terraform into 5 distinct layers deployed sequentially

**Rationale**:
- Clear dependencies and ordering
- Parallel development across teams
- Reduced blast radius of changes
- Aligns with enterprise standards

## Deployment Model

### Deployment Order

```
1. Foundation (01)  ─┐
                     ├─→ Network (02)  ─┐
                                        ├─→ Security (03) ─┐
                                                            ├─→ Workloads (04) ┐
                                                                               ├─→ Observability (05)
```

### Environments

- **Development**: Rapid iteration, auto-deploys on commits
- **Staging**: Pre-production validation, manual deployment gates
- **Production**: Strict approval requirements, canary deployments

## Security Posture

### Zero-Trust Principles

1. **Identity Verification**: All access requires authentication
2. **Least Privilege**: Minimal IAM roles per service
3. **Secrets Management**: All credentials stored in Secret Manager
4. **Audit Logging**: All actions logged and monitored
5. **Network Segmentation**: VPC isolation by environment

### Compliance

- **FedRAMP Ready**: Encryption at rest and in transit
- **SOC 2 Type II**: Regular audits and attestations
- **NIST Controls**: Mapped to infrastructure policies
- **Data Residency**: All data stored in specified GCP regions

## Scalability Considerations

### Horizontal Scaling

- **Backend**: Cloud Run auto-scales based on CPU/memory
- **Database**: Cloud SQL read replicas and connection pooling
- **Frontend**: Cloud CDN caches assets globally
- **Messages**: Pub/Sub handles millions of messages/second

### Performance Targets

- **API Response Time**: < 200ms (p95)
- **Frontend Load Time**: < 3s (3G)
- **Database Query Time**: < 100ms (p99)
- **Availability**: 99.95% uptime SLA

## High Availability

- **Multi-region deployment**: Optional for production
- **Automated backups**: Daily, 30-day retention
- **Disaster recovery**: RTO < 4 hours, RPO < 1 hour
- **Health checks**: Continuous monitoring with auto-remediation

## Cost Optimization

- **Preemptible instances**: Where applicable
- **Resource quotas**: Limits prevent runaway costs
- **Reserved capacity**: For predictable baseline load
- **Cost alerts**: Notifications on budget overruns

## Development Workflow

```
Developer ─→ Git Commit ─→ Cloud Build CI ─→ Tests ─→ Deploy to Dev ─→ Promote to Staging → Prod
                         (automated)       (automated) (automated)
```

## References

- **Terraform Documentation**: https://registry.terraform.io/providers/hashicorp/google
- **GCP Best Practices**: https://cloud.google.com/architecture/best-practices
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Documentation**: https://react.dev/

---

**Version**: 1.0
**Last Updated**: 2026-01-19
**Owner**: Platform Engineering Team
