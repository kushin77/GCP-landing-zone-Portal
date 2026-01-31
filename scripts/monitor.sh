#!/bin/bash
# Monitor GCP Landing Zone Portal services
# Provides real-time health status and logs

set -e

SERVICE_NAME="lz-portal"
COLORS_GREEN='\033[0;32m'
COLORS_RED='\033[0;31m'
COLORS_YELLOW='\033[1;33m'
COLORS_NC='\033[0m'

echo "🔍 GCP Landing Zone Portal - Service Monitor"
echo "=============================================="
echo ""

# Check if running via systemd
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo -e "${COLORS_GREEN}✅ Systemd Service Status:${COLORS_NC}"
    systemctl status "$SERVICE_NAME" --no-pager || true
    echo ""
fi

# Docker status
echo -e "${COLORS_GREEN}🐳 Docker Container Status:${COLORS_NC}"
docker ps --filter "name=lz-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""

# Health checks
echo -e "${COLORS_GREEN}🏥 Health Checks:${COLORS_NC}"

echo -n "Backend API:  "
if curl -s http://localhost:8080/health > /dev/null 2>&1; then
    echo -e "${COLORS_GREEN}✅ Healthy${COLORS_NC}"
else
    echo -e "${COLORS_RED}❌ Unhealthy${COLORS_NC}"
fi

echo -n "Frontend:     "
if curl -s http://localhost:5173 > /dev/null 2>&1; then
    echo -e "${COLORS_GREEN}✅ Healthy${COLORS_NC}"
else
    echo -e "${COLORS_RED}❌ Unhealthy${COLORS_NC}"
fi

echo -n "Redis Cache:  "
if docker exec lz-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${COLORS_GREEN}✅ Healthy${COLORS_NC}"
else
    echo -e "${COLORS_RED}❌ Unhealthy${COLORS_NC}"
fi

echo ""
echo -e "${COLORS_GREEN}📊 Access URLs:${COLORS_NC}"
echo "   Frontend:  http://192.168.168.42:5173"
echo "   Backend:   http://192.168.168.42:8080"
echo "   Analysis:  http://192.168.168.42:5173/analysis"
echo ""

echo -e "${COLORS_GREEN}📝 Recent Logs:${COLORS_NC}"
if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
    echo "Run: sudo journalctl -u $SERVICE_NAME -n 20 -f"
else
    echo "Run: docker-compose logs -f --tail=20"
fi
