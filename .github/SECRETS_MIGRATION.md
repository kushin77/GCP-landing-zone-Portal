# Secrets Migration to GCP Secret Manager

This document describes safe, repeatable steps to migrate repository secrets into GCP Secret Manager and remove plaintext secrets from the repo.

Principles
- Never store secrets in git history or plaintext files. Use Secret Manager for runtime/CI secrets.
- Use Workload Identity or short-lived credentials for CI to access secrets; avoid long-lived JSON keys in repositories.
- Rotate and revoke any exposed credentials prior to history rewrite.

Preflight
1. Identify plaintext secrets in the repository with `gitleaks` or `detect-secrets`.
2. Rotate/revoke compromised secrets before migration (see issue #73 for token rotation steps).
3. Add a `.secrets.baseline` and ensure `detect-secrets` runs locally and in CI.

Migration (example)

Create secret (one-time):

```bash
# Create a secret from stdin
SECRET_NAME=portal-auth-token
PROJECT_ID=my-gcp-project
echo -n "$NEW_SECRET" | gcloud secrets create "$SECRET_NAME" --data-file=- --replication-policy="automatic" --project="$PROJECT_ID"
```

Add a new version (if secret exists):

```bash
echo -n "$NEW_SECRET" | gcloud secrets versions add "$SECRET_NAME" --data-file=- --project="$PROJECT_ID"
```

CI / Runtime access patterns
- Use Workload Identity (recommended) for Cloud Build and GitHub Actions with short-lived tokens.
- Do not store raw secret values in repository settings or CI logs.
- Example in Cloud Build: bind build service account to access secret versions.

Removal from repo and history purge
1. Replace plaintext occurrences in files with a reference or placeholder and a short note pointing to Secret Manager (e.g., `See .github/SECRETS_MIGRATION.md`).
2. After rotation and validation, schedule a history purge (BFG or `git filter-repo`) using the guarded runbook in `docs/HISTORY_PURGE_RUNBOOK.md`.

Verification
- Run `detect-secrets` and `gitleaks` after migration and after history purge to confirm no leakage remains.

Example scripts
- `scripts/gsm_migrate.sh` — helper to create secrets or add versions from stdin (safe, non-destructive). Use it as an example and adapt per org policy.

Owners: Security + DevOps
