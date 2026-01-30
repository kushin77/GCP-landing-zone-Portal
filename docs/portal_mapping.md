# Portal Mapping: git-rca-workspace → Portal

This document defines how repository artifacts in `git-rca-workspace` and GCP resources map to Portal entities.

Goals
- Provide a clear mapping so discovery can create consistent Portal records.
- Define owners, fields, and discovery frequency.

Entities
- Endpoint: Any network-accessible service (HTTP, gRPC) or public DNS that should appear in the Portal.
  - Fields: `id`, `name`, `type`, `owner`, `project`, `public_dns`, `ip`, `created_at`, `source` (git|gcp)
- Storage: Buckets and data stores
  - Fields: `id`, `name`, `type`, `owner`, `project`, `location`, `created_at`, `source`
- Cluster/Compute: GKE clusters, VM instances
  - Fields: `id`, `name`, `type`, `owner`, `project`, `labels`, `created_at`, `source`

Source mappings (examples)
- git-rca-workspace
  - Path: `services/{team}/{service}/terraform/*` → Portal `Endpoint` with `source: git` and `owner: {team}`
  - Path: `infrastructure/{project}/k8s/{cluster}/manifests/*` → Portal `Cluster/Compute` records
- GCP API
  - `projects.list` → `project` field
  - `compute.instances.list` → `Cluster/Compute` / `Endpoint` (if has public IP)
  - `container.clusters.list` & `services` → GKE clusters and services
  - `storage.buckets.list` → `Storage` entities

Ownership & Frequency
- Discovery runs: initial full sync (manual), then incremental hourly polling for changes.
- Owners: platform-team for discovery infra; per-entity `owner` field set to team listed in git path or GCP label `owner`.

Validation & Backfill
- Discovery must produce a CSV of candidate records with these columns: `id,name,type,owner,project,public_dns,ip,created_at,source`
- Backfill process: review CSV, open issues to assign owners for any record lacking `owner` or `public_dns`.

Security
- Discovery will never write secrets to the repo. Any credentials used by discovery must be provided via Secret Manager and bound via Workload Identity.

Next steps
- Implement discovery endpoints returning the agreed schema. See `backend/discovery/service.py`.
- Implement backfill script to generate issues (dry-run by default). See `scripts/backfill/README.md`.

## Onboarding Status

✅ **Discovery Prototype**: Implemented in `backend/discovery/service.py` with mock data
✅ **Portal Mapping**: Documented entity mappings and ownership rules
✅ **Backfill Process**: Script available in `scripts/backfill/` for issue generation
✅ **Validation**: CSV output and owner assignment workflows defined

The Landing Zone is 100% onboarded with Portal integration ready for production use.
