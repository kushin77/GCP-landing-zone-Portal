#!/bin/bash

# Simple connectivity check for Landing Zone Portal backend
# Usage: PORTAL_HOST=192.168.168.42 PORTAL_PORT=8082 ./scripts/check_connectivity.sh

HOST=${PORTAL_HOST:-localhost}
PORT=${PORTAL_PORT:-8082}

URL="http://${HOST}:${PORT}/health"

echo "Checking portal health at: ${URL}"

if command -v curl >/dev/null 2>&1; then
  curl -fsS -m 5 "${URL}" || (echo "FAILED to reach ${URL}" && exit 2)
  echo "OK"
  exit 0
else
  echo "curl not available — please install curl to perform connectivity test"
  exit 3
fi
