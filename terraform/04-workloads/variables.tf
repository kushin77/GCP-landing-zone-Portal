variable "project_id" { type = string }
variable "region" { type = string default = "us-central1" }
variable "domain" { type = string description = "Public domain, e.g., elevatediq.ai" }
variable "frontend_bucket" { type = string description = "GCS bucket hosting SPA artifacts" }
variable "cloud_run_service_name" { type = string description = "Cloud Run service name for backend API" }
variable "iap_client_id" { type = string description = "IAP OAuth client ID" }
variable "iap_client_secret" { type = string sensitive = true description = "IAP OAuth client secret" }
