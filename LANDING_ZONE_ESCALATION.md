# Landing Zone Escalation Report
## GCP-landing-zone-Portal RCA Analysis
**Date:** January 31, 2026  
**From:** GCP-landing-zone-Portal Team  
**To:** Landing Zone Architecture Team  

---

## Executive Summary

During investigation of service startup issues in the GCP-landing-zone-Portal spoke, we identified **1 Landing Zone-level problem** that requires coordination and standardization across all spokes.

**Recommendation:** Implement a standardized OpenTelemetry configuration template at the landing zone level to prevent version compatibility issues.

---

## Issues Identified

### ✅ SPOKE-LEVEL (Resolved Locally)

#### 1. Missing email-validator Dependency
- **Status:** FIXED
- **Files Changed:** `backend/requirements.txt`
- **GitHub Issue:** #166
- **Impact:** Only affects this backend service
- **Resolution:** Added `email-validator>=2.1.0`

#### 2. Development Environment Configuration
- **Status:** FIXED  
- **Files Changed:** `docker-compose.yml`
- **GitHub Issue:** #168
- **Impact:** Local development setup only
- **Resolutions:**
  - Backend port: 8080 → 9000 (avoid VS Code Server conflict)
  - Environment: production → development
  - API URL: Fixed undefined HOST_IP variable

---

### 🚨 LANDING ZONE-LEVEL (Requires Escalation)

#### OpenTelemetry Instrumentation Standardization

**Problem:** Version incompatibility between `opentelemetry-instrumentation-fastapi==0.43b0` and current FastAPI setup.

```
ImportError: cannot import name 'FastInstrumentor' from 'opentelemetry.instrumentation.fastapi'
```

**GitHub Issue:** #167 (marked for Landing Zone escalation)

**Why This is Landing Zone-Level:**

1. **Multi-spoke impact:** All services using Python/FastAPI will face this
2. **Governance requirement:** Observability is a platform concern
3. **Templatable solution:** LZ should provide verified version matrix
4. **Onboarding requirement:** New spokes need clear OT setup guidance
5. **Cost optimization:** Proper instrumentation affects troubleshooting efficiency

**Recommended Solution:**

Create `landing-zone/observability-module/` with:

```
landing-zone/
├── observability/
│   ├── opentelemetry-versions.txt          # Verified dependency matrix
│   ├── fastapi-instrumentation/
│   │   ├── requirements.txt                 # Pinned versions
│   │   ├── main.py.template                 # Reference implementation
│   │   ├── VERSION_MATRIX.md               # Compatibility guide
│   │   └── MIGRATION_GUIDE.md
│   ├── health-checks/
│   │   ├── health_checker.py               # Reusable pattern
│   │   └── IMPLEMENTATION.md
│   └── ONBOARDING.md
```

**Implementation Plan:**

```
PHASE 1 (Week 1):
- [ ] Test all OT package versions against FastAPI v0.109.0
- [ ] Create verified requirements-base.txt for all LZ services
- [ ] Document version matrix and why each version was chosen

PHASE 2 (Week 2):
- [ ] Create reference FastAPI instrumentation template
- [ ] Test with sample spoke services
- [ ] Create migration guide for existing spokes

PHASE 3 (Week 3):
- [ ] Communicate to all spoke teams
- [ ] Support spoke updates to use new template
- [ ] Version in landing zone repo (tag v1.0-observability)

PHASE 4 (Ongoing):
- [ ] Monitor dependency updates
- [ ] Update compatibility matrix quarterly
- [ ] Provide version change notifications to spoke teams
```

**Temporary Workaround (Spoke-Level):**
```python
# backend/main.py
# Disabled incompatible instrumentation until LZ provides standardized version
# from opentelemetry.instrumentation.fastapi import FastInstrumentor
# FastInstrumentor.instrument_app(app)
```

---

## Additional Patterns Recommended for Landing Zone Template

While investigating, we identified other patterns that should be standardized:

