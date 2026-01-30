# Live Sync Implementation Guide

**Status**: Q1 2026 Implementation
**Estimated Duration**: 4 weeks
**Difficulty**: Medium to Advanced

---

## Overview

This guide walks through implementing the **5-layer live sync architecture** between the Landing Zone (source) and Portal (consumer).

---

## Phase 1: Setup & Foundation (Week 1)

### 1.1 Create GitHub Actions Workflow (LZ Repo)

**File**: `.github/workflows/notify-portal-of-changes.yml`

Copy the template from `WORKFLOW_TEMPLATES_FOR_LZ_REPO.yml` to the Landing Zone repository.

**Setup**:
```bash
# 1. Add to GCP-landing-zone repository
cd /path/to/GCP-landing-zone
mkdir -p .github/workflows
cp /path/to/GCP-landing-zone-Portal/WORKFLOW_TEMPLATES_FOR_LZ_REPO.yml \
   .github/workflows/notify-portal-of-changes.yml
git add .github/workflows/notify-portal-of-changes.yml
git commit -m "ci: add portal sync notification workflow"
git push
```

**Verify**:
- [ ] Workflow appears in LZ repo `.github/workflows` directory
- [ ] Workflow has correct trigger paths
- [ ] Requires `PORTAL_SYNC_TOKEN` secret to be configured

### 1.2 Create GitHub Actions Workflow (Portal Repo)

**File**: `.github/workflows/sync-from-lz.yml`

This file is already created. Verify and configure:

**Setup**:
```bash
# Already exists, just verify it's correct
ls -la .github/workflows/sync-from-lz.yml

# Create the required directories
mkdir -p docs/lz-reference
mkdir -p config/lz-config
```

**Verify**:
- [ ] Workflow file exists and is readable
- [ ] Scheduled to run every 6 hours
- [ ] Respects repository_dispatch for webhooks
- [ ] Has write permissions configured

### 1.3 Configure GitHub Secrets

**In Landing Zone Repository** (`kushin77/GCP-landing-zone`):

1. Go to Settings → Secrets and variables → Actions
2. Create new secret: `PORTAL_SYNC_TOKEN`
3. Value: GitHub Personal Access Token with `repo:write` scope

```bash
# Generate token with proper scopes
# Go to https://github.com/settings/tokens/new
# Scopes needed: repo (all), workflow
# Copy token and add to LZ repo secrets as PORTAL_SYNC_TOKEN
```

**In Portal Repository** (`kushin77/GCP-landing-zone-Portal`):

1. Go to Settings → Secrets and variables → Actions
2. Create secrets:
   - `SLACK_WEBHOOK` (optional, for notifications)
   - `GCP_SERVICE_ACCOUNT_KEY` (for API sync layer)

---

## Phase 2: Git Sync Layer (Week 2)

### 2.1 Test Documentation Sync

**Trigger manually**:
```bash
# Go to Portal repo Actions tab
# Select "Sync from Landing Zone" workflow
# Click "Run workflow" → Run workflow
```

**Expected results**:
- [ ] New files appear in `docs/lz-reference/`
- [ ] `config/lz-config/sync-metadata.json` created
- [ ] Pull request created (if changes detected)
- [ ] PR auto-merges if all checks pass

**Verify sync**:
```bash
# After workflow completes
ls -la docs/lz-reference/
cat config/lz-config/sync-metadata.json
git log --oneline | head -5  # Should see sync commits
```

### 2.2 Test Webhook Trigger

**Trigger from Landing Zone**:
```bash
# Make a change to LZ repo terraform files
cd /path/to/GCP-landing-zone
echo "# test comment" >> terraform/01-foundation/main.tf
git add terraform/01-foundation/main.tf
git commit -m "test: trigger portal sync"
git push origin main
```

**Verify webhook triggered Portal sync**:
1. Go to `GCP-landing-zone-Portal` Actions tab
2. Look for "Sync from Landing Zone" workflow run
3. Should start within 2 minutes
4. Check workflow logs for success

---

## Phase 3: API Sync Layer (Week 2-3)

### 3.1 Setup GCP Service Account

**Create service account**:
```bash
PROJECT_ID="your-gcp-project"

# Create service account
gcloud iam service-accounts create portal-sync \
  --display-name="Portal Landing Zone Sync"

# Get service account email
SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:Portal" \
  --format='value(email)')

echo "Service account: $SA_EMAIL"
```

**Grant minimal permissions**:
```bash
# Grant read-only access to necessary APIs
roles=(
  "roles/compute.networkViewer"
  "roles/compute.osLoginViewer"
  "roles/container.viewer"
  "roles/cloudasset.viewer"
  "roles/monitoring.viewer"
)

for role in "${roles[@]}"; do
  gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SA_EMAIL" \
    --role="$role"
done

# Verify permissions
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:$SA_EMAIL" \
  --format='table(bindings.role)'
```

