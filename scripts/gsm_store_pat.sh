#!/usr/bin/env bash
set -euo pipefail

# Store a GitHub PAT in Google Secret Manager securely.
# Usage: echo "<PAT>" | ./scripts/gsm_store_pat.sh [SECRET_NAME]
# Or: ./scripts/gsm_store_pat.sh <SECRET_NAME> (reads PAT from stdin)

SECRET_NAME=${1:-github-pat}
PROJECT_ID=${GCP_PROJECT_ID:-${PROJECT_ID:-}}

usage() {
  cat <<EOF
Usage: echo "<PAT>" | $0 [SECRET_NAME]

Stores the provided PAT into Google Secret Manager as a new version.
If the secret does not exist, it will be created with automatic replication.
EOF
}

if [ -t 0 ]; then
  echo "Reading PAT from stdin..."
fi

PAT=$(cat -)

if [ -z "$PAT" ]; then
  echo "No PAT provided on stdin. Aborting." >&2
  usage
  exit 1
fi

if [ -z "$PROJECT_ID" ]; then
  echo "GCP project not set. Set GCP_PROJECT_ID or PROJECT_ID environment variable." >&2
  exit 1
fi

# NOTE: do NOT enable shell debugging (`set -x`) in this script - it can leak
# secrets into CI logs. Keep the script quiet and avoid echoing sensitive
# values.

# Create secret if it doesn't exist
if ! gcloud secrets describe "$SECRET_NAME" --project="$PROJECT_ID" >/dev/null 2>&1; then
  gcloud secrets create "$SECRET_NAME" \
    --replication-policy="automatic" \
    --project="$PROJECT_ID"
fi

# Add new version from stdin
echo -n "$PAT" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$PROJECT_ID"

echo "PAT stored in secret: projects/$PROJECT_ID/secrets/$SECRET_NAME"
