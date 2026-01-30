# Deployment Guide

## Prerequisites

### Required Tools
- Terraform 1.7+
- gcloud CLI (latest)
- kubectl 1.28+ (optional, for GKE integration)
- Docker 24+ (for local testing)
- Git with GPG signing configured

### Required Permissions
- Project Editor role in staging GCP project
- Project Owner role in production GCP project
- Cloud Build Service Agent role
- Cloud Run Admin role
- IAM Admin role (for service accounts)

### Required Setup
- GitHub repository cloned locally
- Cloud Build pipeline configured
- Service accounts created with Workload Identity
- Secrets stored in Secret Manager

## Pre-Deployment Checklist

- [ ] Code reviewed and approved (2+ reviewers)
- [ ] All tests passing (npm test + pytest)
- [ ] Snyk security scan passing
- [ ] Commit is GPG signed
- [ ] VERSION file updated (semantic versioning)
- [ ] CHANGELOG.md updated
- [ ] Terraform plan reviewed (no unexpected changes)
- [ ] Staging deployment successful (24 hours min)
- [ ] E2E tests passing on staging
- [ ] Performance tests meet targets
- [ ] On-call team notified

## Deployment Process

### Step 1: Staging Deployment (Automated)

Triggered automatically when PR is merged to `main`:

```bash
# Cloud Build pipeline runs:
1. Build Docker image (frontend + backend)
2. Run unit tests (npm test + pytest)
3. Run security scans (Snyk + Gitleaks)
4. Push image to Artifact Registry
5. Deploy to Cloud Run (staging)
6. Run E2E tests on staging
7. Slack notification → #portal-deploys
```

**Verify Staging:**
```bash
curl https://staging-portal.landing-zone.io/api/v1/health

# Expected response:
{
  "status": "healthy",
  "version": "1.2.3",
  "database": "connected",
  "cache": "operational"
}
```

**Monitor Staging (24 hours):**
- Error rate <0.1%
- P95 latency <100ms
- All core features working
- No user complaints

### Step 2: Production Deployment (Manual)

Once staging is verified stable:

```bash
# 1. Request approval from @platform-engineering
# 2. Create deployment ticket

# 3. Push release tag
git tag -s -m "Release v1.2.3" v1.2.3
git push origin v1.2.3

# 4. Cloud Build triggers production pipeline:
#    - Same build steps as staging
#    - Deploy to Cloud Run (production, 10% traffic)
#    - Monitor metrics (5 minutes)
#    - If OK → 50% traffic
#    - Monitor (5 minutes)
#    - If OK → 100% traffic
#    - Keep previous revision as fallback (7 days)

# 5. Verify production
curl https://portal.landing-zone.io/api/v1/health

# 6. Slack notification → #portal-deploys
```

**Gradual Rollout Timeline:**
- 0-5 min: 10% traffic (canary)
- 5-10 min: 50% traffic (validation)
- 10-20 min: 100% traffic (full deployment)
- 20+ min: Monitor for issues

## Infrastructure Deployment

### Initial Setup (One-time)

```bash
# 1. Clone Portal repo
git clone https://github.com/kushin77/GCP-landing-zone-Portal.git
cd GCP-landing-zone-Portal

# 2. Create GCP projects (staging + prod)
gcloud projects create portal-staging --name="Portal Staging"
gcloud projects create portal-prod --name="Portal Production"

# 3. Enable required APIs
gcloud services enable \
  cloudrun.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  secretmanager.googleapis.com \
  cloudkms.googleapis.com \
  iap.googleapis.com \
  --project=portal-staging

# Same for portal-prod

# 4. Initialize Terraform
cd terraform/foundation
terraform init \
  -backend-config="bucket=portal-terraform-state" \
  -backend-config="prefix=staging"

# 5. Deploy foundation
terraform plan -out=tfplan
# Review changes
terraform apply tfplan

# 6. Repeat for production
cd ../../../terraform/foundation
terraform init \
  -backend-config="bucket=portal-terraform-state" \
  -backend-config="prefix=prod"
terraform apply
```

### Update Existing Deployment

```bash
# 1. Make infrastructure changes
vim terraform/02-networking/vpc/main.tf

# 2. Validate changes
terraform validate

# 3. Review plan
terraform plan -out=tfplan

# 4. Apply changes
terraform apply tfplan

# 5. Verify via gcloud
gcloud compute networks describe portal-network --project=portal-staging
```

## Rollback Procedure

### Rollback to Previous Version (Cloud Run)

