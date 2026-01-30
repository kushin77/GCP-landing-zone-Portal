# Workload Identity Binding for Kubernetes Pods
# Secure pod-to-GCP service account authentication without keys

# Service Account for Backend
resource "google_service_account" "backend" {
  account_id   = "landing-zone-backend"
  display_name = "Landing Zone Backend Service Account"
  project      = var.project_id
}

# Service Account for Frontend
resource "google_service_account" "frontend" {
  account_id   = "landing-zone-frontend"
  display_name = "Landing Zone Frontend Service Account"
  project      = var.project_id
}

# Kubernetes Service Account for Backend
resource "kubernetes_service_account" "backend" {
  metadata {
    name      = "backend"
    namespace = "landing-zone"
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.backend.email
    }
  }
}

# Kubernetes Service Account for Frontend
resource "kubernetes_service_account" "frontend" {
  metadata {
    name      = "frontend"
    namespace = "landing-zone"
    annotations = {
      "iam.gke.io/gcp-service-account" = google_service_account.frontend.email
    }
  }
}

# Workload Identity Binding: Backend Pod → Backend SA
resource "google_service_account_iam_binding" "backend_workload_identity" {
  service_account_id = google_service_account.backend.name
  role               = "roles/iam.workloadIdentityUser"
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[landing-zone/backend]"
  ]
}

# Workload Identity Binding: Frontend Pod → Frontend SA
resource "google_service_account_iam_binding" "frontend_workload_identity" {
  service_account_id = google_service_account.frontend.name
  role               = "roles/iam.workloadIdentityUser"
  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[landing-zone/frontend]"
  ]
}

# Cloud SQL Client role for Backend
resource "google_project_iam_member" "backend_sql_client" {
  project = var.project_id
  role    = "roles/cloudsql.client"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# BigQuery Data Editor for Backend
resource "google_project_iam_member" "backend_bigquery" {
  project = var.project_id
  role    = "roles/bigquery.dataEditor"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Cloud Trace Writer for Backend
resource "google_project_iam_member" "backend_trace_writer" {
  project = var.project_id
  role    = "roles/cloudtrace.agent"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Cloud Monitoring Metric Writer for Backend
resource "google_project_iam_member" "backend_monitoring" {
  project = var.project_id
  role    = "roles/monitoring.metricWriter"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Cloud Logging Writer for Backend
resource "google_project_iam_member" "backend_logging" {
  project = var.project_id
  role    = "roles/logging.logWriter"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# Secret Manager Accessor for Backend
resource "google_project_iam_member" "backend_secrets" {
  project = var.project_id
  role    = "roles/secretmanager.secretAccessor"
  member  = "serviceAccount:${google_service_account.backend.email}"
}

# KMS Decrypter for Backend
resource "google_kms_crypto_key_iam_member" "backend_kms" {
  crypto_key_id = var.kms_key_id
  role          = "roles/cloudkms.cryptoKeyDecrypter"
  member        = "serviceAccount:${google_service_account.backend.email}"
}

# Outputs
output "backend_service_account_email" {
  value       = google_service_account.backend.email
  description = "Backend service account email"
}

output "frontend_service_account_email" {
  value       = google_service_account.frontend.email
  description = "Frontend service account email"
}

output "backend_k8s_sa_name" {
  value       = kubernetes_service_account.backend.metadata[0].name
  description = "Backend Kubernetes service account name"
}

output "frontend_k8s_sa_name" {
  value       = kubernetes_service_account.frontend.metadata[0].name
  description = "Frontend Kubernetes service account name"
}
