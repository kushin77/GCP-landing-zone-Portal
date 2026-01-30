# Incident Response Runbook

## Overview

This runbook covers incident detection, response, and resolution for the Landing Zone Portal.

**On-Call Rotation**: See PagerDuty → #portal-oncall
**Escalation**: @platform-engineering on Slack
**War Room**: https://meet.google.com/portal-incident-war-room

## Severity Levels

| Level | Impact | SLA | Examples |
|-------|--------|-----|----------|
| **P1** | Critical | 15 min detect, 1 hr resolve | Full outage, data loss, security breach |
| **P2** | High | 30 min detect, 4 hr resolve | Service degradation, 25%+ error rate |
| **P3** | Medium | 2 hr detect, 8 hr resolve | Single feature broken, minor perf impact |
| **P4** | Low | Next business day | UI bug, typo, documentation issue |

## P1: Full Outage

### Detection
- Cloud Monitoring alert: "Portal unavailable"
- Error Reporting: >10% error rate
- Manual: User reports complete service down

### Immediate Response (0-5 minutes)

1. **Declare Incident**
   ```
   /declare-incident P1 Portal Unavailable
   # Auto-pages on-call team + escalates to CTO
   ```

2. **Establish War Room**
   ```
   Google Meet: https://meet.google.com/portal-incident-war-room
   Participants: On-call engineer, platform team, CTO (if needed)
   ```

3. **Initial Assessment** (Check in this order)
   - Is Cloud Run service running?
   - Are instances healthy?
   - Is database accessible?
   - Are logs collecting?

### Diagnosis (5-15 minutes)

```bash
# 1. Check Cloud Run status
gcloud run services describe portal-backend \
  --region=us-central1 \
  --project=portal-prod

# 2. View recent logs
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" \
  --project=portal-prod \
  --limit=100 \
  --order=desc

# 3. Check database
gcloud firestore databases describe --database='(default)' --project=portal-prod

# 4. Check Pub/Sub
gcloud pubsub subscriptions describe portal-events-sub --project=portal-prod

# 5. Check Cloud Armor
gcloud compute backend-services describe portal-backend \
  --global \
  --project=portal-prod
```

**Common Root Causes:**
- Service crashed (OOM, unhandled exception) → Check logs for crash message
- Database unavailable → Check Firestore status, connection pool
- Network connectivity → Check VPC connector, private IP routing
- Security block → Check Cloud Armor rules, WAF logs
- Configuration error → Check Secret Manager, environment variables

### Resolution

**If service crashed:**
```bash
# 1. Rollback to previous revision
gcloud run services update-traffic portal-backend \
  --to-revisions PREVIOUS_REVISION=100 \
  --project=portal-prod

# 2. Notify team
# "Rolled back to v1.2.0 due to crash in v1.2.1"
# Post in #portal-deploys

# 3. Start post-mortem
# Create issue: "P1 Incident: [date] Service crash"
```

**If database issue:**
```bash
# 1. Check Firestore status
gcloud firestore databases describe --database='(default)' --project=portal-prod

# 2. If locked or unavailable:
#    - Wait 5 minutes (auto-recovery usually happens)
#    - If still down, contact Cloud Support

# 3. Check quota
gcloud compute project-info describe --project=portal-prod | grep FIRESTORE

# 4. If quota exceeded:
#    - Contact Cloud Support for emergency quota increase
#    - Temporary fallback: disable caching to reduce load
```

**If network issue:**
```bash
# 1. Check VPC connector
gcloud compute networks vpc-access connectors describe portal-connector \
  --region=us-central1 \
  --project=portal-prod \
  --status=READY

# 2. Check firewall rules
gcloud compute firewall-rules list \
  --filter="name~'portal'" \
  --project=portal-prod

# 3. Test connectivity
gcloud compute ssh portal-test-vm \
  --zone=us-central1-a \
  --project=portal-prod
# Then run: curl -v https://firestore.googleapis.com
```

### Communication (Ongoing)

- **Every 5 minutes**: Update #portal-status with status
- **After resolution**: Post in #portal-deploys
- **After 1 hour**: Debrief call with team
- **By end of day**: Post-mortem document

### Post-Mortem (Within 24 hours)

1. **Create issue template**
   ```
   Title: P1 Incident: Portal Outage [Date]

   **Impact**: Full service unavailable, ~0 users affected
   **Duration**: 15 minutes (detected at 14:30 UTC, resolved at 14:45 UTC)
   **Root Cause**: [Brief explanation]

   **Timeline**:
   - 14:30: Alert triggered
   - 14:32: Team responded
   - 14:35: Root cause identified
   - 14:45: Resolution deployed

   **Root Cause Analysis**:
   - Why did this happen?
   - Why weren't we protected?
   - Could we detect this earlier?

   **Action Items**:
   - [ ] Add monitoring for [metric]
   - [ ] Add test for [scenario]
   - [ ] Update docs for [process]
   ```