### 1. **Health Check Framework** ✅
**Status:** Working implementation in this portal  
**Recommendation:** Extract and provide as LZ template

**What it does:**
- Verifies GCP connectivity (critical)
- Checks Redis availability (non-critical)
- Returns structured health status
- Used by Kubernetes readiness/liveness probes

**Implementation Location:**
```python
# backend/main.py - HealthChecker class (lines 86-127)
```

**Why it matters:**
- Ensures reliable service startup in production
- Provides visibility into dependency health
- Standard pattern across all spokes

### 2. **Middleware Stack** ✅
**Status:** Complete implementation in this portal  
**Recommendation:** Provide as architectural reference

**Components:**
- SecurityMiddleware (headers, CORS, request tracking)
- AuthMiddleware (optional auth, dev bypass)
- RateLimitMiddleware (sliding window rate limiting)
- Error handlers (structured error responses)

**Value:**
- Consistent API behavior across platform
- Enterprise-grade security baseline
- Easy to adopt in new spokes

---

## Current Service Status

### ✅ Running Successfully

```
SERVICE         STATUS        PORTS                  HEALTH
lz-backend      Up (15s)      0.0.0.0:9000->8080    Healthy ✓
lz-frontend     Up (15s)      0.0.0.0:5173->5173    Starting...
lz-redis        Up (15s)      0.0.0.0:6379->6379    Healthy ✓
```

### Endpoints Available
- API Health: `http://localhost:9000/health`
- API Docs: `http://localhost:9000/docs` (development only)
- Frontend: `http://localhost:5173` (in progress)
- Redis: `localhost:6379`
- Prometheus Metrics: `http://localhost:8001`

---

## Spoke Repositories Affected

This issue likely affects these spoke repositories:
- [ ] **[Name]** - FastAPI backend (affected by OT version issue)
- [ ] **[Name]** - Python services (affected by OT version issue)
- [ ] **[Any]** - Using FastAPI + OpenTelemetry (affected)

**Action:** When LZ provides updated template, all spokes should adopt standardized versions.

---

## Files Changed in This Spoke

```
GCP-landing-zone-Portal/
├── RCA_FRAMEWORK.md (NEW)
│   └── Classification system for LZ vs Spoke issues
├── docker-compose.yml
│   ├── Backend port: 8080 → 9000
│   ├── ENVIRONMENT: production → development
│   └── VITE_API_URL: Fixed HOST_IP variable
└── backend/
    ├── requirements.txt
    │   └── Added: email-validator>=2.1.0
    └── main.py
        ├── Commented out FastInstrumentor import
        └── Commented out FastInstrumentor.instrument_app() call
```

---

## Recommendations

### For Landing Zone Team:
1. **Priority 1:** Create OpenTelemetry standardization module (this will unblock all spokes)
2. **Priority 2:** Extract and document Health Check pattern
3. **Priority 3:** Provide Middleware Stack as reference architecture
4. **Priority 4:** Create spoke onboarding template with these patterns pre-integrated

### For This Spoke (GCP-landing-zone-Portal):
1. ✅ [DONE] Fix email-validator dependency
2. ✅ [DONE] Fix development environment configuration  
3. ⏳ [PENDING] Await Landing Zone OT standardization
4. ⏳ [PENDING] Re-enable instrumentation once LZ provides version guidance
5. ⏳ [PENDING] Complete frontend setup and integration testing

---

## Contact & Next Steps

**Spoke Point of Contact:** [Engineering Team]  
**Landing Zone Response Requested:** OpenTelemetry standardization module

**Timeline:**
- Week 1: LZ analyzes requirement and creates version matrix
- Week 2: LZ publishes template and migration guide
- Week 3: GCP-landing-zone-Portal adopts and tests
- Week 4: Other spokes begin adoption

---

**Document:** Landing Zone Escalation Report v1.0  
**Date:** January 31, 2026  
**Status:** Ready for Landing Zone review and action
