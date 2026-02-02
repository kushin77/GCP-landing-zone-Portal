# Root Cause Analysis (RCA) Framework
## Landing Zone Portal - Governance & Escalation Model

**Date:** January 31, 2026  
**Version:** 1.0  
**Classification:** Landing Zone Architecture Decision Record

---

## Executive Summary

This document establishes the governance model for identifying whether issues and RCAs belong at the **Landing Zone (LZ) Level** (global, templated, reusable) or **Spoke Level** (local, repository-specific).

---

## Classification Criteria

### 🏢 **LANDING ZONE LEVEL** (Global Template)
Issues/patterns that should be standardized, templated, and reused across all spokes.

**Characteristics:**
- **Multi-spoke impact**: Affects 2+ spokes or foundational services
- **Governance requirement**: Relates to compliance, security, audit, policy enforcement
- **Templatable solution**: Fix can be packaged as a reusable module/pattern
- **Cost optimization**: Affects billing, resource allocation, or infrastructure efficiency
- **Infrastructure layer**: Foundation, Network, Security (layers 1-3 in 5-layer model)
- **Observability/compliance**: Monitoring, logging, tracing at platform level
- **Authentication/Authorization**: Identity, RBAC, service accounts, workload identity
- **GCP service integration**: Cloud Asset Inventory, Cloud Resource Manager, BigQuery integration
- **Disaster recovery/continuity**: Backup, replication, failover strategies

**Examples:**
- ❌ Missing email-validator dependency → SPOKE level (local fix)
- ✅ OpenTelemetry instrumentation standardization → LANDING ZONE (template all services)
- ✅ Workload Identity setup pattern → LANDING ZONE (standard for all spokes)
- ✅ Redis caching strategy → SPOKE level (each spoke has own caching needs)
- ✅ Health check framework → LANDING ZONE (consistent readiness probes across platform)

---

### 🔧 **SPOKE LEVEL** (Local, Responsibility of Repository)
Issues specific to this repository's implementation.

**Characteristics:**
- **Single-spoke impact**: Only affects this repository
- **Application-specific**: Related to this portal's unique features/requirements
- **Local dependencies**: Package versions, build configuration for this service
- **UI/UX implementation**: Frontend-specific behaviors, form validation
- **Database schema**: Local data models specific to this portal
- **Testing**: Unit/integration tests for this service
- **Performance tuning**: Cache sizes, connection pools for this workload
- **Logging/debugging**: Service-specific instrumentation

**Examples:**
- ✅ email-validator missing dependency → SPOKE (frontend/backend service fix)
- ✅ VITE_API_URL configuration for local development → SPOKE (portal-specific setup)
- ✅ Nginx configuration for this portal → SPOKE (unless reusable across spokes)
- ✅ React component state management → SPOKE (UI-specific)
- ✅ Backend router organization → SPOKE (service architecture)

---

## Assessment Matrix

| Category | LANDING ZONE | SPOKE | Criteria |
|----------|-------------|-------|----------|
| **Authentication** | ✅ | | Workload Identity, service accounts, RBAC policies |
| **Network** | ✅ | | VPC, subnets, firewall rules, load balancing |
| **Compliance** | ✅ | | Audit logging, data residency, encryption |
| **Dependencies** | ❌ | ✅ | Package versions, library conflicts |
| **Caching Strategy** | ❌ | ✅ | Redis config, cache keys (unless standardization needed) |
| **Health Checks** | ✅ | | Consistent patterns, readiness/liveness probes |
| **Observability** | ✅ | | Logging format, trace schema, metrics definitions |
| **Configuration** | ⚠️ | ✅ | If template exists, LANDING ZONE; if local, SPOKE |
| **Error Handling** | ✅ | | Middleware stack, error response format |

---

## Current State Assessment

### Identified Issues (as of Jan 31, 2026)

#### 1. **OpenTelemetry Integration Issue** ❌ → LANDING ZONE
**Current Status:** FastInstrumentor import failure  
**Impact:** All services attempting to instrument with OpenTelemetry  
**Action:** 
- [ ] Create landing zone template for OpenTelemetry setup
- [ ] Pin compatible versions across all services
- [ ] Document instrumentation patterns
- [ ] Communicate to all spokes

