# Discovery prototype

This folder contains a minimal discovery prototype used to enumerate endpoints and services for the Portal.

How it works
- `service.py` exposes a single endpoint: `/api/v1/discovery/endpoints` that returns a mocked list of endpoints.

Next steps
- Replace mocked data with real GCP API clients (`gcp_clients`) and parsers for `git-rca-workspace`.
- Add caching and incremental discovery to avoid rate limits.

Run locally

Start the backend and visit `/api/v1/discovery/endpoints`.
