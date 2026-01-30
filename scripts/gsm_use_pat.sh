#!/usr/bin/env bash
set -euo pipefail

# Fetch a GitHub PAT from Google Secret Manager and authenticate GH CLI.
# Usage: ./scripts/gsm_use_pat.sh [SECRET_NAME]
# Example:
#   ./scripts/gsm_use_pat.sh github-pat

SECRET_NAME=${1:-github-pat}
PROJECT_ID=${GCP_PROJECT_ID:-${PROJECT_ID:-}}

if [ -z "$PROJECT_ID" ]; then
  echo "GCP project not set. Set GCP_PROJECT_ID or PROJECT_ID environment variable." >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found. Install GitHub CLI (https://cli.github.com/) and try again." >&2
  exit 1
fi

echo "Fetching PAT from Secret Manager (secret: $SECRET_NAME)..."

# Fetch secret and pipe into gh auth login --with-token
gcloud secrets versions access latest --secret="$SECRET_NAME" --project="$PROJECT_ID" \
  | gh auth login --with-token

echo "GH CLI authenticated using secret: $SECRET_NAME"
