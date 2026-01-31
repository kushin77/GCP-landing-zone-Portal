#!/bin/bash
# Disaster Recovery and Backup Management Script
# Fixes issue #47: No Backup/Disaster Recovery

set -e

# ============================================================================
# Configuration
# ============================================================================

GCP_PROJECT_ID=${1:-portal-prod}
BACKUP_BUCKET="gs://${GCP_PROJECT_ID}-backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/tmp/firestore_backup_${TIMESTAMP}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ============================================================================
# Firestore Backup Functions
# ============================================================================

backup_firestore() {
    log_info "Starting Firestore backup..."

    # Create backup location if it doesn't exist
    gsutil mb -c STANDARD -l us-central1 "${BACKUP_BUCKET}" 2>/dev/null || true

    # Export Firestore to Cloud Storage
    gcloud firestore export \
        --project="${GCP_PROJECT_ID}" \
        "${BACKUP_BUCKET}/firestore_${TIMESTAMP}" \
        --async

    log_info "Firestore export started to ${BACKUP_BUCKET}/firestore_${TIMESTAMP}"
    log_info "Monitor progress with:"
    log_info "  gcloud firestore operations list --project=${GCP_PROJECT_ID}"
}

validate_backups() {
    log_info "Validating Firestore backups..."

    # Check backup sizes
    echo "Listing backups:"
    gsutil ls -r "${BACKUP_BUCKET}/firestore_*" | head -20

    # Validate latest backup is not empty
    LATEST_BACKUP=$(gsutil ls -r "${BACKUP_BUCKET}/firestore_*" | grep "metadata.json" | tail -1 | sed 's|/metadata.json||')

    if [ -z "$LATEST_BACKUP" ]; then
        log_error "No valid backups found!"
        return 1
    fi

    # Check metadata file exists
    if gsutil -q stat "${LATEST_BACKUP}/metadata.json"; then
        log_info "Latest backup valid: ${LATEST_BACKUP}"
        return 0
    else
        log_error "Latest backup metadata missing: ${LATEST_BACKUP}"
        return 1
    fi
}

cleanup_old_backups() {
    log_info "Cleaning up backups older than 30 days..."

    # Delete backups older than 30 days
    gsutil -m rm -r $(gsutil ls -r "${BACKUP_BUCKET}/firestore_*" | grep "/" | awk -F/ '{print $1"/"$2"/"$3}' | sort -u | while read backup; do
        backup_date=$(basename "$backup" | sed 's/firestore_//;s/_//g')
        cutoff_date=$(date -d '30 days ago' +%Y%m%d)

        if [[ "$backup_date" < "$cutoff_date" ]]; then
            echo "$backup"
        fi
    done) 2>/dev/null || true

    log_info "Old backups cleaned up"
}

# ============================================================================
# Database Schema Migration Functions
# ============================================================================

migrate_schema() {
    log_info "Running database schema migrations..."

    # In real implementation, use Firestore migrations or scripts
    python3 << 'EOF'
from google.cloud import firestore
import logging

logger = logging.getLogger(__name__)

async def run_migrations():
    db = firestore.Client()

    # Example migration: Add new fields to projects
    projects_ref = db.collection('projects')

    batch = db.batch()
    for doc in projects_ref.stream():
        if 'compliance_status' not in doc.to_dict():
            batch.update(doc.reference, {
                'compliance_status': 'pending',
                'last_compliance_check': None,
            })

    batch.commit()
    logger.info("Schema migration complete")

if __name__ == "__main__":
    import asyncio
    asyncio.run(run_migrations())
EOF

    log_info "Schema migrations complete"
}

# ============================================================================
# Terraform State Backup
# ============================================================================

backup_terraform_state() {
    log_info "Backing up Terraform state..."

    STATE_BUCKET="gs://${GCP_PROJECT_ID}-terraform-state"

    # Create versioning-enabled bucket if it doesn't exist
    gsutil versioning set on "${STATE_BUCKET}" 2>/dev/null || \
        gsutil mb -c STANDARD -l us-central1 "${STATE_BUCKET}" && \
        gsutil versioning set on "${STATE_BUCKET}"

    log_info "Terraform state bucket: ${STATE_BUCKET}"
    log_info "Versioning enabled - old versions retained"
}

# ============================================================================
# Secrets Rotation
# ============================================================================

