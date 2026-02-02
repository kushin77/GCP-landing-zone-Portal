# Systemd Service Deployment Guide

**Date**: January 31, 2026  
**Service**: GCP Landing Zone Portal Backend  
**Environment**: Production

---

## Overview

The Landing Zone Portal backend runs as a systemd service on production servers. This guide covers installation, configuration, operation, and troubleshooting.

## Prerequisites

- Ubuntu 20.04+ or equivalent Linux distribution
- Python 3.10+
- Redis server running (for rate limiting and caching)
- User account: `landing-zone` (create with `useradd`)
- Port 8000 available (or configured alternate port)

## Installation

### 1. Prepare System Dependencies

```bash
# Install Python and utilities
sudo apt-get update
sudo apt-get install -y python3.10 python3.10-venv python3-pip redis-server curl

# Install Google Cloud SDK (for service account credentials)
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init
```

### 2. Set Up Application Directory

```bash
# Create landing-zone user and group
sudo useradd -m -d /home/landing-zone-portal -s /bin/bash landing-zone

# Clone/copy application code
sudo mkdir -p /home/landing-zone-portal
sudo git clone <repo-url> /home/landing-zone-portal
# OR copy from existing deployment

# Set permissions
sudo chown -R landing-zone:landing-zone /home/landing-zone-portal
sudo chmod 755 /home/landing-zone-portal
```

### 3. Set Up Python Virtual Environment

```bash
cd /home/landing-zone-portal/backend

# Create virtual environment
python3.10 -m venv /home/landing-zone-portal/venv

# Activate and install dependencies
source /home/landing-zone-portal/venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

# Deactivate
deactivate
```

### 4. Configure Environment Variables

```bash
# Create production environment file
sudo vi /home/landing-zone-portal/backend/.env.production
```

Add these variables:
```bash
# Application
ENVIRONMENT=production
SERVICE_NAME=landing-zone-portal-backend
SERVICE_VERSION=1.0.0

# GCP Configuration
GCP_PROJECT_ID=your-gcp-project-id
GCP_REGION=us-central1

# Server
BIND_HOST=127.0.0.1
BIND_PORT=8000
BASE_PATH=/api

# Authentication
REQUIRE_AUTH=true
ALLOW_DEV_BYPASS=false

# Redis
REDIS_HOST=127.0.0.1
REDIS_PORT=6379

# Observability
LOG_LEVEL=INFO
ENABLE_METRICS=true
METRICS_PORT=8001

# Security
SECURE_HEADERS_ENABLED=true
CORS_ORIGINS=https://your-domain.com
```

Set permissions:
```bash
sudo chown landing-zone:landing-zone /home/landing-zone-portal/backend/.env.production
sudo chmod 600 /home/landing-zone-portal/backend/.env.production
```

### 5. Install Systemd Service

```bash
# Copy service file
sudo cp scripts/systemd/landing-zone-portal.service /etc/systemd/system/

# Update paths in service file if needed
sudo nano /etc/systemd/system/landing-zone-portal.service

# Enable service to start on boot
sudo systemctl daemon-reload
sudo systemctl enable landing-zone-portal.service
```

### 6. Create Logging Directory

```bash
sudo mkdir -p /home/landing-zone-portal/backend/logs
sudo chown landing-zone:landing-zone /home/landing-zone-portal/backend/logs
sudo chmod 755 /home/landing-zone-portal/backend/logs
```

## Operation

### Start Service

```bash
# Start the service
sudo systemctl start landing-zone-portal.service

# Verify it's running
sudo systemctl status landing-zone-portal.service

# Check logs
sudo journalctl -u landing-zone-portal.service -f
```

### Stop Service

```bash
sudo systemctl stop landing-zone-portal.service
```

### Restart Service

```bash
# Full restart
sudo systemctl restart landing-zone-portal.service

# Reload (without restarting - for config changes)
sudo systemctl reload landing-zone-portal.service
```

### View Logs

```bash
# Real-time logs
sudo journalctl -u landing-zone-portal.service -f

# Last 50 lines
sudo journalctl -u landing-zone-portal.service -n 50

# Since specific time
sudo journalctl -u landing-zone-portal.service --since "2026-01-31 10:00:00"

# Filter by level
sudo journalctl -u landing-zone-portal.service -p err
```

### Health Check

```bash
# Verify service is responding
curl -s http://127.0.0.1:8000/health | jq .

# Check metrics endpoint
curl -s http://127.0.0.1:8001/metrics | head -20
```

## Configuration

### Adjust Worker Count

For production, edit `/etc/systemd/system/landing-zone-portal.service`:

```bash
# Change workers parameter (default: 4)
# Formula: workers = (2 * CPU_cores) + 1
# Example for 4-core system: workers = 9

ExecStart=/usr/bin/python3 -m uvicorn \
    --workers 9 \
    ...
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart landing-zone-portal.service
```

### Update Memory Limit

```bash
# Current setting: 2GB
MemoryLimit=2G

# Adjust as needed (change in service file)
sudo nano /etc/systemd/system/landing-zone-portal.service

# Reload
sudo systemctl daemon-reload
sudo systemctl restart landing-zone-portal.service
```

### Change Port

**Service Port** (backend):
```bash
# Edit .env.production
BIND_PORT=8000

# Restart
sudo systemctl restart landing-zone-portal.service
```

**Metrics Port** (Prometheus):
```bash
# Edit .env.production
METRICS_PORT=8001

# Restart
sudo systemctl restart landing-zone-portal.service
```

