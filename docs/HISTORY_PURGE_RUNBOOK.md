# Runbook: Purging Secret(s) from Git History

This runbook guides maintainers through a safe process to remove sensitive
secrets from repository history after the secret has been rotated and revoked.

Important: DO NOT perform this operation until the secret has been revoked and
rotated. Rewriting history is destructive and requires coordination.

Pre-checks
- Confirm secret rotation and revocation (issue #73).
- Notify all contributors and schedule a maintenance window.
- Ensure CI is paused for merges and branch protection is relaxed where necessary.
- Create a full mirror backup of the repository.

Steps (operator)

1) Create a mirror backup

```bash
git clone --mirror git@github.com:kushin77/GCP-landing-zone-Portal.git /tmp/repo-mirror
cd /tmp/repo-mirror
```

2) Decide approach
- To remove a file entirely (e.g., `API.md`) use `--invert-paths --paths API.md`.
- To replace secret substrings use `--replace-text replacements.txt` where
  `replacements.txt` contains lines of the form:

  ```text
  SECRET_TO_REMOVE==>REDACTED
  ```

3) Execute `git filter-repo` locally and verify

Example: remove `API.md` fully from history

```bash
git filter-repo --invert-paths --paths API.md

# Run scans to validate
gitleaks detect --source . --report-format json --report-path /tmp/gitleaks-after.json || true
detect-secrets scan || true
```

4) Manual verification
- Inspect `gitleaks` and `detect-secrets` outputs to ensure no secret fingerprints remain.
- Run test and CI checks locally if possible.

5) Force-push cleaned history (ONLY AFTER APPROVAL)

```bash
git push --force --all origin
git push --force --tags origin
```

6) Post-purge remediation
- Notify contributors to reclone the repo.
- Re-enable branch protection and CI gates.
- Re-run full pipeline scans and confirm issue #73 closure.

Notes
- Consider preserving a copy of the original mirror for forensic audit.
- BFG is an alternative to `git filter-repo` for some use-cases.
