#!/bin/bash
# Security validation script
# Usage: ./scripts/validation/security-check.sh

set -euo pipefail

echo "🔒 Running security checks..."

# 1. Secret scanning
echo "1️⃣  Scanning for secrets in code..."
if command -v gitleaks &> /dev/null; then
  gitleaks detect --source git --verbose || exit 1
else
  echo "⚠️  gitleaks not installed, skipping secret scan"
fi

# 1b. Background secret detection (detect-secrets)
if command -v detect-secrets &> /dev/null; then
  echo "🔍 Running detect-secrets..."
  detect-secrets scan --exclude-files '.*\.baseline' > .secrets.new
  if [ -f .secrets.baseline ]; then
    detect-secrets audit .secrets.baseline .secrets.new || echo "⚠️  New secrets detected outside baseline!"
  fi
  rm .secrets.new
fi

# 2. Dependency scanning
echo ""
echo "2️⃣  Scanning dependencies..."
if command -v snyk &> /dev/null; then
  snyk test --severity-threshold=high || exit 1
else
  echo "⚠️  Snyk not installed"
fi

# 2b. SAST (Semgrep)
echo ""
echo "3️⃣  Running SAST (Semgrep)..."
if command -v semgrep &> /dev/null; then
  semgrep scan --config auto --error || exit 1
else
  echo "⚠️  Semgrep not installed"
fi

# 3. Terraform security
echo ""
echo "3️⃣  Checking Terraform security..."
if command -v tfsec &> /dev/null; then
  tfsec terraform/ --minimum-severity MEDIUM || exit 1
else
  echo "⚠️  tfsec not installed"
fi

echo ""
echo "✅ Security checks passed!"
