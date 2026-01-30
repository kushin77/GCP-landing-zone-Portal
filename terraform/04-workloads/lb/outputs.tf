output "https_forwarding_rule" {
  value = google_compute_global_forwarding_rule.portal_https.name
}

output "url_map" {
  value = google_compute_url_map.portal.name
}

output "api_backend_service" {
  value = google_compute_backend_service.api_backend.name
}
