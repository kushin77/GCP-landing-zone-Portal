# Contributing to Landing Zone Portal

Thank you for contributing to the Landing Zone Portal! This document outlines our development workflow, code standards, and submission process.

## Code of Conduct

- Be respectful and inclusive
- No discriminatory language
- Assume good intent, communicate clearly
- Escalate conflicts to @platform-engineering

## Getting Started

### 1. Prerequisites

- Node.js 20+
- Python 3.11+
- Terraform 1.7+
- Docker + Docker Compose
- Git (with GPG signing configured)

### 2. Local Setup

```bash
# Clone
git clone https://github.com/kushin77/GCP-landing-zone-Portal.git
cd GCP-landing-zone-Portal

# Install dependencies
cd frontend && npm install && cd ..
cd backend && pip install -r requirements-dev.txt && cd ..

# Start local dev environment
./run.sh dev
```

### 3. Create a Branch

```bash
# Branch naming: feature/*, fix/*, security/*, docs/*
git checkout -b feature/your-feature-name

# Configure git for GPG signing (if not already done)
git config --global user.signingkey [YOUR_GPG_KEY_ID]
git config --global commit.gpgsign true
```

## Development Workflow

### Atomic Commits (REQUIRED)

Every commit must follow these rules:

1. **One logical change** — One feature/fix per commit
2. **1-5 files max** — Keep scope tight
3. **GPG signed** — `git commit -S -m "message"`
4. **Clear message** — Explain "why", not "what"
5. **Issue reference** — `Closes #123`

### Commit Message Format

```
<type>(<scope>): <subject>

<body explaining WHY and WHAT>

<footer with issue reference>

Signed-off-by: Your Name <you@example.com>
```

**Types**: `feat`, `fix`, `security`, `docs`, `refactor`, `perf`, `chore`

**Example**:

```
feat(dashboard): add real-time cost card

Dashboard now displays:
- Daily spend with trend
- Monthly forecast
- Budget status (on-track/at-risk/over)
- Auto-refresh every 30s via TanStack Query

Implements cost transparency for all teams.

Closes #45
Signed-off-by: Jane Doe <jane@example.com>
```

### Code Quality Standards

#### Frontend (React + TypeScript)

- ✅ **TypeScript**: Strict mode, no `any`
- ✅ **ESLint**: All rules pass
- ✅ **Prettier**: Auto-formatted
- ✅ **Tests**: >80% coverage
- ✅ **Accessibility**: WCAG 2.1 AAA compliant

#### Backend (FastAPI + Python)

- ✅ **Type Hints**: All functions annotated
- ✅ **Black**: Auto-formatted
- ✅ **Flake8**: All lint rules pass
- ✅ **Tests**: >80% coverage (pytest)
- ✅ **Docstrings**: All functions documented

#### Infrastructure (Terraform)

- ✅ **Format**: `terraform fmt -recursive`
- ✅ **Validation**: `terraform validate`
- ✅ **Naming**: Follow 5-layer depth pattern
- ✅ **Comments**: Explain "why" for complex resources
- ✅ **Labels**: All resources tagged (environment, team, etc.)

### Pre-Commit Hooks

Pre-commit hooks run automatically before each commit:

```bash
# Install hooks (one time)
pre-commit install

# Run manually (before commit)
pre-commit run --all-files

# Hooks check:
- Formatting (Prettier, Black)
- Linting (ESLint, Flake8)
- Secret scanning (Gitleaks)
- Commit message format (Conventional commits)
```

## Testing

### Run Tests Locally

```bash
# All tests
./run.sh test

# Frontend only
cd frontend && npm test

# Backend only
cd backend && pytest tests/

# With coverage
cd backend && pytest --cov=src tests/ --cov-report=html
```

### Test Requirements

- **Unit Tests**: Cover all functions/components
- **Integration Tests**: Test API endpoints with mocks
- **E2E Tests**: Critical user journeys (login, dashboard, create request)
- **Coverage Target**: >80% for all code

### CI Validation

