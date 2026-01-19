#!/usr/bin/env bash
set -euo pipefail

# Configure Cloud Run service environment variables for BASE_PATH and IAP audience
# Usage: ./scripts/deployment/configure-cloud-run-env.sh <service-name> <region> <project-id> <iap-audience>

SERVICE_NAME=${1:-portal-backend}
REGION=${2:-us-central1}
PROJECT_ID=${3:-$(gcloud config get-value project)}
IAP_AUDIENCE=${4:-}

if [[ -z "$PROJECT_ID" ]]; then
  echo "PROJECT_ID not set" >&2
  exit 1
fi

if [[ -z "$IAP_AUDIENCE" ]]; then
  echo "IAP_AUDIENCE is required: /projects/{project_number}/global/backendServices/{service_id}" >&2
  exit 1
fi

echo "Configuring Cloud Run service $SERVICE_NAME in $REGION (project $PROJECT_ID)"

gcloud run services update "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --set-env-vars=BASE_PATH=/lz,REQUIRE_AUTH=true,IAP_AUDIENCE="$IAP_AUDIENCE" \
  --update-labels=app=landing-zone-portal,base_path=lz

echo "Done. Verify:
  gcloud run services describe $SERVICE_NAME --region=$REGION --project=$PROJECT_ID | grep -A2 env:
"
