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

# Managed SSL certificate for the public domain
resource "google_compute_managed_ssl_certificate" "portal_cert" {
  name = "portal-ssl-cert"
  managed {
    domains = [var.domain]
  }
}

# Frontend backend bucket (GCS)
resource "google_compute_backend_bucket" "frontend" {
  name        = "portal-frontend-bucket"
  bucket_name = var.frontend_bucket
  enable_cdn  = true
}

# Serverless NEG for Cloud Run backend
resource "google_compute_region_network_endpoint_group" "run_neg" {
  name                  = "portal-backend-neg"
  region                = var.region
  network_endpoint_type = "SERVERLESS"
  cloud_run {
    service = var.cloud_run_service_name
  }
}

# Backend service for API (attaches serverless NEG)
resource "google_compute_backend_service" "api_backend" {
  name                  = "portal-api-backend"
  protocol              = "HTTP"
  load_balancing_scheme = "EXTERNAL"

  backend {
    group = google_compute_region_network_endpoint_group.run_neg.id
  }

  health_checks = []
}

# URL map with path rules for /lz
resource "google_compute_url_map" "portal" {
  name            = "portal-url-map"
  default_service = google_compute_backend_bucket.frontend.id

  host_rule {
    hosts        = [var.domain]
    path_matcher = "pm-lz"
  }

  path_matcher {
    name            = "pm-lz"
    default_service = google_compute_backend_bucket.frontend.id

    path_rule {
      paths   = ["/lz/api/*"]
      service = google_compute_backend_service.api_backend.id
    }

    # Serve SPA assets and index.html under /lz
    path_rule {
      paths   = ["/lz/*"]
      service = google_compute_backend_bucket.frontend.id
    }
  }
}

# HTTPS proxy
resource "google_compute_target_https_proxy" "portal" {
  name             = "portal-https-proxy"
  url_map          = google_compute_url_map.portal.id
  ssl_certificates = [google_compute_managed_ssl_certificate.portal_cert.id]
}

# Global forwarding rule (HTTPS)
resource "google_compute_global_forwarding_rule" "portal_https" {
  name        = "portal-https-rule"
  target      = google_compute_target_https_proxy.portal.id
  port_range  = "443"
  ip_protocol = "TCP"
}

# Enable IAP on the backend service (OAuth client provided by Landing Zone)
resource "google_iap_web_backend_service" "iap_api" {
  name = google_compute_backend_service.api_backend.name

  iap {
    enabled              = true
    oauth2_client_id     = var.iap_client_id
    oauth2_client_secret = var.iap_client_secret
  }
}