## Monitoring & Maintenance

### Monitor Service Health

```bash
# Watch service status in real-time
watch -n 5 'sudo systemctl status landing-zone-portal.service'

# Check for errors
sudo journalctl -u landing-zone-portal.service -p err -n 20

# Count restarts
sudo systemctl show landing-zone-portal.service --property=NRestarts
```

### Performance Monitoring

```bash
# CPU and memory usage
ps aux | grep "landing-zone-portal"

# Network connections
sudo ss -tlnp | grep 8000

# Disk I/O
iostat -x 1

# System resources
htop
```

### Backup Configuration

```bash
# Backup environment file
sudo cp /home/landing-zone-portal/backend/.env.production \
        /home/landing-zone-portal/backend/.env.production.backup.$(date +%Y%m%d)

# Backup entire service directory
sudo tar -czf /backup/landing-zone-portal-$(date +%Y%m%d).tar.gz \
             /home/landing-zone-portal/backend
```

## Troubleshooting

### Service Fails to Start

```bash
# Check service status
sudo systemctl status landing-zone-portal.service

# View detailed error logs
sudo journalctl -u landing-zone-portal.service -n 100 -p err

# Check if port is in use
sudo lsof -i :8000

# Verify dependencies
redis-cli ping  # Should return PONG
python3 --version
```

### High Memory Usage

```bash
# Check current memory limit
sudo systemctl show landing-zone-portal.service --property=MemoryLimit

# Identify memory leaks
sudo journalctl -u landing-zone-portal.service -p warn

# Consider reducing workers
# or upgrading server resources
```

### Slow Response Times

```bash
# Check metrics endpoint
curl http://127.0.0.1:8001/metrics | grep http_

# View request logs
sudo journalctl -u landing-zone-portal.service -g "request"

# Check rate limiting
# Look for HTTP 429 responses
sudo journalctl -u landing-zone-portal.service | grep "429"
```

### Service Keeps Restarting

```bash
# Check restart policy violations
sudo journalctl -u landing-zone-portal.service -p err

# View recent restarts
sudo systemctl show landing-zone-portal.service --property=NRestarts,StateChangeTimestamp

# Review service dependencies
sudo systemctl show landing-zone-portal.service --property=Requires,After

# Verify Redis is running
sudo systemctl status redis-server
```

## Updates & Deployments

### Deploy New Version

```bash
# 1. Get new code
cd /home/landing-zone-portal
sudo git fetch
sudo git checkout <new-tag-or-branch>

# 2. Update dependencies (if needed)
source venv/bin/activate
pip install -r backend/requirements.txt
deactivate

# 3. Test (optional)
cd /home/landing-zone-portal/backend
python3 -m pytest

# 4. Restart service
sudo systemctl restart landing-zone-portal.service

# 5. Verify health
curl -s http://127.0.0.1:8000/health | jq .

# 6. Check logs for errors
sudo journalctl -u landing-zone-portal.service -n 20
```

### Rollback Version

```bash
# 1. Stop service
sudo systemctl stop landing-zone-portal.service

# 2. Checkout previous version
cd /home/landing-zone-portal
sudo git checkout <previous-tag>

# 3. Restart service
sudo systemctl start landing-zone-portal.service

# 4. Verify
curl -s http://127.0.0.1:8000/health | jq .
```

## Security Hardening

### File Permissions

```bash
# Verify correct permissions
ls -la /home/landing-zone-portal/backend/.env.production
# Should be: -rw------- 1 landing-zone landing-zone

# Verify service file permissions
ls -la /etc/systemd/system/landing-zone-portal.service
# Should be: -rw-r--r-- 1 root root
```

### Network Security

```bash
# Service only listens on localhost (127.0.0.1)
# Use nginx or HAProxy as reverse proxy for external access

# Verify listening port
sudo ss -tlnp | grep 8000
# Should show: 127.0.0.1:8000

# Enable firewall rules (if needed)
sudo ufw allow from 127.0.0.1 to 127.0.0.1 port 8000
```

### Service Account Setup

```bash
# Configure GCP service account
export GOOGLE_APPLICATION_CREDENTIALS=/home/landing-zone-portal/secrets/gcp-sa-key.json

# Verify credentials
gcloud auth application-default print-access-token
```

## Maintenance Schedule

| Task | Frequency | Command |
|------|-----------|---------|
| Check service health | Daily | `systemctl status landing-zone-portal.service` |
| Review error logs | Daily | `journalctl -u landing-zone-portal.service -p err -n 50` |
| Update dependencies | Monthly | `pip install --upgrade -r requirements.txt` |
| Backup configuration | Weekly | `tar -czf backup.tar.gz backend` |
| Full system test | Quarterly | `cd backend && pytest` |
| Security audit | Quarterly | Review logs and permissions |

## Related Documentation

- [PHASE_3_INFRASTRUCTURE_COMPLETION.md](../PHASE_3_INFRASTRUCTURE_COMPLETION.md) - Phase 3 completion report
- [DEPLOYMENT.md](../DEPLOYMENT.md) - Overall deployment guide
- [LOCAL_SETUP.md](../docs/LOCAL_SETUP.md) - Development environment
- [OPENTELEMETRY_STATUS.md](../docs/OPENTELEMETRY_STATUS.md) - Observability setup

---

**Last Updated**: January 31, 2026  
**Status**: Production-Ready  
**Tested On**: Ubuntu 20.04 LTS
