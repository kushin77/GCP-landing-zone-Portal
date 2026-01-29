# Local Development Setup

This guide walks you through setting up the GCP Landing Zone Portal for local development.

## Prerequisites

- Python 3.11 or higher
- Docker and Docker Compose
- Google Cloud SDK (`gcloud` CLI)
- Git
- GitHub CLI (`gh`) - recommended

## Option 1: Development Container (Recommended)

### Using VS Code Dev Container

1. Install the "Dev Containers" extension in VS Code
2. Clone the repository:
   ```bash
   git clone https://github.com/kushin77/GCP-landing-zone-Portal.git
   cd GCP-landing-zone-Portal
   ```
3. Open in VS Code: `code .`
4. Press `Ctrl+Shift+P` (or `Cmd+Shift+P` on Mac)
5. Select "Dev Containers: Reopen in Container"
6. Wait for the container to build and start

The development container includes:
- Python 3.11+ with all dependencies
- Google Cloud SDK
- Docker CLI
- All required tools

### Using Docker Compose

```bash
# Clone the repository
git clone https://github.com/kushin77/GCP-landing-zone-Portal.git
cd GCP-landing-zone-Portal

# Build and start services
docker-compose -f docker-compose.dev.yml up -d

# Verify services are running
docker-compose -f docker-compose.dev.yml ps

# Access the container
docker-compose -f docker-compose.dev.yml exec backend bash
```

## Option 2: Virtual Environment (Manual Setup)

### Step 1: Clone Repository

```bash
git clone https://github.com/kushin77/GCP-landing-zone-Portal.git
cd GCP-landing-zone-Portal
```

### Step 2: Create Virtual Environment

Using Python venv:
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

Using conda:
```bash
conda create -n gcp-lz python=3.11
conda activate gcp-lz
```

### Step 3: Install Dependencies

```bash
# Backend dependencies
cd backend
pip install -r requirements.txt
pip install -e .

# Frontend dependencies
cd ../frontend
npm install
```

### Step 4: Configure Environment

Create a `.env` file in the backend directory:

```bash
# Backend settings
ENVIRONMENT=development
LOG_LEVEL=DEBUG
SECRET_KEY=your-secret-key-here

# GCP Settings
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1

# Database
DATABASE_URL=postgresql://user:password@localhost/gcp_lz_dev

# Optional: GitHub PAT (for development/testing)
GITHUB_TOKEN=your-github-token-here
```

### Step 5: Initialize Database

```bash
cd backend

# For PostgreSQL (if using Docker Compose)
psql -h localhost -U postgres -d gcp_lz_dev -f init.sql

# For SQLite (development default)
python -c "from app import create_app; app = create_app(); app.db.create_all()"
```

## Running the Application

### Backend (FastAPI)

```bash
cd backend

# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
gunicorn -w 4 -b 0.0.0.0:8000 main:app
```

**Access:** http://localhost:8000  
**API Docs:** http://localhost:8000/docs

### Frontend (React/Vite)

```bash
cd frontend

# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

**Access:** http://localhost:5173

### Running Both Services

Using Docker Compose:
```bash
docker-compose -f docker-compose.dev.yml up
```

Using tmux (in separate terminals):
```bash
# Terminal 1: Backend
cd backend && uvicorn main:app --reload

# Terminal 2: Frontend  
cd frontend && npm run dev

# Terminal 3: Testing/other work
# Your commands here
```

## Running Tests

### Unit Tests

```bash
cd backend

# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_api.py

# Run with coverage
pytest --cov=./ --cov-report=html
```

### Test Configuration

Tests are configured in `backend/pytest.ini`:
- Test discovery: `tests/test_*.py` and `*_test.py`
- Markers: `pytest.mark.unit`, `pytest.mark.integration`
- Coverage threshold: 80%+

### Linting & Code Quality

```bash
cd backend

# Format with Black
black . --check

# Auto-fix formatting
black .

# Lint with Pylint
pylint --rc-file=.pylintrc *.py

