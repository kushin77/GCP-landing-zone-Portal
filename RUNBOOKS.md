# Portal Runbooks

Operational playbooks for incident response, disaster recovery, and routine maintenance of the GCP Landing Zone Portal.

## Table of Contents

- [Incident Response](#incident-response)
- [Disaster Recovery](#disaster-recovery)
- [Operational Procedures](#operational-procedures)
- [Troubleshooting](#troubleshooting)

---

## Incident Response

### P1: Backend API Down

**Severity**: Critical | **SLA**: 15 minutes to resolution  
**Impact**: Users cannot access Portal functionality

#### Detection
- Alert: `backend-service-unhealthy` triggered
- Monitoring: Cloud Monitoring dashboard shows 0 successful requests

#### Response Steps

**1. Immediate Actions (0-5 min)**
```bash
# Check service status
gcloud run services describe portal-backend --region us-central1

# View recent logs
gcloud logging read \
  "resource.type=cloud_run_revision \
   AND resource.labels.service_name=portal-backend \
   AND severity=ERROR" \
  --limit 50 --format json | jq '.'

# Check recent deployments
gcloud run services describe portal-backend --region us-central1 \
  --format 'value(status.traffic[0].revision.name)'
```

**2. Diagnosis (5-15 min)**

If recent deployment:
```bash
# View deployment details
gcloud run services describe portal-backend --region us-central1 \
  --format 'value(status.traffic)'

# Check application logs for errors
gcloud logging read \
  "severity=ERROR resource.type=cloud_run_revision" \
  --limit 100 | grep -i "error\|exception"
```

If infrastructure issue:
```bash
# Check Cloud SQL connectivity
gcloud sql instances describe portal-db --format 'value(state)'

# Check Secret Manager access
gcloud secrets versions access latest --secret=db-password

# Check network connectivity
gcloud compute instances list --filter="zone:(us-central1-*)"
```

**3. Remediation**

Option A: Restart service
```bash
gcloud run deploy portal-backend \
  --image gcr.io/PROJECT/portal-backend:latest \
  --region us-central1 \
  --no-traffic  # Deploy without switching traffic

# Monitor new revision
gcloud logging read \
  "resource.type=cloud_run_revision" \
  --limit 20

# Switch traffic when healthy
gcloud run services update-traffic portal-backend \
  --to-revisions latest=100 \
  --region us-central1
```

Option B: Rollback to previous version
```bash
# Get previous revision
PREV_REVISION=$(gcloud run services describe portal-backend \
  --region us-central1 \
  --format 'value(status.traffic[1].revision.name)')

# Switch traffic to previous
gcloud run services update-traffic portal-backend \
  --to-revisions $PREV_REVISION=100 \
  --region us-central1
```

**4. Post-Incident**

- [ ] Document root cause
- [ ] Create GitHub issue for fix
- [ ] Schedule post-mortem within 24 hours
- [ ] Update runbook if process changed

---

### P2: Database Unavailable

**Severity**: Critical | **SLA**: 30 minutes  
**Impact**: Data cannot be persisted or retrieved

#### Detection
- Alert: `cloudsql-instance-down` triggered
- Monitoring: Database connection errors in application logs

#### Response Steps

```bash
# Check instance status
gcloud sql instances describe portal-db

# Check backup status
gcloud sql backups list --instance=portal-db --limit 5

# If replication issue
gcloud sql instances describe portal-db \
  --format 'value(replicationConfiguration)'

# Restart instance if needed
gcloud sql instances restart portal-db

# Monitor recovery
gcloud sql operations list --instance=portal-db --limit 5
```

#### Recovery from Backup

```bash
# List available backups
gcloud sql backups list --instance=portal-db

# Restore from backup (creates new instance first)
gcloud sql backups restore BACKUP_ID \
  --backup-instance=portal-db \
  --backup-id=BACKUP_ID
```

---

### P3: High Latency / Slow Responses

**Severity**: Medium | **SLA**: 1 hour  
**Impact**: Users experience slow Portal access

#### Diagnosis

```bash
# Check application metrics
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/request_latencies"'

# Check database query performance
gcloud sql instances describe portal-db \
  --format 'value(ipAddresses[0].ipAddress)'

# Connect to database and check slow queries
gcloud sql connect portal-db --user=root
```

#### Resolution

```bash
# Option 1: Scale up Cloud Run
gcloud run services update portal-backend \
  --memory=2Gi \
  --cpu=2 \
  --region us-central1

# Option 2: Scale database
gcloud sql instances patch portal-db \
  --tier=db-custom-4-16384

# Option 3: Clear cache
gcloud redis instances update portal-cache \
  --clear-data
```

---

## Disaster Recovery

### Full Restore Procedure

**RTO**: 4 hours | **RPO**: 1 hour | **Trigger**: Manual authorization from incident commander

#### 1. Assess Damage (30 min)

```bash
# Check backup status
gcloud sql backups list --instance=portal-db --limit 10 \
  --format 'table(name,status,windowStartTime)'

# Verify backup integrity
gcloud sql backups describe BACKUP_ID --instance=portal-db

# Check artifact registry for deployable images
gcloud artifacts repositories describe \
  portal-artifacts --location us-central1
```

#### 2. Restore Database (1 hour)

```bash
# Create new instance from backup
gcloud sql instances clone portal-db portal-db-restored \
  --point-in-time=2026-01-19T10:00:00Z

# Run migrations
gcloud sql connect portal-db-restored --user=root
mysql> -- Run schema migrations from docs/db/migrations/

# Validate restored data
gcloud sql connect portal-db-restored --user=root
mysql> SELECT COUNT(*) FROM users;
mysql> SELECT MAX(created_at) FROM audit_logs;

# Switch DNS to restored instance
gcloud compute addresses describe portal-db-ip
gcloud compute addresses update portal-db-ip \
  --address=<NEW_IP>
```

#### 3. Restore Application (1 hour)

```bash
# Deploy from known-good image
gcloud run deploy portal-backend \
  --image gcr.io/PROJECT/portal-backend:stable \
  --region us-central1 \
  --set-env-vars DB_HOST=portal-db-restored.c.PROJECT.internal

# Deploy frontend
gsutil -m cp gs://portal-frontend-backup/latest/* \
  gs://portal-frontend/

# Invalidate CDN cache
gcloud compute url-maps invalidate-cdn-cache portal-frontend-lb \
  --path "/*"
```

#### 4. Verification (30 min)

```bash
# Health checks
curl https://portal.example.com/api/v1/health

# Test critical flows
# - Login
# - Project list
# - Resource view

# Monitor for errors
gcloud logging read "severity=ERROR" --limit 50

# Notification
echo "Portal restored successfully" | mail -s "DR: Restore Complete" ops@example.com
```

---

## Operational Procedures

### Routine Maintenance

#### Weekly Backup Verification
```bash
# Every Monday 0100 UTC
gcloud sql backups list --instance=portal-db --limit 5
# Verify: Status = SUCCESSFUL, within last 7 days
```

#### Monthly Security Patching
```bash
# Check for available patches
gcloud sql instances describe portal-db \
  --format 'value(databaseVersion)'

# Schedule maintenance window
gcloud sql instances patch portal-db \
  --maintenance-release-channel=production
```

#### Quarterly Certificate Rotation
```bash
# Check cert expiration
gcloud sql ssl-certs list --instance=portal-db

# Create new cert
gcloud sql ssl-certs create new-cert --instance=portal-db

# Rotate (old clients use for 30 days)
gcloud sql ssl-certs delete old-cert --instance=portal-db
```

### Deployments

#### Standard Deployment Process

```bash
# 1. Merge PR to main branch
# (Automatically triggers Cloud Build)

# 2. Monitor build
gcloud builds log BUILD_ID

# 3. Verify deployment
gcloud run services describe portal-backend \
  --region us-central1 --format 'value(status.traffic[0].revision.name)'

# 4. Health check
curl https://portal.example.com/api/v1/health

# 5. Alert monitoring team
echo "Deploy complete" | mail -s "Deploy: portal-backend" ops@example.com
```

#### Canary Deployment (for major changes)

```bash
# Deploy new revision without traffic
gcloud run deploy portal-backend \
  --image gcr.io/PROJECT/portal-backend:v1.2.0 \
  --region us-central1 \
  --no-traffic

# Get revision name
NEW_REV=$(gcloud run services describe portal-backend \
  --region us-central1 --format 'value(status.traffic[0].revision.name)')

# Shift 10% traffic for 30 minutes
gcloud run services update-traffic portal-backend \
  --to-revisions $NEW_REV=10,${OLD_REV}=90

# Monitor metrics
watch -n 10 'gcloud logging read "severity=ERROR" --limit 10'

# If errors spike, rollback
gcloud run services update-traffic portal-backend \
  --to-revisions $OLD_REV=100

# If stable, shift 100%
gcloud run services update-traffic portal-backend \
  --to-revisions $NEW_REV=100
```

---

## Troubleshooting

### Application Won't Start

**Symptoms**: Cloud Run service stuck in "Creating" or "Updating"

```bash
# Check recent events
gcloud run services describe portal-backend \
  --region us-central1 --format 'value(status.conditions)'

# View deployment logs
gcloud builds log BUILD_ID --stream

# Check container image
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/PROJECT/portal-artifacts
```

### Database Connection Errors

**Symptoms**: `Error: connection refused` in application logs

```bash
# Verify Cloud SQL Proxy
gcloud sql connect portal-db --user=root

# Check IAM permissions
gcloud projects get-iam-policy PROJECT \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:portal-backend@PROJECT.iam.gserviceaccount.com"

# Check network connectivity
gcloud compute networks describe default

# Test from Cloud Run container
gcloud run services update portal-backend \
  --set-env-vars TEST_DB_CONNECTION=true
```

### High Memory Usage

**Symptoms**: Cloud Run instance terminated due to memory limit

```bash
# Check memory metrics
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/container_memory_utilizations"'

# Identify memory leaks
# Option 1: Increase memory allocation
gcloud run services update portal-backend \
  --memory=2Gi

# Option 2: Fix application memory leak
# - Check logs for warnings
# - Review recent code changes
# - Add memory profiling
```

### Secrets Not Found

**Symptoms**: `Error: secret not found` in logs

```bash
# List available secrets
gcloud secrets list

# Check secret value
gcloud secrets versions access latest --secret=db-password

# Verify service account has access
gcloud secrets get-iam-policy db-password

# Grant access if needed
gcloud secrets add-iam-policy-binding db-password \
  --member=serviceAccount:portal-backend@PROJECT.iam.gserviceaccount.com \
  --role=roles/secretmanager.secretAccessor
```

---

## Escalation Contacts

| Role | Contact | Hours |
|------|---------|-------|
| On-Call Engineer | Slack: #oncall | 24/7 |
| Platform Lead | name@example.com | Business hours |
| Incident Commander | ic@example.com | 24/7 for P1 |

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [DEPLOYMENT.md](DEPLOYMENT.md) - Deployment procedures
- [SECURITY.md](SECURITY.md) - Security policies

---

**Version**: 1.0  
**Last Updated**: 2026-01-19  
**Owner**: Platform Engineering Team  
**Review Cycle**: Quarterly
