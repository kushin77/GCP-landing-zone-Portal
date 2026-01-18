#!/bin/bash
# Deployment script for Portal to staging environment
# Usage: ./scripts/deployment/deploy-staging.sh

set -euo pipefail

ENVIRONMENT="staging"
PROJECT_ID="${PORTAL_STAGING_PROJECT_ID:?'PORTAL_STAGING_PROJECT_ID not set'}"
REGION="us-central1"
FRONTEND_SERVICE="portal-frontend"
BACKEND_SERVICE="portal-backend"

echo "🚀 Deploying Portal to ${ENVIRONMENT}..."
echo "📦 Project: ${PROJECT_ID}"
echo "🌍 Region: ${REGION}"

# 1. Build Docker image
echo ""
echo "1️⃣  Building Docker image..."
docker build -t gcr.io/${PROJECT_ID}/portal:latest .

# 2. Push to Artifact Registry
echo ""
echo "2️⃣  Pushing to Artifact Registry..."
docker push gcr.io/${PROJECT_ID}/portal:latest

# 3. Deploy backend to Cloud Run
echo ""
echo "3️⃣  Deploying backend service..."
gcloud run deploy ${BACKEND_SERVICE} \
  --image gcr.io/${PROJECT_ID}/portal:latest \
  --platform managed \
  --region ${REGION} \
  --project ${PROJECT_ID} \
  --set-env-vars="ENVIRONMENT=${ENVIRONMENT},PROJECT_ID=${PROJECT_ID}" \
  --min-instances 1 \
  --max-instances 50 \
  --memory 2Gi \
  --cpu 2 \
  --no-allow-unauthenticated

# 4. Configure IAP
echo ""
echo "4️⃣  Configuring Identity-Aware Proxy..."
# TODO: Add IAP configuration

# 5. Run smoke tests
echo ""
echo "5️⃣  Running smoke tests..."
# TODO: Add smoke test script

echo ""
echo "✅ Deployment to ${ENVIRONMENT} complete!"