2. **Schedule debrief**
   - All hands meeting (30 min)
   - Review incident timeline
   - Discuss action items
   - Assign owners + deadlines

## P2: Service Degradation

### Detection
- Error rate 5-25%
- P95 latency >500ms
- Database query timeout
- Cache miss rate >50%

### Response (30 minutes to resolution target)

```bash
# 1. Check error rate
gcloud logging read "severity>=ERROR" \
  --project=portal-prod \
  --limit=50 \
  --format="table(timestamp, labels.error_type, jsonPayload.message)"

# 2. Check latency
gcloud monitoring time-series list \
  --filter 'metric.type = "cloudrun.googleapis.com/request_latencies"'

# 3. Check database performance
gcloud firestore databases describe --database='(default)' --project=portal-prod

# 4. Check if specific endpoint is slow
gcloud logging read "resource.type=cloud_run_revision AND httpRequest.requestUrl::/api" \
  --project=portal-prod \
  --format="table(timestamp, httpRequest.requestUrl, httpRequest.latency)"

# 5. Scale up if needed
gcloud run services update portal-backend \
  --min-instances=5 \
  --max-instances=200 \
  --project=portal-prod
```

**Common Causes & Fixes:**
- High database load → Increase cache TTL, add query caching
- Slow endpoint → Profile code, optimize queries
- High traffic spike → Scale instances, enable Cloud Armor rate limiting
- Memory leak → Restart service, check for resource leaks

## P3: Feature Broken

### Detection
- Single API endpoint returns error
- UI feature not working
- Data not updating

### Response (Next business day target)

1. **Reproduce issue**
   ```bash
   # Test affected endpoint
   curl -H "Authorization: Bearer $TOKEN" \
     https://portal.landing-zone.io/api/v1/costs/summary
   ```

2. **Check logs**
   ```bash
   gcloud logging read "jsonPayload.path=:/api/v1/costs/summary" \
     --project=portal-prod \
     --limit=20
   ```

3. **Create GitHub issue**
   - Title: "[BUG] Feature name broken"
   - Priority: P3
   - Include: error message, steps to reproduce, expected behavior

4. **Assign to team**
   - @frontend if UI issue
   - @backend if API issue
   - Estimate: Next sprint

## P4: Minor Issues

### Examples
- Typo in dashboard
- Styling issue on mobile
- Documentation outdated

### Process
1. Create GitHub issue (label: `type/docs` or `type/ui`)
2. Add to backlog
3. Resolve in next sprint

## Cost Anomaly Detection

### When Cost Spike Detected

```bash
# Notification: "Daily spend $5,000 (forecast: $3,000)"

# 1. Check which service increased
curl -H "Authorization: Bearer $TOKEN" \
  https://portal.landing-zone.io/api/v1/costs/daily?group_by=service

# 2. Check which projects increased
curl -H "Authorization: Bearer $TOKEN" \
  https://portal.landing-zone.io/api/v1/costs/daily?group_by=project

# 3. Investigate resource changes
gcloud compute instances list --project=hub-prod --filter="creationTimestamp>2026-01-15"
gcloud compute disks list --project=hub-prod --sort-by=~creationTimestamp

# 4. If cost is justified:
#    - Document in #portal-alerts
#    - Close notification

# 5. If cost is unexpected:
#    - Identify culprit resource
#    - Create ticket to optimize or delete
#    - Update forecast
```

## Security Incident Response

### If Suspected Security Issue

1. **Immediately notify** @ciso + @platform-engineering
2. **Do NOT** shut down service (preserve evidence)
3. **Enable maximum logging** (if not already)
4. **Isolate affected components** if needed
5. **Follow** INCIDENT_RESPONSE_PLAYBOOK.md (see SECURITY.md)

### Common Security Alerts

- **Unauthorized API access** → Check IAM, OAuth tokens
- **Secret exposure** → Rotate immediately, audit usage
- **Suspicious traffic** → Check Cloud Armor logs, WAF alerts
- **Privilege escalation** → Check IAM policy changes, revert if needed

## Escalation Matrix

| Situation | Escalate To | Method |
|-----------|------------|--------|
| P1 incident | @cto + on-call team | Slack + PagerDuty |
| Security issue | @ciso + @cto | Slack + email |
| Database down | GCP Support | Support ticket + call |
| Network issue | GCP SRE team | Support ticket |
| Customer data loss | Legal + Compliance | Secure channel |

## Prevention

### Monitoring & Alerting

Set up alerts for:
- Error rate >1%
- P95 latency >200ms
- Database connection pool exhaustion
- Memory usage >80%
- Disk usage >90%
- Cost spike (>120% daily average)

### Testing

- Weekly: Chaos engineering test
- Monthly: Disaster recovery drill
- Quarterly: Full incident simulation

### Documentation

Keep updated:
- Runbooks (this document)
- Architecture diagram
- Service dependencies
- Deployment procedures
- Rollback procedures

---

**Last Updated**: 2026-01-18
**Review Schedule**: Quarterly (next: 2026-04-18)
**On-Call**: See PagerDuty
