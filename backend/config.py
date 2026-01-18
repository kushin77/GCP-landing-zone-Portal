import json

# Backend service metadata
SERVICE_NAME = "landing-zone-portal-backend"
SERVICE_VERSION = "1.0.0"

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
