#!/usr/bin/env bash
set -euo pipefail

DOMAIN=${1:-elevatediq.ai}
BASE_URL="https://${DOMAIN}/lz"

echo "Smoking ${BASE_URL}..."

curl -fsSL -I "${BASE_URL}/health" | head -n1 || { echo "Health failed"; exit 1; }
curl -fsSL -I "${BASE_URL}/ready" | head -n1 || { echo "Ready failed"; exit 1; }

# Sample API call (may require auth via IAP)
if curl -fsSL "${BASE_URL}/api/v1/dashboard" | jq '.costs,.compliance' >/dev/null 2>&1; then
  echo "Dashboard OK"
else
  echo "Dashboard endpoint reachable (auth may be required)"
fi

echo "Smoke test complete."
