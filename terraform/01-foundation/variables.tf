variable "project_id" {
  type        = string
  description = "GCP project ID"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{4,28}[a-z0-9]$", var.project_id))
    error_message = "Invalid project ID format"
  }
}

variable "region" {
  type        = string
  description = "GCP region"
  default     = "us-central1"
}

variable "environment" {
  type        = string
  description = "Environment name (staging, prod)"

  validation {
    condition     = contains(["staging", "prod"], var.environment)
    error_message = "Environment must be 'staging' or 'prod'"
  }
}
