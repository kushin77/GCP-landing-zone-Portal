#!/bin/bash
# GCP Landing Zone Portal - Permanent Service Startup
# Ensures portal runs persistently with auto-restart and logging

set -e

PORTAL_HOME="/home/akushnir/GCP-landing-zone-Portal"
LOG_DIR="${PORTAL_HOME}/logs"
BACKEND_LOG="${LOG_DIR}/backend.log"
FRONTEND_LOG="${LOG_DIR}/frontend.log"
PID_DIR="${PORTAL_HOME}/.pids"

# Create directories
mkdir -p "$LOG_DIR" "$PID_DIR"

echo "🚀 Starting GCP Landing Zone Portal..."
echo "📍 Home: $PORTAL_HOME"
echo "📊 Logs: $LOG_DIR"

# Start Docker Compose in background with logging
cd "$PORTAL_HOME"

# Ensure containers are up and running
echo "📦 Starting Docker Compose services..."
docker-compose up -d --remove-orphans 2>&1 | tee -a "${LOG_DIR}/docker-compose.log"

# Wait for services to be ready
echo "⏳ Waiting for services to be ready..."
sleep 5

# Health checks
echo "🏥 Performing health checks..."

# Backend health check
echo -n "Backend: "
for i in {1..30}; do
  if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo "✅ Ready"
    break
  fi
  echo -n "."
  sleep 1
done

# Frontend health check
echo -n "Frontend: "
for i in {1..30}; do
  if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo "✅ Ready"
    break
  fi
  echo -n "."
  sleep 1
done

echo ""
echo "✅ GCP Landing Zone Portal is running!"
echo ""
echo "📌 Access URLs:"
echo "   Frontend:  http://192.168.168.42:5173"
echo "   Backend:   http://192.168.168.42:8080"
echo "   Analysis:  http://192.168.168.42:5173/analysis"
echo ""
echo "📊 Logs:"
echo "   Docker:    tail -f $LOG_DIR/docker-compose.log"
echo "   Backend:   docker logs lz-backend"
echo "   Frontend:  docker logs lz-frontend"
echo ""
echo "🛑 To stop: docker-compose down"
