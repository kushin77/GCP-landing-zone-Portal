#!/bin/bash
# FAANG-Grade Token Rotation Utility
# Handles rotation of GitHub PATs and GCP Secrets

set -e

# Configuration
SECRET_NAME="GITHUB_PAT"
PROJECT_ID=$(gcloud config get-value project)

echo "Starting Token Rotation process for $SECRET_NAME..."

# 1. Verify GitHub CLI is authenticated
if ! gh auth status &>/dev/null; then
  echo "Error: gh CLI not authenticated. Please run 'gh auth login'."
  exit 1
fi

# 2. Check if a new token is provided as an argument
if [ -z "$1" ]; then
  echo "Usage: $0 <new_token_value>"
  echo "Wait! You must generate a new PAT at https://github.com/settings/tokens first."
  exit 1
fi

NEW_TOKEN="$1"

# 3. Update GCP Secret Manager
echo "Updating GCP Secret Manager: $SECRET_NAME in project $PROJECT_ID..."
echo -n "$NEW_TOKEN" | gcloud secrets versions add "$SECRET_NAME" --data-file=-

echo "✅ Secret updated in GCP Secret Manager."

# 4. Verify the new secret
LATEST_VERSION=$(gcloud secrets versions list "$SECRET_NAME" --limit=1 --format="value(name)")
echo "New secret version: $LATEST_VERSION"

# 5. Instructions for environment sync
echo ""
echo "===================================================="
echo "ROTATION STEPS COMPLETE"
echo "===================================================="
echo "1. The newest version is now active."
echo "2. CI/CD pipelines (Cloud Build) will pick up the new secret in the next run."
echo "3. Monitor backend logs for any authentication errors."
echo "4. IMPORTANT: Revoke the old token at https://github.com/settings/tokens after confirming the new one works."
echo "===================================================="
