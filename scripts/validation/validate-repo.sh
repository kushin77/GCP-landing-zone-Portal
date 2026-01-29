#!/bin/bash
# Validation script for repository structure and required files
# Usage: ./scripts/validation/validate-repo.sh

set -euo pipefail

echo "🔍 Validating repository structure..."

REQUIRED_FILES=(
  "README.md"
  "CONTRIBUTING.md"
  "SECURITY.md"
  ".gitignore"
  ".editorconfig"
  ".pre-commit-config.yaml"
  "run.sh"
  "pmo.yaml"
  "frontend/package.json"
  "backend/requirements.txt"
  "backend/pytest.ini"
  "terraform/01-foundation/main.tf"
  "docs/api/API.md"
  "docs/architecture/ARCHITECTURE.md"
  "docs/operations/DEPLOYMENT.md"
  "docs/operations/RUNBOOKS.md"
)

echo "📋 Checking required files..."
MISSING=0
for file in "${REQUIRED_FILES[@]}"; do
  if [ -f "$file" ]; then
    echo "✅ $file"
  else
    echo "❌ MISSING: $file"
    MISSING=$((MISSING + 1))
  fi
done

if [ $MISSING -gt 0 ]; then
  echo ""
  echo "❌ Missing $MISSING required files"
  exit 1
fi

echo ""
echo "✅ All required files present!"

# Check folder structure
echo ""
echo "📁 Checking folder structure (5-layer Terraform)..."
REQUIRED_DIRS=(
  "frontend/src"
  "backend/services"
  "terraform/01-foundation"
  "terraform/02-network"
  "terraform/03-security"
  "terraform/04-workloads"
  "terraform/05-observability"
  "terraform/modules"
  "scripts/deployment"
  "scripts/security"
  "scripts/validation"
  "docs/api"
  "docs/architecture"
  "docs/operations"
)

for dir in "${REQUIRED_DIRS[@]}"; do
  if [ -d "$dir" ]; then
    echo "✅ $dir/"
  else
    echo "❌ MISSING: $dir/"
    MISSING=$((MISSING + 1))
  fi
done

if [ $MISSING -gt 0 ]; then
  echo ""
  echo "❌ Missing $MISSING required directories"
  exit 1
fi

echo ""
echo "✅ Repository structure is valid!"
