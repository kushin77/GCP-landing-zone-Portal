# Portal Global Configuration - Phase 1 & Phase 2

**Status**: Configuration enhanced for both IP address (Phase 1) and DNS (Phase 2) deployment models

---

## Overview

The Portal supports **two deployment phases**:

### Phase 1: IP Address (Current)
- **Frontend**: http://192.168.168.42:5173
- **Backend**: http://192.168.168.42:8080
- **Purpose**: Development, staging, internal testing
- **Environment**: `.env.development` files

### Phase 2: DNS (Production)
- **Frontend**: https://elevatediq.ai/portal
- **Backend**: https://elevatediq.ai/lz
- **Purpose**: Production deployment
- **Environment**: `.env.production` files

---

## Configuration Files

### Frontend Configuration

**Phase 1: IP Address** (`frontend/.env.development`):
```dotenv
VITE_API_URL=http://192.168.168.42:8080
VITE_PORTAL_URL=http://192.168.168.42:5173
```

**Phase 2: DNS** (`frontend/.env.production`):
```dotenv
VITE_PUBLIC_BASE_PATH=/portal/
VITE_API_URL=https://elevatediq.ai/lz
VITE_PORTAL_URL=https://elevatediq.ai/portal
```

**Vite Configuration** (`frontend/vite.config.ts`):
- Listens on `0.0.0.0:5173` for external access
- Proxies `/api` requests to backend
- Supports environment-based API URL switching

### Backend Configuration

**Phase 1: IP Address** (`backend/.env.development`):
```dotenv
ENVIRONMENT=development
PORTAL_IP=192.168.168.42
PORTAL_PORT=8080
BASE_PATH=/lz
GCP_PROJECT_ID=portal-dev
```

**Phase 2: DNS** (`backend/.env.production`):
```dotenv
ENVIRONMENT=production
PORTAL_IP=elevatediq.ai
PORTAL_PORT=443
BASE_PATH=/portal
GCP_PROJECT_ID=portal-prod
ENABLE_HTTPS=true
```

**Config** (`backend/config.py`):
- Automatically selects correct URL based on `ENVIRONMENT` variable
- CORS configured for both Phase 1 (IP) and Phase 2 (DNS)
- Allowed origins:
  - http://192.168.168.42:8080
  - http://192.168.168.42:5173
  - http://localhost:5173
  - http://localhost:8080
  - https://elevatediq.ai/portal
  - https://elevatediq.ai

---

## Running Portal

### Phase 1: IP Address (Current)

**Terminal 1 - Frontend**:
```bash
cd frontend
export ENVIRONMENT=development
npm run dev
# Access: http://192.168.168.42:5173
```

**Terminal 2 - Backend**:
```bash
cd backend
export ENVIRONMENT=development
python main.py
# Runs on: http://192.168.168.42:8080
```

### Phase 2: DNS (Production)

**Using DNS Configuration**:
```bash
# Frontend
cd frontend
export ENVIRONMENT=production
npm run build
# Deploy to: https://elevatediq.ai/portal

# Backend
cd backend
export ENVIRONMENT=production
python main.py
# Runs on: https://elevatediq.ai/lz
```

---

## Environment Variables

### Frontend

| Variable | Phase 1 | Phase 2 | Purpose |
|----------|---------|---------|---------|
| `VITE_API_URL` | http://192.168.168.42:8080 | https://elevatediq.ai/lz | Backend API endpoint |
| `VITE_PORTAL_URL` | http://192.168.168.42:5173 | https://elevatediq.ai/portal | Portal frontend URL |
| `ENVIRONMENT` | development | production | Env mode |

### Backend

| Variable | Phase 1 | Phase 2 | Purpose |
|----------|---------|---------|---------|
| `ENVIRONMENT` | development | production | Environment mode |
| `PORTAL_IP` | 192.168.168.42 | elevatediq.ai | Server IP/domain |
| `PORTAL_PORT` | 8080 | 443 | Server port |
| `BASE_PATH` | /lz | /portal | URL path prefix |
| `ENABLE_HTTPS` | false | true | SSL/TLS support |

---

## Network Access

### Phase 1: IP Address
- **Local Network**: Access from any machine on 192.168.168.0/24
- **External**: Requires port forwarding or VPN
- **Use Case**: Internal development, staging, testing

