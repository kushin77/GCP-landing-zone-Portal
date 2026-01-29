# Landing Zone Portal - Deployment Scripts

Automated deployment scripts for the GCP Landing Zone Portal at `/lz`.

## Quick Start

### 1. Deploy LB/IAP (via Terraform)

```bash
cd terraform/04-workloads
cp terraform.tfvars.example terraform.tfvars  # fill in values
terraform init
terraform apply -var-file=terraform.tfvars
```

Alternatively, trigger via Cloud Build with `_APPLY_WORKLOADS=true`.

### 2. Configure Cloud Run Environment

Once the LB is deployed, wire Cloud Run env variables:

```bash
# Get BACKEND_SERVICE_ID from terraform output or GCP Console
./scripts/deployment/setup-cloud-run-env.sh YOUR_PROJECT portal-backend us-central1 BACKEND_SERVICE_ID
```

Or all-in-one after LB deployment:

```bash
./scripts/deployment/deploy-lz-complete.sh YOUR_PROJECT elevatediq.ai BACKEND_SERVICE_ID
```

### 3. Verify

```bash
./scripts/deployment/smoke-lz.sh elevatediq.ai
```

---

## Scripts

### `setup-cloud-run-env.sh`
Sets Cloud Run environment variables:
- `BASE_PATH=/lz`
- `REQUIRE_AUTH=true`
- `IAP_AUDIENCE=/projects/{project_number}/global/backendServices/{backend_service_id}`
- `ENVIRONMENT=production`

**Usage**:
```bash
./scripts/deployment/setup-cloud-run-env.sh PROJECT_ID SERVICE_NAME REGION BACKEND_SERVICE_ID
```

### `deploy-lz-complete.sh`
All-in-one: configures Cloud Run env, waits for stabilization, runs health checks.

**Usage**:
```bash
./scripts/deployment/deploy-lz-complete.sh PROJECT_ID DOMAIN BACKEND_SERVICE_ID
```

### `smoke-lz.sh`
Quick smoke test of /lz health and readiness endpoints.

**Usage**:
```bash
./scripts/deployment/smoke-lz.sh elevatediq.ai
```

### `configure-cloud-run-env.sh`
Legacy; use `setup-cloud-run-env.sh` instead.

---

## CI/CD Automation

Cloud Build pipeline (cloudbuild.yaml) includes:
- Terraform plan for terraform/04-workloads
- Conditional terraform apply (gated by `_APPLY_WORKLOADS=true`)
- Tfvars loaded from Secret Manager: `PORTAL_WORKLOADS_TFVARS`

### Setup

1. Create Secret Manager secret:
```bash
gcloud secrets create PORTAL_WORKLOADS_TFVARS \
  --data-file=/tmp/workloads.tfvars \
  --project=YOUR_PROJECT
```

2. Grant Cloud Build SA access:
```bash
gcloud secrets add-iam-policy-binding PORTAL_WORKLOADS_TFVARS \
  --member=serviceAccount:PROJECT_NUMBER@cloudbuild.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

3. Set build substitution:
- `_APPLY_WORKLOADS=true` to apply (default: false for plan-only)

---

## Documentation

- Full setup guide: `SETUP_LZ.md`
- Infrastructure: `terraform/04-workloads/lb/README.md`
- Deployment: `DEPLOYMENT.md`

---

**Status**: Production-ready automation stack
**Last Updated**: 2026-01-19
