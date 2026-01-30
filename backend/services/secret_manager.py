"""
Google Secret Manager helper utilities.

Provides a small wrapper to fetch secrets at runtime and optionally populate
environment variables for downstream code to read. Safe to import when
Secret Manager isn't available (will no-op and leave env vars intact).

Usage:
    from backend.services.secret_manager import fetch_and_set_env
    fetch_and_set_env(["DB_PASSWORD", "OAUTH_CLIENT_SECRET", "IAP_AUDIENCE"])

This avoids committing secrets into the repository and supports CI patterns
that populate secrets in GSM and grant access to the runtime service account.
"""
import logging
import os
from typing import Iterable, Optional

logger = logging.getLogger(__name__)


def _get_project_id() -> Optional[str]:
    # Prefer explicit env var, fall back to common names
    for key in ("GCP_PROJECT_ID", "GCP_PROJECT", "GOOGLE_CLOUD_PROJECT", "PROJECT_ID"):
        if os.getenv(key):
            return os.getenv(key)
    return None


def get_secret(
    secret_id: str, project_id: Optional[str] = None, version: str = "latest"
) -> Optional[str]:
    """Retrieve a secret value from Google Secret Manager.

    Returns the secret string or None if Secret Manager is unavailable or access fails.
    """
    try:
        from google.cloud import secretmanager
    except Exception:
        logger.debug("google-cloud-secret-manager not installed or unavailable")
        return None

    try:
        client = secretmanager.SecretManagerServiceClient()

        project = project_id or _get_project_id() or os.getenv("PROJECT_ID")
        if not project:
            logger.debug("No GCP project configured for Secret Manager access")
            return None

        name = f"projects/{project}/secrets/{secret_id}/versions/{version}"
        response = client.access_secret_version(request={"name": name})
        payload = response.payload.data.decode("UTF-8")
        return payload
    except Exception as e:
        logger.warning(f"Failed to access secret {secret_id}: {e}")
        return None


def fetch_and_set_env(secret_names: Iterable[str], project_id: Optional[str] = None) -> None:
    """Fetch a list of secrets and set them as environment variables if unset.

    Only sets variables that are not already present in the environment.
    """
    for name in secret_names:
        if os.getenv(name):
            logger.debug(f"Env var {name} already set; skipping Secret Manager fetch")
            continue

        value = get_secret(name, project_id=project_id)
        if value is not None:
            os.environ[name] = value
            logger.info(f"Loaded secret into environment: {name}")
        else:
            logger.debug(f"Secret {name} not loaded (not found or access denied)")
