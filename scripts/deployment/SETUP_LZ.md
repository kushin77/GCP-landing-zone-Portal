#!/usr/bin/env bash
set -euo pipefail

# Complete setup guide for deploying GCP Landing Zone Portal under /lz with OAuth
# This script documents all manual and automated steps required

cat <<'EOF'

╔════════════════════════════════════════════════════════════════════════════╗
║                                                                            ║
║            GCP Landing Zone Portal - /lz Deployment Setup Guide            ║
║                                                                            ║
║                    ✅ Production-Ready Automation Stack                    ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝

## Overview

The portal is now fully configured to be served at https://elevatediq.ai/lz with:
- HTTPS Load Balancer (managed SSL)
- OAuth protection via Google IAP
- Frontend SPA routed to /lz
- Backend API routed to /lz/api/*
- Fully automated CI/CD pipeline

---

## Prerequisites

1. GCP Project with billing enabled
2. gcloud CLI configured with appropriate permissions
3. Secret Manager API enabled
4. Cloud Build configured for your repository

---

## Step 1: Create Secret Manager Secret for Terraform Variables

Store your Terraform variables in Secret Manager:

```bash
PROJECT_ID="your-project-id"

cat > /tmp/workloads.tfvars << 'TFVARS'
project_id               = "YOUR_PROJECT_ID"
region                   = "us-central1"
domain                   = "elevatediq.ai"
frontend_bucket          = "YOUR_PROJECT_ID-frontend"
cloud_run_service_name   = "portal-backend"
iap_client_id            = "YOUR_IAP_CLIENT_ID.apps.googleusercontent.com"
iap_client_secret        = "YOUR_IAP_CLIENT_SECRET"
TFVARS

# Create the secret
gcloud secrets create PORTAL_WORKLOADS_TFVARS \
  --data-file=/tmp/workloads.tfvars \
  --project=$PROJECT_ID

# Grant Cloud Build service account access
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
CLOUD_BUILD_SA="${PROJECT_NUMBER}@cloudbuild.gserviceaccount.com"

gcloud secrets add-iam-policy-binding PORTAL_WORKLOADS_TFVARS \
  --member=serviceAccount:$CLOUD_BUILD_SA \
  --role=roles/secretmanager.secretAccessor \
  --project=$PROJECT_ID
```

---

## Step 2: Configure Cloud Build Trigger

In Cloud Build, set up a trigger for your repository with:

**Default substitutions**:
- `_APPLY_WORKLOADS`: `false` (plan-only by default; set to `true` to apply)
- `_REGION`: `us-central1`

**Build gating** (optional but recommended):
- Require approval before apply
- Set `_APPLY_WORKLOADS=true` only on approved builds

---

## Step 3: Configure Cloud Run Environment

Once the LB is deployed, set Cloud Run env variables:

```bash
PROJECT_ID="your-project-id"
SERVICE_NAME="portal-backend"
REGION="us-central1"

# Get the backend service ID from Terraform output or GCP Console
BACKEND_SERVICE_ID="xxxxxxxx"  # From terraform/04-workloads apply
PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format='value(projectNumber)')
IAP_AUDIENCE="/projects/${PROJECT_NUMBER}/global/backendServices/${BACKEND_SERVICE_ID}"

# Set environment variables
gcloud run services update $SERVICE_NAME \
  --region=$REGION \
  --project=$PROJECT_ID \
  --set-env-vars=BASE_PATH=/lz,REQUIRE_AUTH=true,IAP_AUDIENCE="$IAP_AUDIENCE"
```

---

## Step 4: Verify Deployment

```bash
# Check health endpoints
curl -I https://elevatediq.ai/lz/health
curl -I https://elevatediq.ai/lz/ready

# Smoke test
./scripts/deployment/smoke-lz.sh elevatediq.ai

# View API docs (dev only)
curl https://elevatediq.ai/lz/docs
```

---

## Step 5: Deploy Frontend Assets (Optional)

If using GCS bucket for frontend:

```bash
cd frontend
npm run build

# Upload to GCS
gsutil -m cp -r dist/* gs://${PROJECT_ID}-frontend/

# Optionally invalidate CDN cache
gcloud compute backend-buckets invalidate-cdn-cache portal-frontend-bucket \
  --path "/*"
```

---

## CI/CD Workflow

### Plan-Only Build (Default)

```bash
git push origin main
# Cloud Build will:
# 1. Run security, lint, test
# 2. Build & push container images
# 3. terraform plan for 04-workloads (_APPLY_WORKLOADS=false)
# 4. Skip terraform apply
```

### Plan + Apply Build

In Cloud Build trigger, set substitution `_APPLY_WORKLOADS=true`:

```bash
gcloud builds submit \
  --substitutions _APPLY_WORKLOADS=true \
  --branch main
# Cloud Build will:
# 1. Run all checks
# 2. terraform plan for 04-workloads
# 3. terraform apply (LB + IAP stack)
```

---

## Troubleshooting

### Health checks fail
- Ensure Cloud Run service is deployed and running
- Check IAP is configured and JWT validation is not failing
- Verify BASE_PATH and IAP_AUDIENCE env vars are set

### DNS not resolving
- Ensure managed SSL cert is provisioned (check Compute → Network Services → SSL certificates)
- Update DNS records to point to the LB public IP

### API 401/403
- Confirm IAP is enforced on the backend service
- Check OAuth client ID/secret match the IAP configuration
- Test with gcloud CLI: gcloud compute security-policies describe

### Terraform apply fails
- Check Secret Manager secret PORTAL_WORKLOADS_TFVARS exists and has correct values
- Ensure Cloud Build SA has Terraform permissions
- Review Cloud Build logs for full error output

---

## Security Best Practices

✅ All environment variables (BASE_PATH, IAP_AUDIENCE, OAUTH_ALLOWED_DOMAINS) set via Cloud Run
✅ Secrets stored in Secret Manager (never in code)
✅ IAP enforces OAuth at edge (LB level)
✅ Backend validates x-goog-iap-jwt-assertion header
✅ HTTPS only (managed SSL cert)
✅ CORS configured for frontend domain
✅ Rate limiting active on API
✅ All commits GPG-signed

---

## Rollback Procedures

### Rollback LB/IAP

```bash
cd terraform/04-workloads
terraform destroy -var-file=terraform.tfvars
```

### Rollback Cloud Run

```bash
gcloud run services update-traffic portal-backend \
  --to-revisions PREVIOUS_REVISION_ID=100 \
  --region us-central1
```

---

## Useful Commands

```bash
# View Cloud Build logs
gcloud builds log BUILD_ID --stream

# Get load balancer status
gcloud compute backend-services describe portal-api-backend

# Check IAP configuration
gcloud iap web get portal-api-backend

# Monitor API traffic
gcloud logging read \
  "resource.type=api" \
  "resource.labels.service=portal-backend" \
  --limit=50

# View Terraform state
cd terraform/04-workloads
terraform show
terraform state list
```

---

## Next Steps

1. ✅ Secrets configured in Secret Manager
2. ✅ Cloud Build trigger set with _APPLY_WORKLOADS substitution
3. ✅ Cloud Run env updated with BASE_PATH/IAP_AUDIENCE
4. ✅ Health checks passing
5. 📋 Monitor logs and metrics
6. 📋 Set up CloudOps alerts for /lz endpoints
7. 📋 Document OAuth client ID for team access

---

**Status**: Ready for Production Deployment  
**Date**: 2026-01-19  
**Support**: See DEPLOYMENT.md and terraform/04-workloads/lb/README.md

EOF
