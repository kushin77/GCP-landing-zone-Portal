import os

# Backend service metadata
SERVICE_NAME = "landing-zone-portal-backend"
SERVICE_VERSION = "1.0.0"

# ============================================================================
# Phase 1 & 2: Network Configuration
# ============================================================================

# Phase 1: IP Address (Current Development/Staging)
# Use LOCAL_IP environment variable instead of PORTAL_IP for clarity
LOCAL_IP = os.getenv("LOCAL_IP", "192.168.168.42")
PORTAL_PORT = int(os.getenv("PORTAL_PORT", "8080"))
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "5173"))
PORTAL_IP_URL = f"http://{LOCAL_IP}:{PORTAL_PORT}"
FRONTEND_IP_URL = f"http://{LOCAL_IP}:{FRONTEND_PORT}"

# Phase 2: DNS Configuration (Environment-specific)
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Environment-specific DNS URLs
ENV_URLS = {
    "development": {
        "domain": os.getenv("DEV_DOMAIN", "dev.elevatedoq.ai"),
        "api_url": os.getenv("DEV_API_URL", "https://dev.elevatedoq.ai/lz"),
        "portal_url": os.getenv("DEV_PORTAL_URL", "https://dev.elevatedoq.ai/portal"),
    },
    "staging": {
        "domain": os.getenv("QA_DOMAIN", "qa.elevatedoq.ai"),
        "api_url": os.getenv("QA_API_URL", "https://qa.elevatedoq.ai/lz"),
        "portal_url": os.getenv("QA_PORTAL_URL", "https://qa.elevatedoq.ai/portal"),
    },
    "production": {
        "domain": os.getenv("PROD_DOMAIN", "elevatedoq.ai"),
        "api_url": os.getenv("PROD_API_URL", "https://elevatedoq.ai/lz"),
        "portal_url": os.getenv("PROD_PORTAL_URL", "https://elevatedoq.ai/portal"),
    },
}

# Determine which URL to use
if ENVIRONMENT == "production":
    PORTAL_URL = ENV_URLS["production"]["portal_url"]
    API_URL = ENV_URLS["production"]["api_url"]
elif ENVIRONMENT == "staging":
    PORTAL_URL = ENV_URLS["staging"]["portal_url"]
    API_URL = ENV_URLS["staging"]["api_url"]
else:  # development
    # Use IP address for local development, NOT localhost
    PORTAL_URL = PORTAL_IP_URL
    API_URL = PORTAL_IP_URL

# CORS Configuration - No localhost/127.0.0.1, use IP address and environment DNS URLs
ALLOWED_ORIGINS = [
    # Phase 1: Local IP Address (development only)
    PORTAL_IP_URL,
    FRONTEND_IP_URL,
    # Phase 2: Environment-specific DNS URLs
    ENV_URLS["development"]["portal_url"],
    ENV_URLS["development"]["api_url"],
    ENV_URLS["staging"]["portal_url"],
    ENV_URLS["staging"]["api_url"],
    ENV_URLS["production"]["portal_url"],
    ENV_URLS["production"]["api_url"],
    # Also allow domain roots
    "https://dev.elevatedoq.ai",
    "https://qa.elevatedoq.ai",
    "https://elevatedoq.ai",
]

# Database configuration
DATABASE_CONFIG = {"project": "portal-prod", "database": "(default)", "collection_prefix": "portal"}

# API configuration
API_CONFIG = {
    "version": "v1",
    "rate_limit": {"requests_per_minute": 100, "burst": 1000},
    "timeout_seconds": 30,
}

# Integration with Hub
HUB_CONFIG = {
    "project_id": None,  # Set via environment variable
    "api_endpoint": "https://hub-api.landing-zone.io",
    "pubsub_topic": "landing-zone-portal-events",
    "bigquery_dataset": "hub_analytics",
}

# Logging configuration
LOGGING_CONFIG = {"level": "INFO", "format": "json", "exclude_paths": ["/health", "/metrics"]}

__all__ = [
    "SERVICE_NAME",
    "SERVICE_VERSION",
    "DATABASE_CONFIG",
    "API_CONFIG",
    "HUB_CONFIG",
    "LOGGING_CONFIG",
    "ENVIRONMENT",
    "PORTAL_URL",
    "API_URL",
    "ALLOWED_ORIGINS",
]


# ---------------------------------------------------------------------------
# Load sensitive values from Google Secret Manager (GSM) when available
# ---------------------------------------------------------------------------
try:
    from backend.services.secret_manager import fetch_and_set_env

    # Secrets we expect to be stored in GSM for production
    _gsm_secrets = [
        "DB_PASSWORD",
        "OAUTH_CLIENT_SECRET",
        "IAP_AUDIENCE",
        "REDIS_URL",
    ]

    # Populate env vars only if they are not already set (local dev override supported)
    fetch_and_set_env(_gsm_secrets)
except Exception:
    # If Secret Manager helper or library isn't available, do nothing.
    pass
