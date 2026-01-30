# Store GitHub PAT in Google Secret Manager (GSM) and use GH CLI

Purpose
- Securely store a GitHub Personal Access Token (PAT) in Google Secret Manager (GSM) for global CI and local developer use, and authenticate the GitHub CLI (`gh`) from the secret without exposing the token.

Security note
- Do NOT paste your PAT into chat or store it in plain text. Use the commands below locally. Rotate the secret regularly and grant `roles/secretmanager.secretAccessor` only to minimal service accounts or workload-identity principals.

Prerequisites
- `gcloud` CLI configured with access to the target GCP project.
- `gh` CLI installed for interactive PR creation and `git` configured locally.
- Optional helper scripts are included at `scripts/gsm_store_pat.sh` and `scripts/gsm_use_pat.sh`.

Quick steps (recommended)

1) Create the secret or add a new version from stdin (helper script):

```bash
# replace YOUR_GITHUB_PAT with your PAT value (do not share)
printf '%s' "YOUR_GITHUB_PAT" | ./scripts/gsm_store_pat.sh github-pat
```

2) Grant access to CI/service accounts or Workload Identity principals:

```bash
# replace values below
gcloud secrets add-iam-policy-binding github-pat \
  --project=YOUR_GCP_PROJECT \
  --member="serviceAccount:CI_SA@YOUR_GCP_PROJECT.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

3) Authenticate the `gh` CLI locally from GSM (helper script):

```bash
# fetch secret and authenticate gh non-interactively
GCP_PROJECT_ID=YOUR_GCP_PROJECT ./scripts/gsm_use_pat.sh github-pat
```

4) Push branch and create PR (example):

```bash
git checkout fix/critical-issues-closure
git push -u origin fix/critical-issues-closure
gh pr create --title "Critical infra fixes: resolve #40–#49" \
  --body "See CRITICAL_ISSUES_RESOLUTION.md for details." --base main
```

Alternative: `gcloud secrets` directly

```bash
printf '%s' "YOUR_GITHUB_PAT" | gcloud secrets create github-pat \
  --project=YOUR_GCP_PROJECT --replication-policy="automatic" --data-file=-

# or add a new version to existing secret
printf '%s' "YOUR_GITHUB_PAT" | gcloud secrets versions add github-pat --project=YOUR_GCP_PROJECT --data-file=-
```

Workload Identity recommendation (CI automation)
- Create a GCP service account for CI (e.g., `ci-secrets@PROJECT.iam.gserviceaccount.com`).
- Configure Workload Identity Pool and provider for your GitHub repo and grant the pool principals `roles/iam.workloadIdentityUser` on the SA.
- Give that SA `roles/secretmanager.secretAccessor` on the `github-pat` secret.

Rotation and audit
- Add a rotation schedule for the secret and record rotation steps in your runbook. Monitor Secret Manager access logs in Cloud Audit Logs for anomalous reads.

Files referenced
- `scripts/gsm_store_pat.sh` — helper to create/add secret versions from stdin
- `scripts/gsm_use_pat.sh` — helper to fetch secret and run `gh auth login --with-token`
- `CRITICAL_ISSUES_RESOLUTION.md` — justification and PR content for `fix/critical-issues-closure`

If you want, I can push `fix/critical-issues-closure` and open the PR after you store the PAT in GSM and grant access (or provide a PAT for me to use temporarily). I will not accept tokens in chat unless you explicitly confirm and understand the risk.
