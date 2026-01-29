#!/usr/bin/env bash
set -euo pipefail

# scripts/gsm_migrate.sh
# Safe helper to create a GCP Secret Manager secret or add a new version.
# Usage:
# 1) Export PROJECT_ID
# 2) Provide secret name as first arg, and pipe the secret value via stdin:
#    echo -n "mysecret" | ./scripts/gsm_migrate.sh portal-auth-token
# The script will create the secret if it does not exist, otherwise add a new version.

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <secret-name>" >&2
  exit 2
fi

SECRET_NAME="$1"
PROJECT_ID="${PROJECT_ID:-}"
if [ -z "$PROJECT_ID" ]; then
  echo "Please set PROJECT_ID environment variable." >&2
  exit 2
fi

# Read secret from stdin
if [ -t 0 ]; then
  echo "Reading secret from stdin; pipe the secret value to this script." >&2
  exit 2
fi

SECRET_VALUE_FILE=$(mktemp)
trap 'rm -f "$SECRET_VALUE_FILE"' EXIT
cat - > "$SECRET_VALUE_FILE"

# Check if secret exists
if gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "Secret exists; adding new version: $SECRET_NAME"
  gcloud secrets versions add "$SECRET_NAME" --data-file="${SECRET_VALUE_FILE}" --project="$PROJECT_ID"
else
  echo "Creating secret: $SECRET_NAME"
  gcloud secrets create "$SECRET_NAME" --replication-policy="automatic" --data-file="${SECRET_VALUE_FILE}" --project="$PROJECT_ID"
fi

echo "Done. Secret $SECRET_NAME migrated to GCP Secret Manager (project: $PROJECT_ID)."