Before submitting a PR, ensure CI passes:

1. **GitHub Actions**: All workflows must pass (backend CI, frontend CI, terraform CI)
2. **Cloud Build**: If deploying, ensure build succeeds
3. **Security Scans**: Snyk, Trivy, Semgrep must pass
4. **Coverage**: Backend coverage >80%

Run locally to verify:

```bash
# Pre-commit checks
pre-commit run --all-files

# Backend tests with coverage
cd backend && pytest --cov=. --cov-report=term-missing

# Frontend tests
cd frontend && npm test

# Terraform validation
cd terraform && terraform fmt -check && terraform validate
```

## Pull Request Process

### 1. Create PR on GitHub

```bash
git push origin feature/your-feature-name
```

Then create PR with this template:

```markdown
## What This Does

Brief description of the feature/fix.

## How To Test

1. Start dev environment: ./run.sh dev
2. Navigate to X
3. Verify Y happens

## Checklist

- [ ] Tests pass locally (npm test + pytest)
- [ ] CI workflows pass (GitHub Actions + Cloud Build)
- [ ] Security scans pass (Snyk, Trivy, Semgrep)
- [ ] Code coverage >80%
- [ ] Pre-commit hooks pass
- [ ] Commit is GPG signed
- [ ] Docs updated (if needed)
- [ ] No hardcoded secrets

## Related Issues

Closes #123
```

### 2. Code Review

- Assign 2+ reviewers (frontend, backend, or ops as needed)
- Address all feedback
- Re-request review after changes
- All conversations must be resolved before merge

### 3. Automated Checks

PR must pass all GitHub status checks:

- ✅ `test` — Unit tests pass
- ✅ `lint` — Linting passes
- ✅ `security` — Snyk + Gitleaks pass
- ✅ `coverage` — Coverage >80%
- ✅ `approval` — 2+ approvals

### 4. Merge

Only maintainers can merge PRs. Merge is done by:

```bash
# Merges via GitHub UI (automatic CI/CD triggers)
# - Deploys to staging automatically
# - Runs E2E tests on staging
# - Waits for manual approval to prod
```

## Security

### Secret Management

**❌ NEVER commit**:

- API keys, passwords, credentials
- Private keys (`.pem`, `.key`, `.pfx`)
- Service account JSON files
- Database credentials

**✅ DO**:

- Store in Secret Manager (production)
- Use `.env.example` for documentation (no values)
- Reference secrets via environment variables
- Rotate credentials regularly

### Running Security Scans

```bash
# Snyk (dependency scanning)
snyk test --severity-threshold=high

# Gitleaks (secret scanning)
gitleaks detect --source git

# Pre-commit (local checks)
pre-commit run --all-files
```

## Documentation

### Required Documentation

- `docs/API.md` — Updated if API changes
- `docs/ARCHITECTURE.md` — Updated if architecture changes
- `docs/development/*.md` — Setup/dev guides
- `README.md` — Updated if project scope changes
- Code comments — "Why" comments, not "what"

### Inline Documentation Standards

```python
def calculate_cost(project_id: str) -> float:
    """
    Calculate monthly cost for a GCP project.

    Args:
        project_id: GCP project ID

    Returns:
        Monthly cost in USD

    Raises:
        ProjectNotFoundError: If project doesn't exist

    Note:
        Uses Hub BigQuery dataset (read-only).
        Results cached for 5 minutes.
    """
```

## Performance

### Frontend Performance Targets

- Lighthouse score: >90 on all pages
- First Contentful Paint (FCP): <2s
- Largest Contentful Paint (LCP): <2.5s
- Cumulative Layout Shift (CLS): <0.1

### Backend Performance Targets

- P95 latency: <100ms
- P99 latency: <500ms
- Error rate: <0.1%
- Max connections: Auto-scale (Cloud Run)

## Questions?

- 📖 See docs/ folder
- 💬 Ask in #portal-dev Slack
- 🐛 Create GitHub issue
- 📞 Ask @platform-engineering

---

**Thank you for contributing!** 🎉
