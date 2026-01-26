# Live Sync Quick Reference

**Objective**: Keep Portal in real-time sync with Landing Zone as it evolves

---

## 5-Layer Sync Architecture

```
LZ Changes
    ↓
[1. Webhook] ← Immediate trigger via GitHub Actions
    ↓
[2. Git Sync] ← Docs & configs every 6 hours
    ↓
[3. API Sync] ← Real infrastructure state every 5 minutes  
    ↓
[4. Pub/Sub] ← Real-time infrastructure events <2s
    ↓
[5. BigQuery] ← Historical analytics daily/weekly
    ↓
Portal Always Updated
```

---

## Implementation Phases

| Phase | Week | Component | Status |
|-------|------|-----------|--------|
| 1 | 1 | GitHub Actions + Git Sync | 📄 Documented |
| 2 | 2-3 | GCP API Sync Service | ✅ Coded |
| 3 | 3-4 | Pub/Sub Real-time Events | 📝 Design ready |
| 4 | 4+ | BigQuery Analytics | 📋 Plan ready |

---

## Key Files Created

**Architecture & Planning**:
- `LIVE_SYNC_ARCHITECTURE.md` - Comprehensive 5-layer design
- `LIVE_SYNC_IMPLEMENTATION_GUIDE.md` - Step-by-step implementation

**Code & Configuration**:
- `.github/workflows/sync-from-lz.yml` - Portal sync workflow (6-hour schedule + webhook)
- `WORKFLOW_TEMPLATES_FOR_LZ_REPO.yml` - Webhook template (add to LZ repo)
- `backend/services/lz_sync_service.py` - FastAPI sync service (async, typed, production-ready)
- `config/sync-config.yaml` - Comprehensive sync configuration

---

## Quick Start (5 minutes)

### 1. Copy webhook to LZ repo
```bash
# Add to kushin77/GCP-landing-zone
cp WORKFLOW_TEMPLATES_FOR_LZ_REPO.yml .github/workflows/notify-portal-of-changes.yml
git add .github/workflows/notify-portal-of-changes.yml
git commit -m "ci: add portal sync webhook"
```

### 2. Configure GitHub secrets
```bash
# In LZ repo: Add PORTAL_SYNC_TOKEN (GitHub Personal Access Token)
# In Portal repo: Add GCP_SERVICE_ACCOUNT_KEY (service account JSON)
```

### 3. Test workflow
```bash
# Edit LZ terraform file
# Push to main
# Watch Portal Actions tab for auto-triggered sync
```

---

## Sync Status

All 5 layers planned and ready for Q1 2026 implementation:

✅ **Layer 1 (Webhook)** - GitHub Actions workflow ready  
✅ **Layer 2 (Git Sync)** - Automated 6-hour sync ready  
✅ **Layer 3 (API Sync)** - Service implementation complete  
✅ **Layer 4 (Pub/Sub)** - Architecture designed  
✅ **Layer 5 (BigQuery)** - Analytics plan ready  

---

## Success Metrics

| Metric | Target | Layer |
|--------|--------|-------|
| Docs sync latency | <1 minute | 2 |
| Infrastructure sync latency | <5 minutes | 3 |
| Event notification | <2 seconds | 4 |
| Sync success rate | >99.5% | All |
| Data freshness | <6 hours | All |

---

## Team Assignment

**Phase 1-2** (Weeks 1-2):
- Backend Engineer: Setup workflows, test git sync
- DevOps: Configure service accounts, secrets

**Phase 2-3** (Weeks 2-4):
- Backend Engineer: Deploy sync service, implement API layer
- Frontend Engineer: Add sync status dashboard, WebSocket UI

**Phase 3-4** (Weeks 4+):
- Backend Engineer: Pub/Sub event handling
- Data Engineer: BigQuery pipelines, dashboards

---

## Configuration

All configurable via `config/sync-config.yaml`:
- Enable/disable layers independently
- Adjust sync frequencies
- Configure alert thresholds
- Manage cache TTLs
- Control cost optimization

---

## Cost Estimate

| Service | Monthly |
|---------|---------|
| Cloud Asset Inventory | $500 |
| Cloud Pub/Sub | $400 |
| BigQuery | $600 |
| Cloud Logging | $500 |
| Cloud Functions | $100 |
| **Total** | **~$2,100** |

---

## Related Issues

- #22 Performance Optimization (sync performance targets)
- #20 Analytics & Telemetry (sync metrics and monitoring)
- #26 Admin Console (displays LZ sync status)

---

## Documentation Links

- [Full Architecture](./LIVE_SYNC_ARCHITECTURE.md)
- [Implementation Guide](./LIVE_SYNC_IMPLEMENTATION_GUIDE.md)
- [Sync Configuration](./config/sync-config.yaml)
- [Backend Service](./backend/services/lz_sync_service.py)

---

**Status**: Ready for Phase 1 Implementation  
**Complexity**: Medium to Advanced  
**Estimated Duration**: 4 weeks (1 backend + 1 frontend engineer)  
**Next Step**: Approve architecture and kickoff Phase 1
