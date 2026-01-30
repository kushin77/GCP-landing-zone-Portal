# Secrets Management Runbook

This document outlines the process for managing secrets in the GCP Landing Zone Portal.

## Secret Creation

### Google Secret Manager

Use GSM for all sensitive data:

```bash
# Create secrets
gcloud secrets create portal-backend-key --data-file=service-account.json
gcloud secrets create portal-db-password --data-file=password.txt

# Grant access to service account
gcloud secrets add-iam-policy-binding portal-backend-key \
  --member="serviceAccount:portal-backend@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### GitHub Secrets

For CI/CD:

1. Go to Repository Settings > Secrets and variables > Actions
2. Add secrets:
   - `GCP_SA_KEY`: Service account key JSON
   - `GCP_PROJECT_ID`: Project ID
   - `SNYK_TOKEN`: Snyk API token (optional)

## Secret Rotation

### Compromised Secrets

1. **Immediate Actions**:
   - Revoke compromised tokens/keys
   - Generate new credentials
   - Update GSM with new versions

2. **Update References**:
   - GitHub secrets
   - CI configurations
   - Application code

3. **Validation**:
   - Test CI pipelines
   - Verify application functionality
   - Monitor for anomalies

### Scheduled Rotation

Rotate secrets quarterly:

1. Generate new credentials
2. Update GSM (create new version)
3. Update references
4. Test and validate
5. Delete old versions after grace period

## IAM Grants

### Service Accounts

- `portal-backend`: `roles/secretmanager.secretAccessor`
- `ci-service-account`: `roles/secretmanager.secretAccessor`, `roles/cloudbuild.builds.editor`

### Users

Grant minimal required roles for secret access.

## Validation

### Test Secret Access

```bash
# Test GSM access
gcloud secrets versions access latest --secret=portal-backend-key

# Test in CI
# Check workflow logs for successful secret retrieval
```

### Audit Logs

Monitor Cloud Audit Logs for secret access:

```bash
gcloud logging read "resource.type=secretmanager.googleapis.com/Secret" \
  --limit=10
```