#!/bin/bash
#
# HCL Syntax Validation Script
# Pre-commit hook to validate Terraform HCL files
# Usage: hcl-syntax-check.sh <file1> [file2] ...

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
project_root="$(cd "$script_dir/../../../" && pwd)"

# Track exit code
exit_code=0

# Validate Terraform syntax
validate_terraform_syntax() {
    local file="$1"

    if ! terraform -chdir="${file%/*}" fmt -check "$file" 2>/dev/null; then
        echo "ERROR: Terraform formatting issue in $file"
        echo "Run: terraform fmt $file"
        return 1
    fi

    return 0
}

# Main validation
if [[ $# -eq 0 ]]; then
    echo "Usage: hcl-syntax-check.sh <file1> [file2] ..."
    exit 1
fi

for file in "$@"; do
    if [[ "$file" == *.tf ]]; then
        if ! validate_terraform_syntax "$file"; then
            exit_code=1
        fi
    fi
done

exit $exit_code
