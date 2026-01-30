# AI Agent Guide — GCP Landing Zone Portal

## Purpose
Provide concise, actionable rules for AI coding agents working in this repo.

## High-level rules
- Preserve FAANG-grade patterns: structured logging, request_id, explicit health checks, and Workload Identity for GCP access.
- Avoid making large cross-cutting changes without a plan and tests. Use small, focused edits.
- Do not store secrets in code or K8s; use Google Secret Manager (see `k8s/backend-deployment.yaml`).

## Workflow for code changes
1. Create a short todo plan and track it (use repo TODOs or the `manage_todo_list` flow).
2. Read relevant files: `backend/main.py`, `docs/LOCAL_SETUP.md`, `docs/TESTING.md`, and `ARCHITECTURE.md`.
3. Update tests or add tests when changing behavior in `backend/services` or `backend/routers`.
4. Use `./run.sh dev` for local Docker-based dev; prefer `docker-compose.dev.yml` for hot-reload.

## Branch, PR & commit guidance
- Branch naming: `feature/*`, `fix/*`, or `copilot/*` for agent branches.
- PR description: include intent, files changed, test plan, and validation steps.
- Use small commits with clear messages and link to related issues.

## Quick commands
- Local dev (docker-compose):

```bash
./run.sh dev
# or
docker-compose -f docker-compose.dev.yml up -d
```

- Run backend tests (inside repo):

```bash
cd backend
pytest -q
```

- Frontend tests:

```bash
cd frontend
npm test
```

## When to ask for human review
- Any change touching IAM, encryption, or secrets handling.
- Changes to the Terraform layers or CI/CD (cloudbuild.yaml, scripts/deployment).
- Adding or changing production K8s manifests.

## Issue-driven workflow (mandatory)

Agents must follow an issue-first workflow for all changes.

- **Create an issue** before coding. Include a concise plan and expected tests.
- **Reference the issue** in every commit and PR (use `(#<issue>)` in commit subjects or bodies).
- **Comment progress** to the issue: `WIP`, `running tests`, `ready for review`.
- **Run tests** locally or in the devcontainer and paste results into the issue.
- **Request a peer review**, address feedback, and merge only after at least one approval.
- **Close the issue** with a final comment referencing the merged PR(s) and test status.

Examples (CLI):

```bash
# create issue
gh issue create --title "feat: add X" --body "Plan: ..."

# commit referencing issue
git commit -m "feat(api): implement X (#162)"

# open PR referencing issue
gh pr create --title "feat(api): implement X (#162)" --body "Closes #162"

# close issue after merge
gh issue close 162 --comment "Merged PR #133. Tests passing. Closing."
```

## Minimal examples
- Adding a router: put handlers in `backend/routers/`, use Pydantic models from `backend/models/schemas.py`, and register in `backend/main.py`.
- Adding a service: add a module under `backend/services/`, add unit tests under `backend/tests/`, and mock GCP clients in tests.

## Contacts & PR links
- Active feature branch: copilot/ruling-krill (see PR: [WIP] Fix issue related to CI/CD and release hardening)


