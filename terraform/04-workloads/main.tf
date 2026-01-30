terraform {
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = ">= 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

module "portal_lb" {
  source = "./lb"

  project_id             = var.project_id
  region                 = var.region
  domain                 = var.domain
  frontend_bucket        = var.frontend_bucket
  cloud_run_service_name = var.cloud_run_service_name
  iap_client_id          = var.iap_client_id
  iap_client_secret      = var.iap_client_secret
}
