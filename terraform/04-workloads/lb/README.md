# Landing Zone Portal - HTTPS LB + IAP Module

This Terraform module provisions an HTTPS Load Balancer serving the portal under `/lz`, with:

- Managed SSL cert for `domain`
- URL map routing `/lz/api/*` to Cloud Run backend and `/lz/*` to a GCS backend bucket
- Serverless NEG attaching the Cloud Run service
- IAP enabled on the backend service (OAuth client provided by Landing Zone)

## Inputs

- `project_id`: GCP project ID
- `region`: Region for the serverless NEG (e.g., `us-central1`)
- `domain`: Public domain (e.g., `elevatediq.ai`)
- `frontend_bucket`: GCS bucket hosting the SPA assets
- `cloud_run_service_name`: Cloud Run service name for backend API
- `iap_client_id`: IAP OAuth client ID
- `iap_client_secret`: IAP OAuth client secret

## Usage

```hcl
module "portal_lb" {
  source                 = "./lb"
  project_id             = var.project_id
  region                 = var.region
  domain                 = "elevatediq.ai"
  frontend_bucket        = "${var.project_id}-frontend"
  cloud_run_service_name = "portal-backend"
  iap_client_id          = var.iap_client_id
  iap_client_secret      = var.iap_client_secret
}
```

## Notes

- Ensure the Cloud Run service is deployed and accessible before attaching via serverless NEG.
- IAP requires an OAuth consent brand and client. Provide the client ID/secret via variables.
- The backend FastAPI app must be configured with `BASE_PATH=/lz`.
- The frontend build must use `VITE_PUBLIC_BASE_PATH=/lz/`.
- Optionally forward `X-Forwarded-Prefix: /lz` from a proxy.

## Verification

```bash
# After apply:
curl -I https://elevatediq.ai/lz/health
curl -I https://elevatediq.ai/lz/ready
```