#### 2. **Email-validator Dependency** ❌ → SPOKE (GCP-landing-zone-Portal)
**Current Status:** Missing pydantic[email] requirement  
**Impact:** Only this backend service  
**Action:**
- [x] Add email-validator to requirements.txt (COMPLETED)
- [ ] Document dependency management process

#### 3. **Development Environment Configuration** ❌ → SPOKE (GCP-landing-zone-Portal)
**Current Status:** VITE_API_URL, port configuration, environment vars  
**Impact:** Only this portal's Docker setup  
**Action:**
- [x] Update docker-compose.yml to use localhost:9000
- [x] Change ENVIRONMENT to "development" by default
- [ ] Document local dev setup

#### 4. **Health Check Framework** ✅ → LANDING ZONE (Template)
**Current Status:** Implemented in this portal  
**Recommendation:** Standardize and provide as LZ template
- **Why:** Consistent readiness probe pattern needed across all services
- **Impact:** Ensures reliable deployment and orchestration
- **Action:** Extract to landing zone and provide for reuse

#### 5. **Middleware Stack** ✅ → LANDING ZONE (Template)
**Current Status:** Implemented in this portal  
**Recommendation:** Provide as reference implementation for all spokes
- **Components:** Auth, Rate Limiting, Security, Error Handling
- **Benefit:** Consistent API behavior across platform
- **Action:** Document and share as architectural pattern

---

## Escalation Process

### When You Find an Issue:

1. **Ask:** "Does this affect multiple spokes or is foundational?"
   - YES → LANDING ZONE (send RCA + templating plan)
   - NO → Continue to step 2

2. **Ask:** "Can this be packaged as reusable module/pattern?"
   - YES → LANDING ZONE (standardize across platform)
   - NO → Continue to step 3

3. **Ask:** "Is this governance, compliance, or security-related?"
   - YES → LANDING ZONE (ensure all spokes comply)
   - NO → SPOKE (local responsibility)

4. **Default:** If still uncertain → **SPOKE** (let repository own it, escalate if pattern emerges)

---

## RCA Template for Escalation

When sending RCA to Landing Zone, include:

```
# RCA: [Issue Title]

## Problem Statement
[What's broken and why it matters]

## Root Cause
[Why did this happen]

## Current Impact
- [Spoke 1]: [Impact]
- [Spoke 2]: [Impact]

## Recommended Landing Zone Solution
[How to template/standardize this]

## Implementation Pattern
[Reusable code/config example]

## Onboarding Checklist
- [ ] Create terraform module (if infra-related)
- [ ] Create sample implementation
- [ ] Document in architecture guide
- [ ] Communicate to all spoke teams
- [ ] Version in landing zone repo
```

---

## Action Items - GCP Landing Zone Portal (This Repo)

### Completed (Jan 31, 2026)
- [x] Fixed email-validator dependency
- [x] Updated docker-compose for development
- [x] Fixed OpenTelemetry import (disabled incompatible instrumentation)
- [x] Backend service running on port 9000
- [x] Frontend service configured

### To Do (SPOKE LEVEL)
- [ ] Rebuild frontend with correct API configuration
- [ ] Complete systemd service setup for auto-start
- [ ] Configure Nginx reverse proxy for external access
- [ ] Create local development documentation
- [ ] Add to spoke team's issue board

### Escalate to Landing Zone
- [ ] OpenTelemetry version standardization
- [ ] Health check framework (as template)
- [ ] Middleware stack (as reference)
- [ ] Environment variable naming conventions
- [ ] Docker Compose vs Kubernetes transition strategy

---

## References

- **Architecture:** ARCHITECTURE.md (5-layer model)
- **Contributing:** CONTRIBUTING.md
- **Testing:** docs/TESTING.md
- **Local Setup:** docs/LOCAL_SETUP.md

---

**Document Owner:** Engineering Team  
**Last Updated:** Jan 31, 2026  
**Next Review:** [After all spokes assessed]
