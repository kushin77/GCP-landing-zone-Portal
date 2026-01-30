terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 6.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 6.0"
    }
  }

  backend "gcs" {
    bucket = "portal-terraform-state"
    # prefix set via init: -backend-config="prefix=staging" or "prefix=prod"
  }
}

provider "google" {
  project = var.project_id
  region  = var.region

  default_labels {
    environment   = var.environment
    team          = "platform-engineering"
    managed_by    = "terraform"
    cost_center   = "engineering"
    git_repo      = "github.com/kushin77/GCP-landing-zone-Portal"
  }
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs
resource "google_project_service" "required_apis" {
  for_each = toset([
    "compute.googleapis.com",
    "run.googleapis.com",
    "firestore.googleapis.com",
    "cloudbuild.googleapis.com",
    "secretmanager.googleapis.com",
    "cloudkms.googleapis.com",
    "iap.googleapis.com",
    "cloudarmor.googleapis.com",
    "logging.googleapis.com",
    "monitoring.googleapis.com",
    "container.googleapis.com"
  ])

  service            = each.value
  disable_on_destroy = false
}

# Get current project data
data "google_project" "project" {
  project_id = var.project_id
}