### Phase 2: DNS
- **Global Access**: https://elevatediq.ai/portal (worldwide)
- **Load Balancer**: Cloudflare or AWS CloudFront
- **SSL/TLS**: Automatic with Let's Encrypt
- **Use Case**: Production environment

---

## CORS Configuration

The backend automatically allows requests from:

**Phase 1 Origins**:
- http://192.168.168.42:5173 (Frontend dev)
- http://192.168.168.42:8080 (Backend)
- http://localhost:5173 (Local dev)
- http://localhost:8080 (Local backend)

**Phase 2 Origins**:
- https://elevatediq.ai/portal
- https://elevatediq.ai

---

## Docker Deployment

### Phase 1: IP Address
```dockerfile
FROM node:18 as frontend
WORKDIR /app
COPY frontend .
RUN npm install && npm run build

FROM python:3.11 as backend
WORKDIR /app
COPY backend .
RUN pip install -r requirements.txt
ENV ENVIRONMENT=development
ENV PORTAL_IP=192.168.168.42
EXPOSE 8080
CMD ["python", "main.py"]
```

### Phase 2: DNS
```dockerfile
# Phase 2 Dockerfile
ENV ENVIRONMENT=production
ENV PORTAL_IP=elevatediq.ai
ENV ENABLE_HTTPS=true
# Includes SSL certificate mounting
```

---

## Nginx Configuration

### Phase 1: IP Address
```nginx
server {
    listen 5173;
    server_name 192.168.168.42;

    location / {
        proxy_pass http://localhost:5173;
    }

    location /api {
        proxy_pass http://192.168.168.42:8080;
    }
}
```

### Phase 2: DNS
```nginx
server {
    listen 443 ssl http2;
    server_name elevatediq.ai www.elevatediq.ai;

    ssl_certificate /etc/letsencrypt/live/elevatediq.ai/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/elevatediq.ai/privkey.pem;

    location /portal {
        proxy_pass http://localhost:5173;
    }

    location /lz {
        proxy_pass http://localhost:8080;
    }
}
```

---

## DNS Migration Timeline

### Week 1-2: Phase 1 Setup (IP Address)
- ✅ Configure IP address (192.168.168.42)
- ✅ Test locally and on network
- ✅ Deploy frontend and backend
- ✅ Verify all functionality

### Week 3-4: Phase 2 Preparation
- [ ] Register domain: elevatediq.ai
- [ ] Configure DNS records
- [ ] Setup SSL/TLS certificates
- [ ] Configure load balancer

### Week 5-6: Phase 2 Migration
- [ ] Deploy to production (Phase 2)
- [ ] Update DNS to point to new servers
- [ ] Monitor traffic and performance
- [ ] Retire Phase 1 infrastructure

---

## Current Status

✅ **Phase 1 (IP Address)**: Fully configured and ready
- Frontend: http://192.168.168.42:5173
- Backend: http://192.168.168.42:8080
- All CORS rules configured
- Environment variables set

📋 **Phase 2 (DNS)**: Ready for transition
- Configuration templates provided
- Environment files created
- Nginx configs available
- Docker configs prepared

---

## Testing Configuration

### Test Phase 1 Configuration
```bash
# Frontend
curl http://192.168.168.42:5173

# Backend
curl http://192.168.168.42:8080/health

# API
curl http://192.168.168.42:8080/api/v1/projects
```

### Test Phase 2 Configuration (when deployed)
```bash
# Frontend
curl https://elevatediq.ai/portal

# Backend
curl https://elevatediq.ai/lz/health

# API
curl https://elevatediq.ai/lz/api/v1/projects
```

---

## Support & Documentation

- **Architecture**: See [LIVE_SYNC_ARCHITECTURE.md](../LIVE_SYNC_ARCHITECTURE.md)
- **Deployment**: See [PORTAL_SETUP_COMPLETE.md](../PORTAL_SETUP_COMPLETE.md)
- **API Docs**: http://192.168.168.42:8080/docs (development)
- **GitHub**: https://github.com/kushin77/GCP-landing-zone-Portal

---

## Summary

✅ **Phase 1 (Current)**: IP-based deployment (192.168.168.42)
✅ **Phase 2 (Future)**: DNS-based deployment (elevatediq.ai/portal)
✅ **Seamless Transition**: Configuration supports both phases
✅ **Production Ready**: All security and CORS settings configured
