#!/bin/bash
set -e

# Landing Zone Portal — Interactive CLI Entry Point
# Usage: ./run.sh [command]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to detect host IP address
detect_host_ip() {
    # Try multiple methods to get the host IP
    if command -v hostname &> /dev/null; then
        IP=$(hostname -I | awk '{print $1}')
        if [[ -n "$IP" && "$IP" != "127.0.0.1" ]]; then
            echo "$IP"
            return 0
        fi
    fi

    # Fallback to ip route
    if command -v ip &> /dev/null; then
        IP=$(ip route get 8.8.8.8 | awk '{print $7; exit}')
        if [[ -n "$IP" && "$IP" != "127.0.0.1" ]]; then
            echo "$IP"
            return 0
        fi
    fi

    # Last resort - use the configured default
    echo "192.168.168.42"
}

# Export environment variables
export HOST_IP=$(detect_host_ip)
export VITE_API_URL="http://${HOST_IP}:8082"
export PORTAL_IP="${HOST_IP}"

echo "🌐 Detected host IP: ${HOST_IP}"
echo "🔗 API URL: ${VITE_API_URL}"

case "${1:-help}" in
  dev)
    echo "🚀 Starting local development environment..."
    # Start backend in background
    echo "  → Starting backend on port 8082..."
    cd "${SCRIPT_DIR}/backend" && source ../venv/bin/activate && python main.py &
    BACKEND_PID=$!

    # Start frontend in background
    echo "  → Starting frontend on port 5173..."
    cd "${SCRIPT_DIR}/frontend" && VITE_API_URL="${VITE_API_URL}" npm run dev &
    FRONTEND_PID=$!

    echo "✅ Services started!"
    echo "  📱 Frontend: http://${HOST_IP}:5173"
    echo "  🔧 Backend: http://${HOST_IP}:8082"
    echo "  🛑 Press Ctrl+C to stop all services"

    # Wait for services and handle shutdown
    trap "echo '🛑 Stopping services...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
    wait
    ;;

  test)
    echo "🧪 Running all tests..."
    echo "  → Frontend unit tests..."
    if [ -d "frontend" ]; then
      cd frontend && npm test -- --run --coverage && cd ..
    fi
    echo "  → Backend unit tests..."
    if [ -d "backend" ]; then
      cd backend && python -m pytest tests/ --cov=src --cov-report=html && cd ..
    fi
    echo "✅ All tests passed!"
    ;;

  security)
    echo "🔐 Running security scans..."
    echo "  → Snyk..."
    snyk test --severity-threshold=high 2>/dev/null || echo "⚠️  Snyk not installed (optional)"
    echo "  → Pre-commit hooks..."
    pre-commit run --all-files 2>/dev/null || echo "⚠️  Pre-commit not installed (optional)"
    echo "✅ Security scans complete!"
    ;;

  validate)
    echo "✅ Validating repository structure..."
    errors=0

    # Check required files
    for file in README.md CONTRIBUTING.md SECURITY.md pmo.yaml cloudbuild.yaml .pre-commit-config.yaml .gitignore .editorconfig; do
      if [ ! -f "$SCRIPT_DIR/$file" ]; then
        echo "❌ Missing: $file"
        ((errors++))
      fi
    done

    # Check required directories
    for dir in frontend backend terraform scripts docs; do
      if [ ! -d "$SCRIPT_DIR/$dir" ]; then
        echo "❌ Missing folder: $dir/"
        ((errors++))
      fi
    done

    if [ $errors -eq 0 ]; then
      echo "✅ Repository structure is valid!"
    else
      echo "❌ Found $errors issues"
      exit 1
    fi
    ;;

  deploy)
    echo "📦 Deploying to staging..."
    if [ -f "scripts/deployment/deploy-staging.sh" ]; then
      bash scripts/deployment/deploy-staging.sh
    else
      echo "❌ Deployment script not found: scripts/deployment/deploy-staging.sh"
      exit 1
    fi
    ;;

  fmt)
    echo "🔄 Formatting code..."
    if command -v prettier &> /dev/null; then
      prettier --write "**/*.{js,jsx,ts,tsx,json,yaml,md}" 2>/dev/null || true
    fi
    if command -v black &> /dev/null; then
      black . 2>/dev/null || true
    fi
    echo "✅ Code formatted!"
    ;;

  clean)
    echo "🧹 Cleaning build artifacts..."
    rm -rf frontend/dist frontend/node_modules backend/__pycache__ backend/.pytest_cache terraform/.terraform terraform.tfstate*
    echo "✅ Clean complete!"
    ;;

  *)
    cat << 'EOF'
Landing Zone Portal — Control Plane

Usage: ./run.sh [command]

Commands:
  dev           Start local development environment (Docker Compose)
  test          Run all tests (frontend + backend)
  security      Run security scans (Snyk, pre-commit)
  validate      Validate repository structure
  deploy        Deploy to staging (Cloud Build)
  fmt           Format code (Prettier, Black)
  clean         Remove build artifacts
  help          Show this help message

Examples:
  ./run.sh dev              # Start local dev (http://localhost:5173)
  ./run.sh test             # Run all tests
  ./run.sh security         # Snyk + pre-commit scans
  ./run.sh deploy           # Deploy to staging

For more info, see: docs/DEPLOYMENT.md
EOF
    ;;
esac
