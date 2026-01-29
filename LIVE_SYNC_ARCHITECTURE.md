# Live Sync Architecture: Landing Zone ↔ Portal

**Purpose**: Keep the Portal in real-time sync with Landing Zone updates, ensuring the Portal always reflects the latest infrastructure state, policies, configurations, and documentation.

**Status**: Architecture Document (Q1 2026 Implementation)

---

## 1. Sync Strategy Overview

The Portal will operate as a **consumer** of the Landing Zone (source of truth), syncing at multiple layers:

```
┌─────────────────────────────────────────────────────────┐
│     GCP-landing-zone (Source of Truth)                  │
│     - Infrastructure code (Terraform)                   │
│     - Policies & enforcement gates                      │
│     - Documentation & runbooks                          │
│     - pmo.yaml configuration                            │
│     - Compliance frameworks                             │
└──────────────────┬──────────────────────────────────────┘
                   │
        ┌──────────┼──────────┬──────────┬──────────┐
        │          │          │          │          │
        ▼          ▼          ▼          ▼          ▼
   [Layer 1]  [Layer 2]  [Layer 3]  [Layer 4]  [Layer 5]
    Webhook   Git Sync   API Sync   Real-time  Data
    Trigger   (Docs)     (State)    Events     Pipeline
        │          │          │          │          │
        └──────────┼──────────┴──────────┴──────────┘
                   │
┌──────────────────▼──────────────────────────────────────┐
│     GCP-landing-zone-Portal (Consumer)                  │
│     - Always synced documentation                       │
│     - Live infrastructure state                         │
│     - Policy enforcement displays                       │
│     - Dashboard metrics & analytics                     │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Five-Layer Sync Architecture

### Layer 1: **Webhook-Triggered Sync** (Immediate)
**When**: Landing Zone repository updated (push/PR merge)
**What**: Trigger Portal rebuild/updates
**Implementation**: GitHub Actions webhook

```yaml
# .github/workflows/notify-portal-sync.yml (in LZ repo)
name: Notify Portal of Updates

on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'
      - 'pmo.yaml'
      - 'docs/**'
      - 'ENFORCEMENT_GATES.md'

jobs:
  notify-portal:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger Portal Sync
        run: |
          curl -X POST \
            https://api.github.com/repos/kushin77/GCP-landing-zone-Portal/dispatches \
            -H "Authorization: token ${{ secrets.PORTAL_SYNC_TOKEN }}" \
            -d '{"event_type": "lz-update", "client_payload": {"commit_sha": "${{ github.sha }}", "trigger": "landing-zone-change"}}'
```

---

### Layer 2: **Git Sync** (Documentation & Configs)
**Frequency**: Every 6 hours or on webhook trigger
**What**: Auto-sync docs, policies, enforcement gates
**Files to sync**:
- `docs/**` → Portal knowledge base
- `pmo.yaml` → Portal governance config
- `ENFORCEMENT_GATES.md` → Compliance rules
- `terraform/**/*.tf` → Infrastructure reference
- `RUNBOOKS.md` → Operational procedures

**Implementation**: GitHub Actions scheduled job

```yaml
# .github/workflows/sync-from-lz.yml (in Portal repo)
name: Sync from Landing Zone

on:
  workflow_dispatch:
  repository_dispatch:
    types: [lz-update]
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours

jobs:
  sync:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure Git
        run: |
          git config user.name "Portal Sync Bot"
          git config user.email "noreply@portal.local"

      - name: Sync Documentation
        run: |
          # Clone LZ repo to temp directory
          git clone --depth 1 https://github.com/kushin77/GCP-landing-zone.git /tmp/lz

          # Sync specific directories
          cp -r /tmp/lz/docs/* ./docs/lz-reference/
          cp /tmp/lz/pmo.yaml ./config/lz-pmo.yaml
          cp /tmp/lz/ENFORCEMENT_GATES.md ./docs/lz-reference/
          cp /tmp/lz/RUNBOOKS.md ./docs/lz-reference/

      - name: Commit changes
        run: |
          git add -A
          if [[ -z $(git status -s) ]]; then
            echo "No changes to commit"
            exit 0
          fi
          git commit -m "chore(sync): update from landing zone [$(date -I)]"
          git push
```

---

### Layer 3: **API Sync** (Infrastructure State)
**Frequency**: Real-time (Pub/Sub) or every 5 minutes
**What**: Query actual GCP infrastructure, policies, resource state
**Implementation**: FastAPI backend querying GCP APIs

```python
# backend/services/lz_sync_service.py
from google.cloud import asset_v1, container_v1
from datetime import datetime
import logging

class LZSyncService:
    """Syncs real-time infrastructure state from GCP."""

    def __init__(self):
        self.asset_client = asset_v1.AssetServiceClient()
        self.gke_client = container_v1.ClusterManagerClient()

    async def sync_infrastructure_state(self):
        """Fetch current infrastructure state from GCP."""
        resources = {
            'projects': self.get_projects(),
            'vpcs': self.get_vpcs(),
            'vms': self.get_compute_instances(),
            'gke_clusters': self.get_gke_clusters(),
            'databases': self.get_databases(),
            'compliance_status': self.get_compliance_status(),
            'policy_violations': self.get_policy_violations(),
            'last_sync': datetime.utcnow().isoformat()
        }
        return resources

    def get_projects(self):
        """Get all GCP projects in Landing Zone."""
        query = """
        SELECT resource.name, resource.labels
        FROM `projects`
        WHERE resource.parent.type = 'organization'
        """
        return self.asset_client.search_all_resources(parent=..., query=query)

    def get_vpcs(self):
        """Get all VPC networks."""
        query = """
        SELECT resource.name, resource.data.autoCreateSubnetworks
        FROM `compute.googleapis.com/Network`
        """
        return self.asset_client.search_all_resources(parent=..., query=query)

    def get_policy_violations(self):
        """Get policy violations from enforcement gates."""
        # Query Cloud Asset Inventory + custom enforcement
        violations = []
        # Implementation details...
        return violations

    def get_compliance_status(self):
        """Aggregate compliance posture."""
        return {
            'framework': 'CIS v1.2',
            'score': 0.92,
            'violations': [...],
            'last_audit': datetime.utcnow().isoformat()
        }
```

**Endpoint** (exposed to Portal frontend):
```python
@router.get("/api/v1/sync/infrastructure-state")
async def get_infrastructure_state():
    """Get latest synced infrastructure state."""
    service = LZSyncService()
    state = await service.sync_infrastructure_state()
    return state
```

---

### Layer 4: **Real-Time Events** (Pub/Sub)
**When**: Infrastructure changes detected
**What**: Publish events for real-time Portal updates
**Implementation**: Cloud Pub/Sub + WebSocket

```python
# backend/services/pubsub_service.py
from google.cloud import pubsub_v1

class LZEventSubscriber:
    """Subscribe to LZ infrastructure changes."""

    def __init__(self):
        self.subscriber_client = pubsub_v1.SubscriberClient()
        self.subscription_path = self.subscriber_client.subscription_path(
            'project-id', 'lz-events-subscription'
        )

    def start_listening(self):
        """Listen to infrastructure change events."""
        streaming_pull_future = self.subscriber_client.subscribe(
            self.subscription_path,
            callback=self._handle_infrastructure_change
        )
        return streaming_pull_future

    async def _handle_infrastructure_change(self, message):
        """Process infrastructure change and broadcast to Portal."""
        event = json.loads(message.data)

        # Event types: resource_created, resource_deleted, policy_violated
        event_type = event['event_type']
        resource = event['resource']
        timestamp = event['timestamp']

        # Broadcast to connected WebSocket clients
        await self._broadcast_to_portal(event)

        # Update Portal cache/database
        await self._update_portal_state(event)

        message.ack()

    async def _broadcast_to_portal(self, event):
        """Send WebSocket update to Portal UI."""
        # WebSocket implementation
        pass
```

---

### Layer 5: **Data Pipeline** (Aggregation & Analytics)
**Frequency**: Daily/Weekly
**What**: Historical trends, cost analysis, compliance evolution
**Implementation**: BigQuery + scheduled Cloud Functions

```sql
-- Landing Zone metrics aggregation
CREATE OR REPLACE SCHEDULED QUERY `project.dataset.daily_lz_metrics`
OPTIONS(
  query="""
  SELECT
    CURRENT_DATE() as date,
    'gcp-landing-zone' as source,
    COUNT(DISTINCT resource_name) as total_resources,
    COUNT(CASE WHEN violation_count > 0 THEN 1 END) as resources_with_violations,
    SUM(monthly_cost) as total_cost,
    AVG(compliance_score) as avg_compliance
  FROM `project.dataset.asset_inventory_latest`
  GROUP BY date, source
  """,
  schedule='every day 01:00'
);
```

---

## 3. Implementation Timeline

### Phase 1: Foundation (Q1 2026 - Weeks 1-4)
- [ ] Setup GitHub Actions webhook (Layer 1)
- [ ] Create git sync workflow (Layer 2)
- [ ] Build basic API sync service (Layer 3)
- [ ] Setup Pub/Sub topic for LZ events

### Phase 2: Real-time (Q1 2026 - Weeks 5-8)
- [ ] Implement Pub/Sub listener (Layer 4)
- [ ] Add WebSocket support for real-time updates
- [ ] Create sync status dashboard in Portal
- [ ] Add sync health monitoring

### Phase 3: Advanced Analytics (Q2 2026)
- [ ] Setup BigQuery data pipeline (Layer 5)
- [ ] Create historical analytics dashboards
- [ ] Add trend analysis (cost, compliance, growth)
- [ ] Implement predictive insights

---

## 4. Configuration Files Needed

### `.github/workflows/lz-notify-portal.yml`
Trigger Portal sync when LZ changes (add to LZ repo)

### `.github/workflows/portal-sync-from-lz.yml`
Automated git sync workflow (add to Portal repo)

### `backend/config/sync_config.yaml`
```yaml
sync_layers:
  webhook:
    enabled: true
    timeout_seconds: 300

  git_sync:
    enabled: true
    frequency_hours: 6
    paths:
      - docs/**
      - pmo.yaml
      - ENFORCEMENT_GATES.md

  api_sync:
    enabled: true
    frequency_minutes: 5
    endpoints:
      - /projects
      - /vpcs
      - /compute
      - /compliance

  pubsub:
    enabled: true
    topic: 'lz-infrastructure-events'
    subscription: 'portal-lz-events'

  bigquery:
    enabled: true
    schedule: 'daily'
    dataset: 'lz_metrics'
```

---

## 5. Data Models for Sync

### Sync Status Model
```python
@dataclass
class SyncStatus:
    layer: str  # webhook, git, api, pubsub, bigquery
    status: str  # success, in_progress, failed
    last_sync: datetime
    items_synced: int
    errors: List[str]
    next_sync: datetime
```

### Infrastructure State Model
```python
@dataclass
class LZInfrastructureState:
    timestamp: datetime
    projects: List[Project]
    vpcs: List[VPC]
    compute_instances: List[VM]
    gke_clusters: List[Cluster]
    compliance_score: float
    policy_violations: List[Violation]
    sync_metadata: SyncStatus
```

---

## 6. Portal Dashboard Enhancements

### New "LZ Sync" Section
- **Sync Status Page**: Show sync health per layer
- **Real-time Activity Feed**: Infrastructure changes as they happen
- **Sync Analytics**: Sync performance, error rates
- **Compliance Timeline**: Historical compliance evolution
- **Cost Trends**: Daily/weekly/monthly cost analysis

### Real-time Updates
- WebSocket notifications for infrastructure changes
- Live policy violation alerts
- Cost spike notifications
- Compliance drift warnings

---

## 7. Error Handling & Resilience

### Retry Strategy
```python
MAX_RETRIES = 3
RETRY_BACKOFF = [5, 30, 300]  # seconds

def sync_with_retry(func, *args, **kwargs):
    for attempt in range(MAX_RETRIES):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                wait_time = RETRY_BACKOFF[attempt]
                logger.warning(f"Sync failed, retrying in {wait_time}s: {e}")
                time.sleep(wait_time)
            else:
                logger.error(f"Sync failed after {MAX_RETRIES} attempts: {e}")
                raise
```

### Fallback & Cache
- Local cache of last successful sync state
- Graceful degradation if sync fails
- Cache TTL: 1 hour (use last known state if sync fails)
- Alert after 3 consecutive failures

---

## 8. Security Considerations

### Authentication
- Service account with minimal LZ permissions (read-only)
- Short-lived tokens (1 hour)
- Separate token for git operations vs API calls

### Permissions Required
```yaml
# GCP service account permissions
roles:
  - roles/compute.networkViewer
  - roles/compute.osLoginViewer
  - roles/container.viewer
  - roles/cloudasset.viewer
  - roles/monitoring.viewer

# GitHub token permissions
github_token_scopes:
  - repo:read
  - actions:read
```

### Audit Trail
- Log all sync operations
- Track who triggered manual syncs
- Export logs to Cloud Logging
- Monthly sync audit reports

---

## 9. Monitoring & Alerting

### Key Metrics
- **Sync Latency**: Time from LZ update to Portal update
- **Sync Success Rate**: % of successful syncs (target: 99.9%)
- **Data Freshness**: Age of Portal data vs actual state
- **Sync Volume**: Resources synced per sync cycle

### Alerts
```yaml
alerts:
  - name: SyncFailure
    condition: sync_success_rate < 0.95
    notification: slack, email, pagerduty

  - name: SyncLatency
    condition: sync_latency_seconds > 300
    severity: warning

  - name: DataFreshness
    condition: portal_data_age_hours > 6
    severity: warning
```

---

## 10. Cost Estimation

### Monthly Costs (Rough)
| Service | Usage | Cost |
|---------|-------|------|
| Cloud Asset Inventory | 1M API calls | $500 |
| Cloud Pub/Sub | 1M messages/month | $400 |
| BigQuery | 100GB scanned/month | $600 |
| Cloud Logging | 100GB/month | $500 |
| Cloud Functions | Minimal | $100 |
| **Total** | | **~$2,100/month** |

---

## 11. Success Criteria

✅ **Phase 1 Complete When:**
- Git sync working (documentation always fresh)
- API sync queries real infrastructure state
- Webhook triggers Portal updates within 5 minutes
- Sync status dashboard showing all layers

✅ **Phase 2 Complete When:**
- WebSocket real-time updates <2s latency
- Pub/Sub events processing all infrastructure changes
- Portal showing live activity feed
- Sync health monitoring 24/7

✅ **Phase 3 Complete When:**
- BigQuery pipeline aggregating trends
- Historical analytics dashboards available
- Predictive insights generating recommendations
- Cost trends and compliance evolution visible

---

## 12. Next Steps

1. **Approve architecture** (this document)
2. **Create GitHub Actions workflows** (Layers 1 & 2)
3. **Implement LZ sync service** (Layer 3)
4. **Setup Pub/Sub infrastructure** (Layer 4)
5. **Build Portal sync status dashboard**
6. **Monitor and iterate**

---

## Related Issues
- #22 Performance Optimization (sync performance targets)
- #20 Analytics & Telemetry (sync metrics)
- #26 Admin Console (LZ status display)

---

**Document Version**: 1.0
**Last Updated**: 2026-01-26
**Maintained By**: Platform Engineering Team
