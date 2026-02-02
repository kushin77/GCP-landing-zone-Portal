# Critical Onboarding Tasks — Execution Guide

This guide provides step-by-step instructions for executing the critical onboarding tasks (#104-107).

## Prerequisites

Ensure you have:
- GitHub admin access to the repository
- GCP project owner/editor access
- `gh` CLI installed and authenticated
- `gcloud` CLI installed and authenticated
- SSH access to GCP console or Cloud Shell

## Task #104: Rotate Compromised Token

**Status:** ⏳ In Progress
**Estimated Duration:** 1-2 hours
**Owner:** @kushin77

### Steps

1. **Generate New GitHub PAT**
   ```bash
   # Go to https://github.com/settings/tokens
   # Create new PAT with scopes: repo, workflow
   # Copy the new token value
   NEW_PAT="ghp_your_new_token_here"
   ```

2. **Store New PAT in Google Secret Manager**
   ```bash
   export GCP_PROJECT_ID="your-gcp-project"
   echo "$NEW_PAT" | ./scripts/gsm_store_pat.sh github-pat
   ```

3. **Revoke Old PAT**
   - Go to https://github.com/settings/tokens
   - Find the compromised token
   - Click "Delete" or "Revoke"
   - Confirm revocation

4. **Update CI/CD Configuration**
   - Update `cloudbuild.yaml` to use GSM secret instead of GitHub Secrets
   - See Task #105 for detailed steps

5. **Verify Rotation**
   - Test that new PAT works: `gh auth status`
   - Check GCP secret: `gcloud secrets versions list github-pat`
   - Confirm old token is no longer accessible

6. **Audit Log Check**
   ```bash
   # Check GitHub audit log for any unauthorized use
   gh api orgs/kushin77/audit-log --limit 100
   ```

7. **Close Issue #104**
   - Mark all acceptance criteria as complete
   - Add comment with rotation timestamp
   - Close issue with label `security-resolved`

---

## Task #105: Migrate Secrets to Google Secret Manager

**Status:** ⏳ In Progress
**Estimated Duration:** 2-4 hours
**Owner:** @kushin77
**Depends on:** Task #104

### Steps

1. **Audit Current Secrets**
   ```bash
   # List GitHub Secrets
   gh secret list

   # List GCP Secrets
   gcloud secrets list --project="${GCP_PROJECT_ID}"
   ```

2. **Store All Secrets in GSM**
   ```bash
   # Store each secret with the format:
   # echo "<SECRET_VALUE>" | ./scripts/gsm_store_pat.sh <SECRET_NAME>

   echo "$GITHUB_PAT" | ./scripts/gsm_store_pat.sh github-pat
   # Repeat for each secret: GCP_SA_KEY, API_KEY, etc.
   ```

3. **Update cloudbuild.yaml**
   ```yaml
   steps:
     - name: 'gcr.io/cloud-builders/gcloud'
       args: ['secrets', 'versions', 'access', 'latest', '--secret', 'github-pat']
       env:
         - 'GITHUB_TOKEN=secretManager:github-pat'
   ```

4. **Test CI Pipeline**
   ```bash
   # Trigger a test build
   gcloud builds submit --config=cloudbuild.yaml
   ```

5. **Disable GitHub Secrets**
   - Go to repo Settings > Secrets and variables
   - Remove or disable old GitHub Secrets
   - Verify CI still works

6. **Document Migration**
   - Update README with GSM secret setup instructions
   - Document each secret's purpose and usage
   - Add troubleshooting guide

7. **Close Issue #105**
   - Mark all acceptance criteria as complete
   - Link to updated cloudbuild.yaml
   - Close issue with label `security-resolved`

---

## Task #106: Verify CI Pipelines

**Status:** ⏳ In Progress
**Estimated Duration:** 1-2 hours
**Owner:** @kushin77
**Depends on:** Tasks #104-105

### Steps

1. **Check Build Status**
   ```bash
   # View recent builds
   gcloud builds list --limit=5

   # View detailed build log
   gcloud builds log <BUILD_ID>
   ```

2. **Verify Test Execution**
   ```bash
   # Run tests locally
   cd backend
   pytest -v --cov

   # Check coverage threshold
   ```

3. **Create CI Checklist Document**
   - Create `docs/CI_CHECKLIST.md`
   - List pre-commit checks
   - List test execution requirements
   - List coverage thresholds
   - List build validation steps

4. **Fix Any Failing Builds**
   - Diagnose failures in build logs
   - Apply fixes to codebase
   - Re-run builds until all pass

5. **Document CI Status**
   - Add CI badge to README
   - Link to build dashboard
   - Document how to view CI status

6. **Close Issue #106**
   - Mark all acceptance criteria as complete
   - Link to CI dashboard
   - Close issue

---

## Task #107: Document Test Commands & Pytest Workflow

**Status:** ⏳ In Progress
**Estimated Duration:** 1-2 hours
**Owner:** @kushin77

### Steps

1. **Document Test Commands**
   - Create `docs/TESTING.md`
   - Add: `pytest` (unit/integration tests)
   - Add: `pytest -v --cov` (with coverage)
   - Add: coverage threshold requirements

2. **Verify pytest Configuration**
   ```bash
   # Check pytest.ini
   cat backend/pytest.ini

   # Run with verbose output
   pytest -v backend/tests/
   ```

3. **Create Test Fixtures Documentation**
   - Document common fixtures
   - Add examples of fixture usage
   - Document test utilities

4. **Document CI Pytest Workflow**
   - Add section to cloudbuild.yaml for pytest
   - Document expected test discovery patterns
   - Document naming conventions for tests

5. **Add Sample Test Output**
   - Run tests and capture output
   - Include in documentation
   - Show coverage report format

6. **Close Issue #107**
   - Mark all acceptance criteria as complete
   - Link to TESTING.md documentation
   - Close issue

---

## Success Criteria

All 4 critical tasks (#104-107) are complete when:

- ✅ Token rotation confirmed (old token revoked, new token in use)
- ✅ All secrets migrated to GSM (GitHub Secrets disabled)
- ✅ CI pipelines passing (all builds green)
- ✅ Test documentation complete (TESTING.md created)
- ✅ All 4 issues closed with acceptance criteria met

---

## Troubleshooting

### Token Rotation Issues
- **Problem:** New token not working
  - **Solution:** Verify token scopes (repo, workflow)
  - **Solution:** Check GitHub auth status: `gh auth status`

### GSM Secret Issues
- **Problem:** Secret not accessible in Cloud Build
  - **Solution:** Check service account permissions
  - **Solution:** Verify secret exists: `gcloud secrets describe <name>`

### CI Pipeline Issues
- **Problem:** Build failing with permission error
  - **Solution:** Check service account has required roles
  - **Solution:** Check secret is properly injected in cloudbuild.yaml

---

**Last Updated:** 2026-01-29
**Related Issues:** #104, #105, #106, #107
**Parent Epic:** #90 (Secrets & IAM)
