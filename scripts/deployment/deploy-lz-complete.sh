#!/usr/bin/env bash
set -euo pipefail

# Complete automated setup for /lz deployment (requires all parameters)
# Usage: ./scripts/deployment/deploy-lz-complete.sh <PROJECT_ID> <DOMAIN> <BACKEND_SERVICE_ID>

PROJECT_ID=${1:?Missing PROJECT_ID}
DOMAIN=${2:-elevatediq.ai}
BACKEND_SERVICE_ID=${3:?Missing BACKEND_SERVICE_ID}

SERVICE_NAME="portal-backend"
REGION="us-central1"

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║            Deploying Landing Zone Portal to /lz                           ║"
echo "║            Project: $PROJECT_ID"
echo "║            Domain: $DOMAIN"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Cloud Run environment
echo "📍 Step 1/3: Configuring Cloud Run environment..."
./scripts/deployment/setup-cloud-run-env.sh "$PROJECT_ID" "$SERVICE_NAME" "$REGION" "$BACKEND_SERVICE_ID"
sleep 5

echo ""
echo "📍 Step 2/3: Waiting for Cloud Run to stabilize..."
sleep 30

# Step 3: Health check
echo "📍 Step 3/3: Running health checks..."
BACKEND_URL="https://${DOMAIN}/lz"

for i in {1..5}; do
  echo "  Attempt $i/5..."
  if curl -sfI "${BACKEND_URL}/health" > /dev/null 2>&1; then
    echo "✅ Health check passed!"
    break
  fi
  if [ $i -lt 5 ]; then
    sleep 10
  fi
done

echo ""
echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                       ✨ Deployment Complete ✨                            ║"
echo "║                                                                            ║"
echo "║  Portal URL:  $BACKEND_URL"
echo "║  API:         ${BACKEND_URL}/api/v1"
echo "║  Health:      ${BACKEND_URL}/health"
echo "║  Docs:        ${BACKEND_URL}/docs (dev only)"
echo "║                                                                            ║"
echo "║  Next: Test with curl -I $BACKEND_URL/health                             ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"
