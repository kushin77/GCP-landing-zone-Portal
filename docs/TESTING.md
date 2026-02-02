# Testing Guide

This guide covers running tests, fixtures, and testing best practices for the GCP Landing Zone Portal.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Running Tests](#running-tests)
3. [Test Structure](#test-structure)
4. [Fixtures and Utilities](#fixtures-and-utilities)
5. [Coverage](#coverage)
6. [Best Practices](#best-practices)
7. [CI/CD Integration](#cicd-integration)

---

## Quick Start

### Run All Tests

```bash
cd backend
pytest
```

### Run Specific Test File

```bash
pytest tests/test_api.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=backend --cov-report=term-missing --cov-report=html
```

---

## Running Tests

### Basic Test Execution

```bash
cd backend

# Run all tests
pytest

# Run all tests in a directory
pytest tests/

# Run specific test file
pytest tests/test_api.py

# Run specific test function
pytest tests/test_api.py::test_get_projects

# Run tests matching pattern
pytest -k "test_auth" -v
```

### Test Options

| Option | Purpose | Example |
|--------|---------|---------|
| `-v, --verbose` | Verbose output | `pytest -v` |
| `-s` | Show print statements | `pytest -s` |
| `-x` | Stop on first failure | `pytest -x` |
| `-k EXPRESSION` | Filter by name | `pytest -k "auth"` |
| `-m MARKER` | Filter by marker | `pytest -m "unit"` |
| `--tb=short` | Short traceback | `pytest --tb=short` |
| `--pdb` | Drop to debugger on failure | `pytest --pdb` |
| `--lf` | Run last failed | `pytest --lf` |
| `--ff` | Run failed first | `pytest --ff` |

### Test Markers

Tests are marked with pytest markers for categorization:

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run both unit and integration
pytest -m "unit or integration"

# Skip slow tests
pytest -m "not slow"
```

### Available Markers

- `@pytest.mark.unit` — Unit tests
- `@pytest.mark.integration` — Integration tests
- `@pytest.mark.slow` — Slow-running tests
- `@pytest.mark.security` — Security-related tests
- `@pytest.mark.skip` — Skip test
- `@pytest.mark.skipif(condition)` — Conditional skip

---

## Test Structure

### Directory Layout

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py                 # Pytest configuration & fixtures
│   ├── test_api.py                 # API endpoint tests
│   ├── test_auth.py                # Authentication tests
│   ├── test_comprehensive.py       # Integration tests
│   ├── fixtures/
│   │   ├── __init__.py
│   │   ├── test_data.json
│   │   └── mock_responses.py
│   └── unit/
│       ├── test_models.py
│       └── test_services.py
├── pytest.ini                      # Pytest configuration
├── conftest.py                     # Root pytest configuration
└── requirements-dev.txt            # Development dependencies
```

### Test File Naming

- Test files: `test_*.py` or `*_test.py`
- Test functions: `test_*()`
- Test classes: `Test*()`

### Example Test

```python
import pytest
from app import create_app
from app.models import User

@pytest.mark.unit
def test_user_model():
    """Test User model creation."""
    user = User(username="testuser", email="test@example.com")
    assert user.username == "testuser"
    assert user.email == "test@example.com"

@pytest.mark.integration
def test_create_user_endpoint(client):
    """Test creating user via API."""
    response = client.post("/api/users", json={
        "username": "newuser",
        "email": "new@example.com"
    })
    assert response.status_code == 201
    assert response.json()["username"] == "newuser"
```

---

## Fixtures and Utilities

### Using Fixtures

Fixtures are reusable test components defined in `conftest.py`:

```python
@pytest.fixture
def client():
    """Provide test client."""
    app = create_app("testing")
    return app.test_client()

@pytest.fixture
def db(app):
    """Provide test database."""
    with app.app_context():
        db.create_all()
        yield db
        db.session.remove()
        db.drop_all()

@pytest.fixture
def user(db):
    """Provide test user."""
    user = User(username="testuser", email="test@example.com")
    db.session.add(user)
    db.session.commit()
    return user
```

### Using Fixtures in Tests

```python
def test_api_with_client(client):
    """Test using client fixture."""
    response = client.get("/api/projects")
    assert response.status_code == 200

def test_api_with_user(client, user):
    """Test using both client and user fixtures."""
    response = client.get(f"/api/users/{user.id}")
    assert response.status_code == 200
    assert response.json()["username"] == "testuser"

def test_database(db, user):
    """Test database fixture."""
    assert db.session.query(User).count() == 1
    assert db.session.query(User).first().username == "testuser"
```

### Available Fixtures

| Fixture | Purpose | Example Usage |
|---------|---------|----------------|
| `app` | Flask/FastAPI application | `def test_app(app): assert app.config["TESTING"]` |
| `client` | Test client | `def test_client(client): response = client.get("/")` |
| `db` | Database session | `def test_db(db): db.session.query(User)` |
| `user` | Test user | `def test_user(user): assert user.id` |
| `admin` | Admin user | `def test_admin(admin): assert admin.is_admin` |
| `mock_gcp` | Mock GCP client | `def test_gcp(mock_gcp): mock_gcp.list_projects()` |

### Mock Objects

```python
from unittest.mock import Mock, patch

# Create mock
mock_gcp = Mock()
mock_gcp.list_projects.return_value = [{"name": "test-project"}]

# Use in test
@patch("app.services.gcp_client.Client")
def test_list_projects(mock_client):
    mock_client.return_value.list_projects.return_value = [{"name": "test"}]
    result = list_projects()
    assert len(result) == 1
```

---

## Coverage

### Generate Coverage Report

```bash
cd backend

# Terminal report
pytest --cov=backend --cov-report=term-missing

# HTML report (generates htmlcov/ directory)
pytest --cov=backend --cov-report=html

# Open HTML report
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

### Coverage Configuration

**File:** `backend/pytest.ini`

```ini
[pytest]
addopts = --cov=backend --cov-report=term-missing --cov-report=html
testpaths = tests
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*
markers =
    unit: unit tests
    integration: integration tests
    slow: slow-running tests
    security: security-related tests
```

### Minimum Coverage

Current requirement: **80%+** code coverage

To check coverage:
```bash
pytest --cov=backend --cov-report=term-missing --cov-fail-under=80
```

---

## Best Practices

### 1. Test Independence

Tests should be independent and not rely on execution order:

```python
# ✅ Good: Test is self-contained
def test_create_user(db):
    user = User(username="test", email="test@example.com")
    db.session.add(user)
    db.session.commit()
    assert user.id is not None

# ❌ Bad: Test depends on previous test
user_id = None
def test_create_user(db):
    global user_id
    user = User(username="test", email="test@example.com")
    db.session.add(user)
    db.session.commit()
    user_id = user.id
```

### 2. Clear Test Names

Use descriptive test names:

```python
# ✅ Good
def test_create_user_with_valid_email():
    pass

def test_create_user_with_invalid_email_raises_error():
    pass

# ❌ Bad
def test_user():
    pass

def test_bad_email():
    pass
```

### 3. Arrange-Act-Assert Pattern

Structure tests clearly:

```python
def test_calculate_cost(client):
    # Arrange: Setup test data
    project = {"id": "test-project", "resources": 10}

    # Act: Perform action
    response = client.post("/api/cost", json=project)

    # Assert: Verify results
    assert response.status_code == 200
    assert response.json()["cost"] > 0
```

### 4. Parametrized Tests

Test multiple scenarios:

```python
import pytest

@pytest.mark.parametrize("email,expected", [
    ("valid@example.com", True),
    ("invalid-email", False),
    ("", False),
    ("test@.com", False),
])
def test_validate_email(email, expected):
    assert validate_email(email) == expected
```

### 5. Test Isolation

Use fixtures to isolate tests:

```python
# ✅ Good: Each test gets fresh database
@pytest.fixture(autouse=True)
def reset_db(db):
    yield
    db.session.rollback()

def test_one(db):
    db.session.add(User(username="user1"))
    db.session.commit()

def test_two(db):
    # Database is clean, no user1
    assert db.session.query(User).count() == 0
```

---

## CI/CD Integration

### CloudBuild Configuration

**File:** `cloudbuild.yaml`

```yaml
steps:
  # Install dependencies
  - name: 'gcr.io/cloud-builders/python'
    args: ['pip', 'install', '-r', 'backend/requirements.txt']
    env:
      - 'PYTHONPATH=/workspace'

  # Run tests
  - name: 'gcr.io/cloud-builders/python'
    args:
      - 'pytest'
      - 'backend/tests/'
      - '--cov=backend'
      - '--cov-report=term-missing'
      - '--cov-fail-under=80'
      - '-v'
    env:
      - 'PYTHONPATH=/workspace'

  # Generate coverage report
  - name: 'gcr.io/cloud-builders/python'
    args:
      - 'pytest'
      - 'backend/tests/'
      - '--cov=backend'
      - '--cov-report=html'
    env:
      - 'PYTHONPATH=/workspace'
```

### GitHub Actions Alternative

**File:** `.github/workflows/tests.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r backend/requirements.txt

      - name: Run tests
        run: |
          pytest backend/tests/ \
            --cov=backend \
            --cov-report=term-missing \
            --cov-fail-under=80 \
            -v

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

## Troubleshooting

### Common Issues

**Issue:** Tests pass locally but fail in CI
- **Solution:** Ensure all dependencies are installed: `pip install -r requirements.txt -r requirements-dev.txt`
- **Solution:** Check environment variables in CI

**Issue:** Flaky tests (passing/failing intermittently)
- **Solution:** Use `pytest-rerunfailures` plugin
- **Solution:** Check for timing issues, use `pytest.mark.slow` for slow tests
- **Solution:** Avoid shared state between tests

**Issue:** Database locked error
- **Solution:** Ensure database is cleaned up: `db.session.rollback()` in fixtures
- **Solution:** Use in-memory SQLite for tests

### Debug Tests

```bash
# Run with debugger
pytest --pdb

# Run with print output
pytest -s

# Run single test with verbose output
pytest -vv tests/test_api.py::test_specific_test

# Run with detailed traceback
pytest --tb=long
```

---

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Testing Best Practices](https://docs.pytest.org/en/stable/fixture.html)
- [FastAPI Testing](https://fastapi.tiangolo.com/advanced/testing-dependencies/)

---

**Last Updated:** 2026-01-29
**Minimum Coverage:** 80%
**Test Framework:** pytest 7.0+