```bash
# 1. Check available revisions
gcloud run revisions list \
  --service=portal-backend \
  --region=us-central1 \
  --project=portal-prod

# 2. Route 100% traffic to previous revision
gcloud run services update-traffic portal-backend \
  --to-revisions REVISION_NAME=100 \
  --region=us-central1 \
  --project=portal-prod

# 3. Verify new version
curl https://portal.landing-zone.io/api/v1/health

# 4. Keep new revision for 7 days (audit trail)
# 5. Automatically deleted after 7 days
```

### Rollback Terraform Changes

```bash
# 1. Revert to previous state
terraform state pull > backup.tfstate
gsutil cp gs://portal-terraform-state/prod/terraform.tfstate previous-state.tfstate
terraform state push previous-state.tfstate

# 2. Verify changes
terraform plan # Should show rollback changes

# 3. Apply rollback
terraform apply

# 4. Notify team → #portal-deploys
```

## Monitoring Deployment

### Real-time Monitoring

```bash
# Cloud Run logs
gcloud run logs read portal-backend \
  --project=portal-prod \
  --limit=100

# Error reporting
gcloud logging read "severity=ERROR AND resource.type=cloud_run_revision" \
  --project=portal-prod \
  --format=json | head -20

# Performance metrics
gcloud monitoring dashboards describe portal-main \
  --project=portal-prod
```

### Deployment Health Checks

| Check | Target | Tool |
|-------|--------|------|
| Uptime | 99.9% | Cloud Monitoring SLO |
| Error rate | <0.1% | Error Reporting |
| P95 latency | <100ms | Cloud Trace |
| Database connectivity | 100% | Health endpoint |
| Cache hit rate | >80% | Application metrics |

## Deployment Troubleshooting

### Issue: Cloud Run service won't start

```bash
# 1. Check logs
gcloud run logs read portal-backend --project=portal-prod --tail=50

# 2. Check secrets
gcloud secrets list --project=portal-prod
gcloud secrets versions access latest --secret=db-url --project=portal-prod

# 3. Check service account
gcloud iam service-accounts describe portal-sa@portal-prod.iam.gserviceaccount.com

# 4. Check Workload Identity binding
gcloud iam service-accounts add-iam-policy-binding \
  portal-sa@portal-prod.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:portal-prod.svc.id.goog[portal/portal-sa]"

# 5. Restart service
gcloud run services update portal-backend --no-traffic --project=portal-prod
```

### Issue: Database connection timeout

```bash
# 1. Check Firestore connectivity
gcloud firestore databases describe --database='(default)' --project=portal-prod

# 2. Check private VPC connector
gcloud compute networks vpc-access connectors describe portal-connector \
  --region=us-central1 \
  --project=portal-prod

# 3. Check IAM permissions
gcloud projects get-iam-policy portal-prod \
  --flatten="bindings[].members" \
  --filter="bindings.members:portal-sa@portal-prod.iam.gserviceaccount.com"

# 4. Check BigQuery connectivity
bq ls --project_id=portal-prod
```

### Issue: High error rate after deployment

```bash
# 1. Check application logs
gcloud logging read "resource.type=cloud_run_revision AND severity=ERROR" \
  --project=portal-prod \
  --limit=50

# 2. Check if it's a dependency issue
curl https://portal.landing-zone.io/api/v1/health -v

# 3. Rollback if critical
gcloud run services update-traffic portal-backend \
  --to-revisions PREVIOUS_REVISION=100 \
  --project=portal-prod

# 4. Post-mortem
# Create issue: "Deployment incident: [date] [description]"
# Include: logs, root cause, prevention steps
```

## Post-Deployment

### Immediate (First hour)
- Monitor error rates via Cloud Monitoring
- Check P95/P99 latencies
- Verify all APIs responding
- Confirm Pub/Sub events flowing

### Short-term (First 24 hours)
- Monitor database performance
- Check cache hit rates
- Verify no security alerts
- Collect user feedback

### Long-term (First week)
- Performance trending
- Cost impact analysis
- User adoption metrics
- Security posture

## Version Management

### Semantic Versioning
- **MAJOR**: Breaking changes (Cloud Run, database schema)
- **MINOR**: New features (API endpoints, UI components)
- **PATCH**: Bug fixes, security patches

### Version Tagging
```bash
# Create version
git tag -s -m "Release v1.2.3" v1.2.3
git push origin v1.2.3

# Verify
git describe --tags
```

### VERSION File
```
MAJOR=1
MINOR=2
PATCH=3
BUILD=20260118
COMMIT_SHA=$(git rev-parse --short HEAD)
```

---

**Last Updated**: 2026-01-18
**Deployment Version**: 1.0