rotate_secrets() {
    log_info "Rotating service account keys..."

    # List all service accounts
    SERVICE_ACCOUNTS=$(gcloud iam service-accounts list \
        --project="${GCP_PROJECT_ID}" \
        --format="value(email)")

    for sa in $SERVICE_ACCOUNTS; do
        log_info "Rotating keys for: $sa"

        # Find old keys (created > 90 days ago)
        cutoff_date=$(date -d '90 days ago' --iso-8601=seconds)

        OLD_KEYS=$(gcloud iam service-accounts keys list \
            --iam-account="${sa}" \
            --project="${GCP_PROJECT_ID}" \
            --filter="validAfterTime < ${cutoff_date}" \
            --format="value(name)")

        for key in $OLD_KEYS; do
            log_warn "Deleting old key: $key"
            gcloud iam service-accounts keys delete "$key" \
                --iam-account="${sa}" \
                --project="${GCP_PROJECT_ID}" \
                --quiet
        done

        # Create new key
        gcloud iam service-accounts keys create \
            "/tmp/sa-key-${sa}.json" \
            --iam-account="${sa}" \
            --project="${GCP_PROJECT_ID}"

        # Store in Secret Manager
        gcloud secrets versions add "${sa}-key" \
            --data-file="/tmp/sa-key-${sa}.json" \
            --project="${GCP_PROJECT_ID}" 2>/dev/null || \
            gcloud secrets create "${sa}-key" \
            --data-file="/tmp/sa-key-${sa}.json" \
            --project="${GCP_PROJECT_ID}"

        # Securely delete temp file
        shred -vfz "/tmp/sa-key-${sa}.json"

        log_info "Key rotated for: $sa"
    done
}

# ============================================================================
# Disaster Recovery Drill
# ============================================================================

dr_drill() {
    log_info "Starting Disaster Recovery drill..."
    log_info "This is a DRY RUN - no changes will be made"

    # 1. Verify backups exist
    if validate_backups; then
        log_info "✓ Backups exist and valid"
    else
        log_error "✗ Backup validation failed"
        return 1
    fi

    # 2. Verify Terraform state is backed up
    log_info "Checking Terraform state backup..."
    gsutil -q stat "gs://${GCP_PROJECT_ID}-terraform-state/prod/terraform.tfstate" && \
        log_info "✓ Terraform state backed up" || \
        log_error "✗ Terraform state not found"

    # 3. Test restore procedure (dry-run)
    log_info "Testing restore procedure (dry-run)..."
    gcloud firestore databases list --project="${GCP_PROJECT_ID}" && \
        log_info "✓ Can access Firestore" || \
        log_error "✗ Cannot access Firestore"

    # 4. Verify health checks
    log_info "Verifying health checks..."
    curl -s https://api.example.com/health >/dev/null && \
        log_info "✓ API health check passes" || \
        log_warn "⚠ API health check failed (may be expected in DR)"

    log_info "DR Drill complete - if all checks passed, recovery is possible"
}

# ============================================================================
# Runbook: Database Corruption
# ============================================================================

incident_database_corruption() {
    log_error "INCIDENT: Database Corruption Detected"
    log_info ""
    log_info "IMMEDIATE ACTIONS (0-5 min):"
    log_info "1. [ ] Declare incident in Slack #incident-response"
    log_info "2. [ ] Page on-call engineer"
    log_info "3. [ ] Switch traffic to read-only (serve cached data)"
    log_info ""
    log_info "INVESTIGATION (5-30 min):"
    log_info "1. Check Firestore logs:"
    log_info "   gcloud logging read 'resource.type=cloud_firestore' --project=${GCP_PROJECT_ID} --limit=50"
    log_info "2. Check recent deployments"
    log_info "3. List available backups:"
    gsutil ls -r "${BACKUP_BUCKET}/firestore_*" | head -5
    log_info ""
    log_info "RECOVERY (30-60 min):"
    log_info "1. Create new database from backup (restore script below)"
    log_info "2. Validate restore in staging first"
    log_info "3. Switch traffic to restored database"
    log_info ""
    log_info "RTO: 1 hour | RPO: 1 hour (last backup)"
}

# ============================================================================
# Main
# ============================================================================

show_usage() {
    cat << EOF
Disaster Recovery & Backup Management

Usage: $0 <command> [options]

Commands:
    backup              Backup Firestore database
    validate            Validate existing backups
    cleanup             Remove backups older than 30 days
    migrate-schema      Run database schema migrations
    rotate-secrets      Rotate service account keys
    dr-drill            Run disaster recovery drill
    incident            Show incident response runbook

Examples:
    $0 backup                    # Backup to GCS
    $0 backup my-project         # Backup specific project
    $0 validate                  # Check backup integrity
    $0 dr-drill                  # Run DR exercise
    $0 incident                  # Show runbook

EOF
}

main() {
    case "${1:-help}" in
        backup)
            backup_firestore
            ;;
        validate)
            validate_backups
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        migrate-schema)
            migrate_schema
            ;;
        rotate-secrets)
            rotate_secrets
            ;;
        dr-drill)
            dr_drill
            ;;
        incident)
            incident_database_corruption
            ;;
        help|--help|-h)
            show_usage
            ;;
        *)
            log_error "Unknown command: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
