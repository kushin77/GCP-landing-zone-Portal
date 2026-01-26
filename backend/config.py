import json
import os

# Backend service metadata
SERVICE_NAME = "landing-zone-portal-backend"
SERVICE_VERSION = "1.0.0"

# ============================================================================
# Phase 1 & 2: Network Configuration
# ============================================================================

# Phase 1: IP Address (Current Development/Staging)
IP_ADDRESS = os.getenv("PORTAL_IP", "192.168.168.42")
IP_PORT = int(os.getenv("PORTAL_PORT", "8080"))
PORTAL_IP_URL = f"http://{IP_ADDRESS}:{IP_PORT}"

# Phase 2: DNS (Production)
PORTAL_DNS = "https://elevatediq.ai/portal"
PORTAL_API_DNS = "https://elevatediq.ai/lz"

# Determine which URL to use
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
if ENVIRONMENT == "production":
    PORTAL_URL = PORTAL_DNS
    API_URL = PORTAL_API_DNS
else:
    PORTAL_URL = PORTAL_IP_URL
    API_URL = PORTAL_IP_URL

# CORS Configuration - Allow both Phase 1 (IP) and Phase 2 (DNS)
ALLOWED_ORIGINS = [
    PORTAL_IP_URL,
    f"http://{IP_ADDRESS}:5173",  # Frontend dev server
    "http://localhost:5173",
    "http://localhost:8080",
    PORTAL_DNS,
    "https://elevatediq.ai",
    "https://www.elevatediq.ai",
]

# Database configuration
DATABASE_CONFIG = {
    "project": "portal-prod",
    "database": "(default)",
    "collection_prefix": "portal"
}

# API configuration
API_CONFIG = {
    "version": "v1",
    "rate_limit": {
        "requests_per_minute": 100,
        "burst": 1000
    },
    "timeout_seconds": 30
}

# Integration with Hub
HUB_CONFIG = {
    "project_id": None,  # Set via environment variable
    "api_endpoint": "https://hub-api.landing-zone.io",
    "pubsub_topic": "landing-zone-portal-events",
    "bigquery_dataset": "hub_analytics"
}

# Logging configuration
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "json",
    "exclude_paths": ["/health", "/metrics"]
}

__all__ = [
    "SERVICE_NAME",
    "SERVICE_VERSION",
    "DATABASE_CONFIG",
    "API_CONFIG",
    "HUB_CONFIG",
    "LOGGING_CONFIG"
]
