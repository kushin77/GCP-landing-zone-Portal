# KMS Key for Database Encryption
resource "google_kms_key_ring" "landing_zone" {
  name     = "landing-zone-keyring"
  location = var.region
  project  = var.project_id
}

# Primary encryption key for secrets & databases
resource "google_kms_crypto_key" "database_key" {
  name            = "database-encryption-key"
  key_ring        = google_kms_key_ring.landing_zone.id
  rotation_period = "2592000s" # 30 days
  lifecycle {
    prevent_destroy = true
  }
}

# Secondary key for key rotation (blue-green)
resource "google_kms_crypto_key" "database_key_secondary" {
  name            = "database-encryption-key-secondary"
  key_ring        = google_kms_key_ring.landing_zone.id
  rotation_period = "2592000s"
  lifecycle {
    prevent_destroy = true
  }
}

# Backup encryption key (separate key ring)
resource "google_kms_key_ring" "backup" {
  name     = "backup-keyring"
  location = var.region
  project  = var.project_id
}

resource "google_kms_crypto_key" "backup_key" {
  name            = "backup-encryption-key"
  key_ring        = google_kms_key_ring.backup.id
  rotation_period = "2592000s"
  lifecycle {
    prevent_destroy = true
  }
}

# Audit logging key (immutable)
resource "google_kms_crypto_key" "audit_key" {
  name            = "audit-log-encryption"
  key_ring        = google_kms_key_ring.landing_zone.id
  rotation_period = "7776000s" # 90 days (longer for audit compliance)
  lifecycle {
    prevent_destroy = true
  }
}

# Secret Manager Secret: Database Password
resource "google_secret_manager_secret" "db_password" {
  secret_id = "landing-zone-db-password"
  project   = var.project_id
  replication {
    automatic = true
  }
  labels = {
    app           = "landing-zone"
    rotation      = "automatic"
    frequency     = "30-days"
  }
}

# Database password secret version
resource "google_secret_manager_secret_version" "db_password" {
  secret      = google_secret_manager_secret.db_password.id
  secret_data = var.db_password # Should be passed from CI/CD
}

# Secret: API Keys
resource "google_secret_manager_secret" "api_keys" {
  secret_id = "landing-zone-api-keys"
  project   = var.project_id
  replication {
    automatic = true
  }
  labels = {
    app       = "landing-zone"
    rotation  = "quarterly"
  }
}

# Secret: OAuth Client Credentials
resource "google_secret_manager_secret" "oauth_credentials" {
  secret_id = "landing-zone-oauth-credentials"
  project   = var.project_id
  replication {
    automatic = true
  }
  labels = {
    app      = "landing-zone"
    rotation = "quarterly"
  }
}

# Secret: JWT Signing Key
resource "google_secret_manager_secret" "jwt_key" {
  secret_id = "landing-zone-jwt-key"
  project   = var.project_id
  replication {
    automatic = true
  }
  labels = {
    app       = "landing-zone"
    rotation  = "annually"
  }
}

# Secret rotation using Cloud Scheduler + Cloud Functions (trigger every 30 days)
resource "google_cloud_scheduler_job" "secret_rotation" {
  name             = "secret-rotation-trigger"
  description      = "Trigger database password rotation every 30 days"
  schedule         = "0 2 1 * *" # 2 AM on first of month
  time_zone        = "UTC"
  attempt_deadline = "600s"
  region           = var.region
  project          = var.project_id

  http_target {
    http_method = "POST"
    uri         = google_cloudfunctions_function.rotate_secrets.https_trigger_url
    auth_header {
      update_value = true
    }
  }
}

# Cloud Function for Secret Rotation
resource "google_cloudfunctions_function" "rotate_secrets" {
  name        = "rotate-secrets"
  description = "Rotate database passwords and API keys"
  runtime     = "python39"
  available_memory_mb = 256
  source_archive_bucket = google_storage_bucket.function_source.name
  source_archive_object = google_storage_bucket_object.function_zip.name
  event_trigger {
    event_type = "google.pubsub.topic.publish"
    resource   = google_pubsub_topic.rotation_trigger.id
  }
  environment_variables = {
    PROJECT_ID      = var.project_id
    SECRET_ID       = google_secret_manager_secret.db_password.secret_id
    KMS_KEY_ID      = google_kms_crypto_key.database_key.id
  }
}

