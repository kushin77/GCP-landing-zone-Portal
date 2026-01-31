#!/usr/bin/env bash
set -euo pipefail

# purge_history.sh
# Safely prepares commands to purge sensitive data from git history using
# git-filter-repo. THIS SCRIPT DOES NOT RUN THE DESTRUCTIVE PUSH. It creates a
# cleaned mirror in a separate folder and verifies results. Operators must
# manually review and execute the force-push when ready.

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <backup-dir>"
  echo "Example: $0 /tmp/repo-mirror"
  exit 1
fi

BACKUP_DIR="$1"
REPO_URL=$(git config --get remote.origin.url || true)

if [ -z "$REPO_URL" ]; then
  echo "Cannot determine origin remote URL. Run this script from a clone with origin set." >&2
  exit 2
fi

echo "Creating mirror backup: $BACKUP_DIR"
git clone --mirror "$REPO_URL" "$BACKUP_DIR"

cat <<'EOF'
DONE: mirror created.

Next manual steps (review before running):

1) Enter the mirror directory:
   cd "${BACKUP_DIR}"

2) OPTIONAL: Create a mapping file for --replace-text to redact secrets instead
   of deleting files. Example mapping file `replacements.txt`:

   "password123"==>REDACTED

   Use:
   git filter-repo --replace-text replacements.txt

3) To remove a file entirely from history (e.g., API.md), run:
   git filter-repo --invert-paths --paths API.md

4) Verify the repo is clean:
   gitleaks detect --source . || gitleaks detect --source . --redact
   detect-secrets scan || true

5) When satisfied, coordinate a maintenance window and force-push the cleaned
   mirror to origin (operator action only):
   git push --force --all origin
   git push --force --tags origin

WARNING: This rewrites git history and will require all contributors to reclone.
Coordinate with stakeholders before pushing.
EOF

echo "Prepared mirror at: $BACKUP_DIR. Manual review required before force-push."
