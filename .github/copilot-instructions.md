# AI Coding Agent Instructions for GCP Landing Zone Portal

## Project Overview
This is a **GCP Landing Zone Portal** - an enterprise-grade control plane for managing GCP infrastructure. It provides a self-service web portal for engineers to handle projects, costs, compliance, and governance, built with a 5-layer architecture (Foundation → Network → Security → Workloads → Observability) plus a portal frontend.

## Architecture & Key Components
- **Backend**: FastAPI (Python) with enterprise middleware stack (auth, rate limiting, security, error handling)
- **Frontend**: React 18 + TypeScript + Vite, using TanStack Query for API calls and Zustand for state
- **Infrastructure**: Terraform modules organized in 5 layers (01-foundation/ to 05-observability/)
- **Deployment**: Docker Compose for local dev, Kubernetes manifests for production
- **Data Flow**: Frontend → REST API → GCP services (BigQuery, Firestore, Cloud Asset Inventory, etc.) via Workload Identity

## Critical Workflows
- **Local Development**: `./run.sh dev` starts full stack with Docker Compose (ports: frontend 3000, backend 8080, Redis 6379)
- **Testing**: `cd backend && pytest` for backend tests; `cd frontend && npm test` for frontend; `./run.sh test` for all
- **Build/Deploy**: `./run.sh deploy` for staging; Cloud Build YAML for CI/CD
- **Debugging**: Structured logging with correlation IDs; health checks verify GCP connectivity; OpenTelemetry traces ready

## Project-Specific Patterns
- **Middleware Stack**: Always include auth, rate limiting, and error handling in new endpoints (see `backend/middleware/`)
- **API Structure**: Use Pydantic models in `backend/models/schemas.py`; routers in `backend/routers/` with service layer separation
- **GCP Integration**: Use service accounts with Workload Identity; handle GCP API errors gracefully with retries
- **Logging**: Include `request_id` in all log messages for traceability (see `backend/main.py`)
- **Health Checks**: Implement actual dependency verification, not just HTTP 200 (see `HealthChecker` class)
- **Frontend State**: Use TanStack Query for server state, Zustand for client state; avoid prop drilling

## Conventions Differing from Standards
- **Environment Variables**: Use `GCP_PROJECT_ID` instead of generic `PROJECT_ID`; `ENVIRONMENT=development` for dev mode
- **Docker Compose**: Use `docker-compose.dev.yml` for development (includes hot reload); production uses `docker-compose.yml`
- **Testing**: Mark tests with `@pytest.mark.unit` or `@pytest.mark.integration`; use fixtures from `backend/tests/conftest.py`
- **Terraform**: Layered approach with numbered directories; use modules extensively for reusability
- **Secrets**: Never store in K8s secrets; use Google Secret Manager with Workload Identity

## Key Files to Reference
- `ARCHITECTURE.md`: 5-layer infrastructure design
- `backend/main.py`: Enterprise FastAPI setup with middleware
- `backend/routers/projects.py`: Example API router pattern
- `frontend/package.json`: React/TypeScript tooling
- `terraform/01-foundation/`: Bootstrap layer example
- `k8s/backend-deployment.yaml`: Production K8s deployment
- `docs/LOCAL_SETUP.md`: Development environment setup
- `docs/TESTING.md`: Testing patterns and commands

## Integration Points
- **GCP Services**: Auth via Workload Identity; data from BigQuery/Firestore; monitoring via Cloud Trace
- **External APIs**: RESTful communication between frontend/backend; WebSocket for real-time updates
- **Caching**: Redis for session/API response caching
- **Observability**: Prometheus metrics exposed on `/metrics`; OpenTelemetry for distributed tracing
 
Focus on maintaining the "FAANG-grade" quality: comprehensive error handling, security-first design, and production-ready patterns.

## Agent Checklist (practical)

- **Start**: Read `docs/LOCAL_SETUP.md`, `docs/TESTING.md`, and `backend/main.py` before making code changes.
- **Local run**: Use `./run.sh dev` or `docker-compose -f docker-compose.dev.yml up -d` to run the stack locally.
- **Testing**: Run `cd backend && pytest -q` for backend unit tests; update or add tests for behavior changes.
- **Auth & Secrets**: Never hardcode credentials. Use `GCP_PROJECT_ID` env and Google Secret Manager for secrets.
- **Observability**: Keep metrics on `/metrics` and preserve OpenTelemetry instrumentation when modifying HTTP handlers.
- **PRs**: Keep changes small, include test plan, list affected Terraform layers if relevant.

## Quick Links
- Active feature branch: copilot/ruling-krill — PR: [WIP] Fix issue related to CI/CD and release hardening
- Dev compose: `docker-compose.dev.yml` (hot reload) — production compose: `docker-compose.yml`

If anything in this guide is unclear, tell me which section and I will expand with concrete examples from the codebase.