# Cloud Storage bucket for Cloud Function source code
resource "google_storage_bucket" "function_source" {
  name     = "${var.project_id}-function-source"
  location = var.region
  project  = var.project_id
  encryption {
    default_kms_key_name = google_kms_crypto_key.database_key.id
  }
}

# Pub/Sub topic for rotation triggers
resource "google_pubsub_topic" "rotation_trigger" {
  name    = "secret-rotation-trigger"
  project = var.project_id
  labels = {
    app = "landing-zone"
  }
}

# Pub/Sub subscription for rotation handler
resource "google_pubsub_subscription" "rotation_trigger_sub" {
  name    = "secret-rotation-trigger-sub"
  topic   = google_pubsub_topic.rotation_trigger.name
  project = var.project_id
  push_config {
    push_endpoint = google_cloudfunctions_function.rotate_secrets.https_trigger_url
    attributes = {
      x-goog-version = "v1"
    }
  }
}

# Audit logging for secret access
resource "google_logging_project_sink" "secret_access_logs" {
  name        = "secret-manager-audit-sink"
  destination = "storage.googleapis.com/${google_storage_bucket.audit_logs.name}"
  filter      = "resource.type=secretmanager.googleapis.com AND protoPayload.methodName=google.iam.admin.v1.GetServiceAccountKey"
  project     = var.project_id
}

# Bucket for audit logs (immutable, encrypted, long retention)
resource "google_storage_bucket" "audit_logs" {
  name          = "${var.project_id}-audit-logs"
  location      = var.region
  project       = var.project_id
  force_destroy = false

  uniform_bucket_level_access = true

  encryption {
    default_kms_key_name = google_kms_crypto_key.audit_key.id
  }

  lifecycle_rule {
    condition {
      age = 2555 # 7 years for compliance
    }
    action {
      type = "Delete"
    }
  }

  versioning {
    enabled = true
  }
}

# Lock bucket from deletion
resource "google_storage_bucket_object_retention_lock" "audit_logs" {
  bucket = google_storage_bucket.audit_logs.name
  object = "audit-lock"
}

# VPC Service Controls for secret access
resource "google_access_context_manager_access_policy" "policy" {
  parent = "organizations/${var.org_id}"
  title  = "Landing Zone Access Policy"
}

resource "google_access_context_manager_service_perimeter" "secrets" {
  parent         = google_access_context_manager_access_policy.policy.name
  name           = "accessPolicies/${google_access_context_manager_access_policy.policy.name}/servicePerimeters/secrets"
  title          = "Secrets Perimeter"
  perimeter_type = "PERIMETER_TYPE_REGULAR"

  status {
    restricted_services = [
      "secretmanager.googleapis.com",
      "cloudkms.googleapis.com"
    ]
    access_levels = [
      google_access_context_manager_access_level.landing_zone_vpc.name
    ]
  }
}

# Access Level for on-premises/VPN connections
resource "google_access_context_manager_access_level" "landing_zone_vpc" {
  parent      = google_access_context_manager_access_policy.policy.name
  name        = "accessPolicies/${google_access_context_manager_access_policy.policy.name}/accessLevels/landingZoneVpc"
  title       = "Landing Zone VPC"
  description = "Access from Landing Zone VPC"
  basic {
    conditions {
      vpc_network_sources {
        network_name = var.vpc_network_name
      }
    }
  }
}

# Outputs
output "kms_key_id" {
  value       = google_kms_crypto_key.database_key.id
  description = "KMS key ID for database encryption"
}

output "backup_kms_key_id" {
  value       = google_kms_crypto_key.backup_key.id
  description = "KMS key ID for backup encryption"
}

output "database_password_secret_id" {
  value       = google_secret_manager_secret.db_password.id
  description = "Secret Manager secret ID for database password"
}

output "audit_logs_bucket_name" {
  value       = google_storage_bucket.audit_logs.name
  description = "GCS bucket for immutable audit logs"
}