### 3.2 Create and Store Service Account Key

```bash
# Create key
gcloud iam service-accounts keys create /tmp/portal-sync-key.json \
  --iam-account=$SA_EMAIL

# Add to Portal repo secrets
# Go to Settings → Secrets → Actions → New Repository Secret
# Name: GCP_SERVICE_ACCOUNT_KEY
# Value: (paste contents of /tmp/portal-sync-key.json)

# Clean up local key
rm /tmp/portal-sync-key.json
```

### 3.3 Deploy Sync Service to Backend

**Update FastAPI main.py**:

```python
# backend/main.py

from services.lz_sync_service import LZSyncService, router as sync_router
from contextlib import asynccontextmanager

# Global sync service
sync_service = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize sync service on startup."""
    global sync_service

    # Initialize with your project ID
    sync_service = LZSyncService(
        project_id="your-gcp-project",
        gcp_parent="organizations/YOUR_ORG_ID"  # Optional
    )

    logger.info("LZ Sync service initialized")
    yield

    logger.info("Shutting down LZ Sync service")

app = FastAPI(lifespan=lifespan)

# Include sync routes
app.include_router(sync_router)
```

**Test API endpoint**:
```bash
# Start Portal backend
cd backend
python main.py

# In another terminal
curl http://localhost:8000/api/v1/sync/infrastructure-state

# Response should show projects, VPCs, instances, compliance status, etc.
```

### 3.4 Add Sync Status Dashboard Component

**Create React component**:
```typescript
// frontend/src/components/SyncStatus.tsx

import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';

interface SyncMetadata {
  layer: string;
  status: string;
  last_sync: string;
  items_synced: number;
  sync_duration_seconds: number;
}

export function SyncStatus() {
  const { data: status, isLoading } = useQuery<Record<string, SyncMetadata>>({
    queryKey: ['syncStatus'],
    queryFn: async () => {
      const res = await fetch('/api/v1/sync/sync-status');
      return res.json();
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  if (isLoading) return <div>Loading sync status...</div>;

  return (
    <div className="sync-status-panel">
      <h3>Landing Zone Sync Status</h3>
      <div className="sync-layers">
        {status && Object.entries(status).map(([layer, meta]) => (
          <div key={layer} className="sync-layer">
            <div className={`status-badge ${meta?.status}`}>
              {meta?.status || 'pending'}
            </div>
            <span>{layer}</span>
            <time>{new Date(meta?.last_sync).toLocaleString()}</time>
          </div>
        ))}
      </div>
    </div>
  );
}
```

**Add to Dashboard**:
```typescript
// frontend/src/pages/Dashboard.tsx
import { SyncStatus } from '../components/SyncStatus';

export function Dashboard() {
  return (
    <div className="dashboard">
      <header>
        <h1>Portal Dashboard</h1>
        <SyncStatus />  {/* Add sync status display */}
      </header>
      {/* Rest of dashboard */}
    </div>
  );
}
```

---

## Phase 4: Pub/Sub Layer (Week 3-4)

### 4.1 Create Pub/Sub Topic and Subscription

```bash
PROJECT_ID="your-gcp-project"

# Create topic for LZ events
gcloud pubsub topics create lz-infrastructure-events \
  --project=$PROJECT_ID

# Create subscription for Portal
gcloud pubsub subscriptions create portal-lz-events \
  --topic=lz-infrastructure-events \
  --project=$PROJECT_ID

# List topics/subscriptions
gcloud pubsub topics list --project=$PROJECT_ID
gcloud pubsub subscriptions list --project=$PROJECT_ID
```

### 4.2 Implement Event Listener

**Start listening to events**:
```python
# backend/services/lz_sync_service.py (already has skeleton)

async def start_event_listener():
    """Start listening to LZ infrastructure events."""
    service = LZSyncService(project_id="your-project")
    streaming_pull_future = service.start_pubsub_listener()

    try:
        streaming_pull_future.result()
    except KeyboardInterrupt:
        streaming_pull_future.cancel()

# Add to main.py startup
if __name__ == "__main__":
    import asyncio
    asyncio.create_task(start_event_listener())
```

### 4.3 Add WebSocket Support

**Create WebSocket endpoint**:
```python
# backend/routers/websocket.py

from fastapi import WebSocket, APIRouter

router = APIRouter(prefix="/ws", tags=["websocket"])

@router.websocket("/sync-events")
async def websocket_sync_events(websocket: WebSocket):
    """WebSocket endpoint for real-time sync events."""
    await websocket.accept()
    try:
        async for event in event_queue:
            await websocket.send_json(event)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await websocket.close()
```