# Type checking
mypy --config-file=mypy.ini backend/
```

## GCP Configuration

### Authenticate with GCP

```bash
# Login to GCP
gcloud auth login

# Set default project
gcloud config set project YOUR_PROJECT_ID

# Create service account (if needed)
gcloud iam service-accounts create lz-dev-sa \
  --display-name="Landing Zone Dev SA"

# Create and download service account key
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=lz-dev-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Set environment variable
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/sa-key.json"
```

### Verify GCP Access

```bash
# Check authentication
gcloud auth list

# List available projects
gcloud projects list

# Describe current project
gcloud config get-value project
```

## Troubleshooting

### Python Issues

**Problem:** `python3.11: command not found`
- **Solution:** Install Python 3.11 via `brew install python@3.11` (Mac) or your system package manager
- **Alternative:** Use conda: `conda create -n gcp-lz python=3.11`

**Problem:** Pip modules not found
- **Solution:** Activate virtual environment first: `source venv/bin/activate`

### Docker Issues

**Problem:** Permission denied when running Docker
- **Solution:** Add your user to docker group: `sudo usermod -aG docker $USER`
- **Solution:** Or use `sudo docker` for commands

**Problem:** Port already in use
- **Solution:** Change port in command: `docker-compose -f docker-compose.dev.yml -p different-name up`
- **Solution:** Kill existing process: `lsof -i :8000` then `kill -9 <PID>`

### Database Issues

**Problem:** Cannot connect to PostgreSQL
- **Solution:** Verify service running: `docker-compose -f docker-compose.dev.yml ps`
- **Solution:** Check credentials in `.env` file
- **Solution:** Reset database: `docker-compose -f docker-compose.dev.yml down -v && docker-compose -f docker-compose.dev.yml up`

### GCP Issues

**Problem:** Authentication required
- **Solution:** Run `gcloud auth login` or set `GOOGLE_APPLICATION_CREDENTIALS`

**Problem:** Permission denied
- **Solution:** Verify service account has required IAM roles
- **Solution:** Check `gcloud projects get-iam-policy PROJECT_ID`

## Development Workflow

### Creating a Feature Branch

```bash
# Update main branch
git checkout main
git pull origin main

# Create feature branch
git checkout -b feat/your-feature-name

# Make changes and commit
git add .
git commit -m "feat: add your feature"

# Push to remote
git push origin feat/your-feature-name
```

### Running Tests Before Push

```bash
# Ensure tests pass
pytest -v --cov

# Check code formatting
black --check .

# Verify linting
pylint backend/

# Build frontend
cd frontend && npm run build
```

### Creating a Pull Request

1. Push your branch to GitHub
2. Open pull request on GitHub
3. Ensure CI checks pass (automated)
4. Request review from @kushin77
5. Address review feedback
6. Merge when approved

## Useful Commands

```bash
# Backend virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests with coverage
pytest --cov=backend --cov-report=term-missing --cov-report=html

# Generate requirements.txt from environment
pip freeze > requirements.txt

# Check for security vulnerabilities
pip install safety
safety check

# Frontend package updates
npm outdated
npm update
npm audit fix
```

## Next Steps

- Read [CONTRIBUTING.md](https://github.com/kushin77/GCP-landing-zone-Portal/blob/main/CONTRIBUTING.md)
- Review [TESTING.md](https://github.com/kushin77/GCP-landing-zone-Portal/blob/main/docs/TESTING.md)
- Check [SECURITY.md](https://github.com/kushin77/GCP-landing-zone-Portal/blob/main/SECURITY.md)
- Join the team discussion on GitHub Discussions

## Getting Help

- 📖 Check the [README](https://github.com/kushin77/GCP-landing-zone-Portal/blob/main/README.md)
- 🐛 Open an issue if you find problems
- 💬 Start a discussion for questions
- 👤 DM @kushin77 for direct assistance

---

**Last Updated:** 2026-01-29  
**Maintained by:** @kushin77
