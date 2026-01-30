# 04 WORKLOADS Layer

Infrastructure layer for GCP Landing Zone Portal.

## Deploy

```bash
cd terraform
terraform -chdir=04-workloads init
terraform -chdir=04-workloads plan
terraform -chdir=04-workloads apply
```

## Status

🚧 Implementation in progress...

## Load Balancer + IAP for /lz

This layer now includes an HTTPS Load Balancer that serves the portal at `/lz`, routes `/lz/api/*` to the backend (Cloud Run), `/lz/*` to the frontend bucket (SPA), and enables IAP on the API backend.

### Inputs (see `variables.tf`)
- `project_id`
- `region` (default `us-central1`)
- `domain` (e.g., `elevatediq.ai`)
- `frontend_bucket` (e.g., `${project_id}-frontend`)
- `cloud_run_service_name` (e.g., `portal-backend`)
- `iap_client_id`, `iap_client_secret` (from your Landing Zone OAuth client)

### Example tfvars
See `terraform.tfvars.example`:

```
project_id               = "YOUR_PROJECT_ID"
region                   = "us-central1"
domain                   = "elevatediq.ai"
frontend_bucket          = "YOUR_PROJECT_ID-frontend"
cloud_run_service_name   = "portal-backend"
iap_client_id            = "YOUR_IAP_CLIENT_ID"
iap_client_secret        = "YOUR_IAP_CLIENT_SECRET"
```

### Apply

```bash
cd terraform/04-workloads
terraform init
terraform apply -var-file=terraform.tfvars
```

### Verify

```bash
./scripts/deployment/smoke-lz.sh elevatediq.ai
```