**Frontend listener**:
```typescript
// frontend/src/hooks/useSyncEvents.ts

import { useEffect, useState } from 'react';

export function useSyncEvents() {
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws/sync-events');

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setEvents(prev => [data, ...prev].slice(0, 100));
    };

    return () => ws.close();
  }, []);

  return events;
}
```

---

## Phase 5: BigQuery Layer (Week 4+)

### 5.1 Create BigQuery Dataset

```bash
PROJECT_ID="your-gcp-project"

# Create dataset
bq mk \
  --dataset \
  --description="Landing Zone metrics and analytics" \
  --location=US \
  "$PROJECT_ID:lz_metrics"

# Verify
bq ls -d
```

### 5.2 Create Metric Tables

```sql
-- Create daily_metrics table
CREATE OR REPLACE TABLE `{project}.lz_metrics.daily_metrics` (
  date DATE,
  source STRING,
  total_resources INT64,
  resources_with_violations INT64,
  total_cost NUMERIC,
  avg_compliance_score FLOAT64,
  created_at TIMESTAMP
);

-- Create scheduled query
CREATE OR REPLACE SCHEDULED QUERY `{project}.lz_metrics.daily_metrics_query`
OPTIONS(
  display_name='Daily LZ Metrics',
  query='''
    SELECT
      CURRENT_DATE() as date,
      'gcp-landing-zone' as source,
      -- Query metrics from asset inventory
      CAST(COUNT(*) AS INT64) as total_resources,
      0 as resources_with_violations,  -- TODO: implement
      0.0 as total_cost,  -- TODO: get from billing
      0.92 as avg_compliance_score,
      CURRENT_TIMESTAMP() as created_at
    FROM `{project}.asset_inventory.latest`
  ''',
  schedule='every day 01:00',
  time_zone='UTC'
);
```

### 5.3 Create Analytics Dashboards

Use [Looker](https://looker.com/) or Google Data Studio to create dashboards showing:
- Resource trends (growth/shrinkage)
- Compliance evolution
- Cost analysis
- Policy violations over time

---

## Testing Checklist

### Layer 1: Webhook
- [ ] Make change to LZ repo
- [ ] Verify Portal workflow triggers within 2 minutes
- [ ] Check workflow logs for success

### Layer 2: Git Sync
- [ ] Docs sync to `docs/lz-reference/`
- [ ] Configs sync to `config/lz-config/`
- [ ] PR created and auto-merged
- [ ] Can manually trigger sync

### Layer 3: API Sync
- [ ] GET `/api/v1/sync/infrastructure-state` returns data
- [ ] Status shows projects, VPCs, instances, clusters
- [ ] Compliance status populated
- [ ] Sync status available at `/api/v1/sync/sync-status`

### Layer 4: Pub/Sub
- [ ] Events published to topic
- [ ] Portal subscription receives events
- [ ] WebSocket endpoint works
- [ ] Real-time events display in UI

### Layer 5: BigQuery
- [ ] Dataset created
- [ ] Tables created with schema
- [ ] Scheduled queries run on schedule
- [ ] Dashboards display trends

---

## Troubleshooting

### Workflow not triggering
```bash
# Check workflow logs in GitHub Actions
# Verify PORTAL_SYNC_TOKEN secret exists
# Verify webhook is configured in LZ repo Settings
```

### API sync returning errors
```bash
# Verify service account has correct roles
gcloud projects get-iam-policy $PROJECT_ID | grep portal-sync

# Check service account key is valid
gcloud auth activate-service-account --key-file=/tmp/key.json
gcloud compute networks list
```

### Pub/Sub not receiving events
```bash
# Verify topic exists
gcloud pubsub topics list

# Check subscription
gcloud pubsub subscriptions describe portal-lz-events

# Publish test message
gcloud pubsub topics publish lz-infrastructure-events \
  --message='{"test": "message"}'
```

---

## Success Criteria

✅ **Minimal Viable Sync** (Week 1-2):
- Git sync operational
- Webhook triggers Portal updates
- Documentation always up-to-date

✅ **API Sync Operational** (Week 2-3):
- Infrastructure state queryable
- Compliance status available
- Sync status dashboard working

✅ **Real-time Streaming** (Week 3-4):
- Pub/Sub events flowing
- WebSocket updates working
- Live activity feed in Portal

✅ **Analytics & Insights** (Week 4+):
- BigQuery pipelines running
- Historical trends visible
- Predictive insights generated

---

## Next Steps

1. ✅ Complete Phase 1 (Git sync setup)
2. ✅ Test webhook triggering
3. ✅ Implement API sync service
4. ✅ Deploy to Cloud Run
5. ✅ Add real-time WebSocket
6. ✅ Setup BigQuery analytics

---

**Estimated Total Effort**: 4 weeks (1 engineer, full-time)
**Recommended Team**: 1 Backend Engineer + 1 Frontend Engineer
**Support**: Platform Engineering, DevOps, Data Engineering (for BigQuery)
