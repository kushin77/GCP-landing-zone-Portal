#!/usr/bin/env bash
set -euo pipefail

# Wire Cloud Run service environment variables for /lz deployment
# Usage: ./scripts/deployment/setup-cloud-run-env.sh <PROJECT_ID> <SERVICE_NAME> <REGION> <BACKEND_SERVICE_ID>

PROJECT_ID=${1:?Missing PROJECT_ID}
SERVICE_NAME=${2:-portal-backend}
REGION=${3:-us-central1}
BACKEND_SERVICE_ID=${4:?Missing BACKEND_SERVICE_ID (from terraform/04-workloads apply)}

echo "🔧 Setting up Cloud Run environment for /lz"
echo "  Project: $PROJECT_ID"
echo "  Service: $SERVICE_NAME"
echo "  Region: $REGION"
echo "  Backend Service ID: $BACKEND_SERVICE_ID"
echo ""

# Get project number
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)' 2>/dev/null || echo "")
if [[ -z "$PROJECT_NUMBER" ]]; then
  echo "❌ Failed to get project number. Check PROJECT_ID."
  exit 1
fi

# Build IAP audience
IAP_AUDIENCE="/projects/${PROJECT_NUMBER}/global/backendServices/${BACKEND_SERVICE_ID}"

echo "📝 IAP Audience: $IAP_AUDIENCE"
echo ""

# Set environment variables
echo "⏳ Updating Cloud Run service..."
gcloud run services update "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --set-env-vars=BASE_PATH=/lz,REQUIRE_AUTH=true,IAP_AUDIENCE="$IAP_AUDIENCE",ENVIRONMENT=production \
  --update-labels=app=landing-zone-portal,base_path=lz,oauth=iap \
  --quiet

echo "✅ Cloud Run service updated successfully"
echo ""

# Verify
echo "🔍 Verifying environment..."
gcloud run services describe "$SERVICE_NAME" \
  --region="$REGION" \
  --project="$PROJECT_ID" \
  --format='table(spec.template.spec.containers[0].env[].name,spec.template.spec.containers[0].env[].value)' | head -10

echo ""
echo "✨ Done! Cloud Run is ready for /lz"
echo ""
echo "Next: Verify with:"
echo "  curl -I https://elevatediq.ai/lz/health"
