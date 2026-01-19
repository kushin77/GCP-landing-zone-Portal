#!/bin/bash
#
# Folder Hierarchy Validation Script
# Enforces 5-layer depth pattern for Terraform and scripts
# Part of landing zone enforcement policy

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../../" && pwd)"

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Initialize counters
warnings=0
errors=0

echo "🔍 Validating 5-Layer Folder Hierarchy..."
echo "📁 Project Root: $project_root"
echo ""

# Check Terraform layers
echo "📦 Terraform Layers (Required: 01-05):"
terraform_dir="$project_root/terraform"

if [[ ! -d "$terraform_dir" ]]; then
    echo -e "${RED}❌ terraform/ directory not found${NC}"
    errors=$((errors + 1))
else
    required_layers=("01-foundation" "02-network" "03-security" "04-workloads" "05-observability")

    for layer in "${required_layers[@]}"; do
        if [[ -d "$terraform_dir/$layer" ]]; then
            echo -e "${GREEN}✅ $layer${NC}"
        else
            echo -e "${RED}❌ $layer (MISSING)${NC}"
            errors=$((errors + 1))
        fi
    done

    # Check for modules directory
    if [[ -d "$terraform_dir/modules" ]]; then
        echo -e "${GREEN}✅ modules/ (reusable components)${NC}"
    else
        echo -e "${YELLOW}⚠️  modules/ (optional but recommended)${NC}"
        warnings=$((warnings + 1))
    fi
fi

echo ""
echo "📂 Scripts Directories (Required):"
scripts_dir="$project_root/scripts"

if [[ ! -d "$scripts_dir" ]]; then
    echo -e "${RED}❌ scripts/ directory not found${NC}"
    errors=$((errors + 1))
else
    required_scripts=("automation" "bootstrap" "deployment" "lib" "maintenance" "monitoring" "security" "validation")

    for script_cat in "${required_scripts[@]}"; do
        if [[ -d "$scripts_dir/$script_cat" ]]; then
            echo -e "${GREEN}✅ $script_cat/${NC}"
        else
            echo -e "${RED}❌ $script_cat/ (MISSING)${NC}"
            errors=$((errors + 1))
        fi
    done
fi

echo ""
echo "📋 Summary:"
echo "  Errors: $errors"
echo "  Warnings: $warnings"

if [[ $errors -gt 0 ]]; then
    echo -e "${RED}❌ Validation FAILED - Fix errors before committing${NC}"
    exit 1
elif [[ $warnings -gt 0 ]]; then
    echo -e "${YELLOW}⚠️  Validation PASSED with warnings - Recommended improvements available${NC}"
    exit 0
else
    echo -e "${GREEN}✅ Validation PASSED - All layers present${NC}"
    exit 0
fi
