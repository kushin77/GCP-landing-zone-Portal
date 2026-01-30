output "project_id" {
  value       = data.google_project.project.project_id
  description = "GCP project ID"
}

output "project_number" {
  value       = data.google_project.project.number
  description = "GCP project number"
}

output "region" {
  value       = var.region
  description = "GCP region"
}
