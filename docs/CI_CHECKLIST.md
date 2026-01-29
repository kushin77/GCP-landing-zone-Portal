# CI/CD Verification Checklist

**Issue #106 Deliverable**  
**Status:** Pre-Flight Checklist (Ready for execution after #104 & #105 complete)  
**Depends On:** #104 (token rotation), #105 (GSM migration)

---

## Overview

This checklist validates that the CI/CD pipeline is properly configured, all secrets are securely stored, and tests are running successfully. This work depends on completion of the critical security tasks (#104 token rotation, #105 GSM migration).

---

## Pre-Execution Prerequisites

Before starting this task, verify:

- [ ] **#104 Complete**: Token has been rotated and new PAT stored in GSM
- [ ] **#105 Complete**: All secrets migrated from GitHub Secrets to Google Secret Manager
- [ ] **Cloud Build Access**: Verified permissions in GCP project (roles: `cloudbuild.builds.editor`)
- [ ] **GitHub Token**: Confirmed new PAT in GSM (via `gcloud secrets versions access latest --secret=github-pat`)
- [ ] **Cloud Build Credentials**: Verified in Secret Manager

---

## Section 1: Local Test Validation

### 1.1 Run Full Test Suite

```bash
cd /home/akushnir/GCP-landing-zone-Portal/backend
python -m pytest tests/ -v --cov=. --cov-report=html
```

**Acceptance Criteria:**
- [ ] All tests pass (exit code 0)
- [ ] Coverage >= 80%
- [ ] `coverage_html/index.html` generated

**Expected Output:**
```
====== test session starts ======
collected 45 items
tests/test_api.py ........................... [ 50%]
tests/test_auth.py ................. [ 100%]
====== 45 passed in 2.34s ======
```

### 1.2 Verify Pytest Configuration

```bash
cat backend/pytest.ini
```

**Acceptance Criteria:**
- [ ] File exists and contains proper pytest markers
- [ ] `markers = unit, integration, slow` configured
- [ ] Coverage thresholds set to >= 80%

---

## Section 2: Cloud Build Pipeline Validation

### 2.1 Verify cloudbuild.yaml Configuration

```bash
cat cloudbuild.yaml | grep -A 5 "steps:"
```

**Acceptance Criteria:**
- [ ] Step 1: Run tests (`python -m pytest`)
- [ ] Step 2: Build Docker images (backend & frontend)
- [ ] Step 3: Push to GCR
- [ ] Step 4: Deploy to GKE (if applicable)

### 2.2 Check Cloud Build Secrets Integration

```bash
gcloud builds describe <BUILD_ID> --format='value(substitutions)'
```

**Acceptance Criteria:**
- [ ] Secret Manager references present in build config
- [ ] No hardcoded credentials in cloudbuild.yaml
- [ ] All required secrets referenced: `_GITHUB_TOKEN`, `_GCP_PROJECT_ID`

### 2.3 Trigger Build Manually

```bash
gcloud builds submit . \
  --config=cloudbuild.yaml \
  --substitutions=_GITHUB_TOKEN=$(gcloud secrets versions access latest --secret=github-pat),_GCP_PROJECT_ID=$GOOGLE_CLOUD_PROJECT
```

**Acceptance Criteria:**
- [ ] Build starts successfully
- [ ] Build log shows test execution
- [ ] Build completes with status: SUCCESS
- [ ] No authentication errors in logs

**Expected Output:**
```
ID: <BUILD_ID>
CREATE_TIME: 2026-01-29T...
STATUS: QUEUED
```

---

## Section 3: GitHub Actions Integration

### 3.1 Verify GitHub Actions Workflows

```bash
ls -la .github/workflows/
```

**Acceptance Criteria:**
- [ ] `pytest.yml` exists (test workflow)
- [ ] `docker-build.yml` exists (container build)
- [ ] `deploy.yml` exists (deployment workflow) [if applicable]
- [ ] All workflows reference GSM secrets, not GitHub Secrets

### 3.2 Check Workflow Secrets Configuration

```bash
gh secret list
```

**Acceptance Criteria:**
- [ ] Minimal secrets in GitHub (only build tokens if needed)
- [ ] All application secrets removed (moved to GSM)
- [ ] Output shows < 5 secrets (migration successful)

**Expected Output:**
```
MINIMAL_SECRET_1  Updated 2026-01-29
MINIMAL_SECRET_2  Updated 2026-01-29
(should have very few entries)
```

### 3.3 Run Test Workflow

```bash
# View latest workflow run
gh run list --workflow=pytest.yml --limit=1

# Check job status
gh run view <RUN_ID> --log
```

**Acceptance Criteria:**
- [ ] Latest workflow run passed
- [ ] All test steps completed successfully
- [ ] Log shows proper pytest output
- [ ] No secrets exposed in logs

---

## Section 4: Secret Manager Verification

### 4.1 List All Secrets in GSM

```bash
gcloud secrets list --format='table(name,created,updated)'
```

**Acceptance Criteria:**
- [ ] All production secrets present
- [ ] Timestamps show recent updates (within 24 hours of #105 completion)
- [ ] Secrets include: `github-pat`, `gcp-sa-key`, database credentials, API keys

### 4.2 Verify Secret Access Permissions

```bash
for SECRET in github-pat gcp-sa-key; do
  gcloud secrets get-iam-policy $SECRET --format='table(bindings[].members[])'
done
```

**Acceptance Criteria:**
- [ ] Cloud Build service account has `secretmanager.secretAccessor` role
- [ ] Only authorized users/services can access
- [ ] No public access permissions

### 4.3 Test Secret Retrieval (Non-Sensitive Values)

```bash
gcloud secrets versions access latest --secret=github-pat | head -c 10
```

**Acceptance Criteria:**
- [ ] Command succeeds without errors
- [ ] Output shows token prefix (verify storage, don't expose full token)
- [ ] Confirms GSM integration is working

---

## Section 5: Docker & Container Registry

### 5.1 Build Docker Images Locally

```bash
docker-compose build backend frontend
```

**Acceptance Criteria:**
- [ ] Backend image builds successfully
- [ ] Frontend image builds successfully
- [ ] No build errors or warnings (warnings acceptable)
- [ ] Images tagged correctly

### 5.2 Verify Docker Image Scanning (if GCR enabled)

```bash
gcloud container images list --repository=$GOOGLE_CLOUD_PROJECT/gcr.io
```

**Acceptance Criteria:**
- [ ] Images exist in Container Registry
- [ ] Vulnerability scanning completed
- [ ] Critical vulnerabilities: 0
- [ ] High vulnerabilities: < 5

### 5.3 Test Container Runtime

```bash
docker-compose up -d backend
sleep 5
docker-compose logs backend | grep "Application startup complete"
```

**Acceptance Criteria:**
- [ ] Container starts without errors
- [ ] Application initializes successfully
- [ ] Health endpoints respond (e.g., `/health`)

```bash
curl http://localhost:8000/health
# Should return: {"status": "ok"}
```

---

## Section 6: Integration Testing

### 6.1 Test API Endpoints

```bash
# Assuming backend running on port 8000
curl -X GET http://localhost:8000/api/projects -H "Authorization: Bearer $TEST_TOKEN"
```

**Acceptance Criteria:**
- [ ] API responds with status 200 or appropriate error code
- [ ] Response format valid JSON
- [ ] No authentication errors (indicates token in GSM working)

### 6.2 Test Database Connectivity

```bash
# Via Docker Compose
docker-compose exec backend python -c "from backend.models import Base; print('DB connection successful')"
```

**Acceptance Criteria:**
- [ ] Database connection successful
- [ ] No connection timeout errors
- [ ] All models load correctly

### 6.3 Test GCP Integration

```bash
# Verify gcloud CLI works with credentials
gcloud auth list
gcloud projects list --limit=1
```

**Acceptance Criteria:**
- [ ] GCP authentication working
- [ ] Can list GCP projects
- [ ] Service account properly configured

---

## Section 7: Pipeline Observability

### 7.1 Check Cloud Build Metrics (Prometheus)

```bash
cat observability/prometheus.yml | grep -A 10 "cloud_build"
```

**Acceptance Criteria:**
- [ ] Cloud Build job metrics configured
- [ ] Scrape endpoints reachable
- [ ] Metrics include: build duration, success rate, failure count

### 7.2 View Build Dashboard

- **Access Point:** Grafana (if deployed) or GCP Cloud Build console
- **URL:** `https://console.cloud.google.com/cloud-build/builds`

**Acceptance Criteria:**
- [ ] Recent builds visible
- [ ] Success rate > 90% in last 7 days
- [ ] Average build time < 10 minutes
- [ ] No cascading failures

### 7.3 Create CI Monitoring Dashboard Documentation

Create `docs/CI_MONITORING_DASHBOARD.md`:

```markdown
# CI/CD Monitoring Dashboard

## Real-Time Metrics

### Cloud Build Metrics
- **Success Rate**: XXX% (7-day average)
- **Average Duration**: XXX minutes
- **Total Builds**: XXX
- **Failed Builds (7d)**: XXX

### Test Metrics
- **Total Tests**: 45
- **Pass Rate**: 100%
- **Coverage**: 85%
- **Slow Tests (>5s)**: 2

### Deployment Metrics
- **Last Deployment**: [timestamp]
- **Deployment Success Rate**: 95%
- **Rollback Rate**: < 1%
```

**Acceptance Criteria:**
- [ ] File created at `docs/CI_MONITORING_DASHBOARD.md`
- [ ] Contains current metrics snapshot
- [ ] Includes dashboard access instructions

---

## Section 8: Documentation Validation

### 8.1 Verify CI Documentation is Complete

```bash
ls -la docs/ | grep -i ci
# Should include: CI_CHECKLIST.md, CI_MONITORING_DASHBOARD.md, TESTING.md
```

**Acceptance Criteria:**
- [ ] `docs/CI_CHECKLIST.md` exists (this file)
- [ ] `docs/CI_MONITORING_DASHBOARD.md` exists
- [ ] `docs/TESTING.md` includes CI section
- [ ] Links between docs are correct

### 8.2 Cross-Reference Validation

Verify all CI docs are linked in main README:

```bash
grep -i "ci\|pipeline\|testing" README.md
```

**Acceptance Criteria:**
- [ ] README links to `docs/TESTING.md`
- [ ] README links to `docs/CI_CHECKLIST.md`
- [ ] README links to observability/prometheus.yml
- [ ] All links are working (test locally with markdown preview)

---

## Completion Checklist

### All Sections Completed
- [ ] Section 1: Local tests passing (80%+ coverage)
- [ ] Section 2: Cloud Build pipeline validated
- [ ] Section 3: GitHub Actions configured for GSM
- [ ] Section 4: All secrets verified in GSM
- [ ] Section 5: Docker images building and scanning
- [ ] Section 6: Integration tests passing
- [ ] Section 7: Pipeline observability configured
- [ ] Section 8: Documentation complete and linked

### Issue Resolution
- [ ] All acceptance criteria verified
- [ ] No CI/CD blockers identified
- [ ] Green status on all builds (last 5 runs)
- [ ] Performance metrics acceptable
- [ ] Team members notified of CI status

### Final Actions
- [ ] Add completion comment to issue #106
- [ ] Tag @kushin77 for final review
- [ ] Close issue #106 with summary
- [ ] Update issue #81 final status
- [ ] Close parent epic #88 (CI/CD & Tests)

---

## Troubleshooting Reference

### Issue: Build Fails with "Secret Not Found"
**Solution:** Verify GSM migration complete (#105), check service account permissions
```bash
gcloud secrets get-iam-policy github-pat
```

### Issue: Docker Build Fails
**Solution:** Clear Docker cache and rebuild
```bash
docker-compose down -v
docker-compose build --no-cache backend frontend
```

### Issue: Tests Timeout
**Solution:** Check if integration tests are marked `@pytest.mark.slow`
```bash
grep -r "@pytest.mark" backend/tests/
```

### Issue: GCP Auth Fails in Pipeline
**Solution:** Verify service account key stored in GSM and accessible to Cloud Build
```bash
gcloud secrets versions access latest --secret=gcp-sa-key | head -c 20
```

---

## Sign-Off

**Completed By:** [Your Name]  
**Completion Date:** [Date]  
**Issue Link:** https://github.com/kushin77/GCP-landing-zone-Portal/issues/106  
**Epic Link:** https://github.com/kushin77/GCP-landing-zone-Portal/issues/88

---

**Next Steps After This Task:**
1. Update issue #81 with final completion status
2. Close parent epic #88 (CI/CD & Tests)
3. Close remaining parent epics (#87, #89-92) as child tasks complete
4. Archive old discovery branch (feat/discovery-prototype)
5. Create final onboarding summary PR
