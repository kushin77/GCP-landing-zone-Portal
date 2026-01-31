# Frontend API Integration & Configuration

**Date**: January 31, 2026  
**Status**: Post-Phase 3 Configuration  
**Scope**: Frontend → Backend API connectivity

---

## Overview

The Landing Zone Portal frontend (React 18 + TypeScript + Vite) connects to the backend API via HTTP. This guide covers configuration, environment setup, and integration validation.

## Architecture

```
┌─────────────────┐
│  Frontend (React)  │  (http://localhost:5173)
│  Port: 5173        │
└────────┬──────────┘
         │
         │ HTTP/REST
         │ (Proxied in dev via Vite)
         │
┌────────▼──────────┐
│  Backend (FastAPI) │  (http://localhost:9000)
│  Port: 9000        │
└────────┬──────────┘
         │
         │ gRPC/REST
         │
┌────────▼──────────────┐
│  GCP Services          │
│ (BigQuery, Firestore)  │
└────────────────────────┘
```

## Environment Configuration

### Development Setup

```bash
# 1. Create .env file in project root
cp .env.example .env

# 2. Update for local development
cat > .env << EOF
# Environment
ENVIRONMENT=development

# Network Configuration
HOST_IP=localhost
PORTAL_PORT=5173
API_PORT=9000

# Frontend
VITE_API_URL=http://localhost:9000
VITE_PUBLIC_BASE_PATH=/

# GCP (optional for local dev)
GCP_PROJECT_ID=your-gcp-project

# Authentication
REQUIRE_AUTH=false
ALLOW_DEV_BYPASS=true

# Redis (local Docker)
REDIS_URL=redis://localhost:6379/0

# Logging
LOG_LEVEL=DEBUG

# Feature Flags
ENABLE_RCA_ANALYSIS=true
ENABLE_NOTIFICATIONS=true
ENABLE_CACHING=true
EOF

# 3. Run Docker Compose for backend + Redis
cd /home/akushnir/GCP-landing-zone-Portal
docker-compose up -d
```

### Production Setup

```bash
# 1. Set up environment on production server
export ENVIRONMENT=production
export HOST_IP=landing-zone-portal.example.com
export PORTAL_PORT=443
export API_PORT=8000
export GCP_PROJECT_ID=your-prod-gcp-project
export VITE_API_URL=https://landing-zone-portal.example.com/api
```

## Frontend Configuration Files

### 1. Vite Configuration (`frontend/vite.config.ts`)

The Vite configuration handles:
- **Development proxy** - Routes `/api/*` requests to backend
- **Base path** - Supports deployment under subdirectory (e.g., `/lz/`)
- **Build optimization** - Minification and chunk splitting

**Current config**:
```typescript
proxy: {
  '/api': {
    target: process.env.VITE_API_URL || 'http://192.168.168.42:8080',
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/api/, '/api'),
  },
}
```

**For custom backend host**, set environment variable:
```bash
export VITE_API_URL=http://your-backend-host:port
npm run dev
```

### 2. API Client (`frontend/src/services/api.ts`)

The API client provides:
- **Automatic retry** - Exponential backoff for failed requests
- **Error handling** - Structured error responses
- **Type safety** - TypeScript interfaces for all API methods
- **Request cancellation** - Abort controller support
- **Offline detection** - Network status monitoring

**Configuration**:
```typescript
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

const DEFAULT_RETRY_CONFIG = {
  maxRetries: 3,
  baseDelay: 1000,
  maxDelay: 10000,
  retryableStatuses: [408, 429, 500, 502, 503, 504],
};
```

### 3. Environment Variables

Required environment variables:

```bash
# Frontend API URL
VITE_API_URL=http://localhost:9000          # Dev
VITE_API_URL=https://api.example.com        # Prod

# Base path for deployment
VITE_PUBLIC_BASE_PATH=/                     # Root
VITE_PUBLIC_BASE_PATH=/lz/                  # Subpath

# GCP Configuration
VITE_GCP_PROJECT_ID=your-project-id
VITE_GCP_REGION=us-central1

# Feature flags
VITE_ENABLE_RCA_ANALYSIS=true
VITE_ENABLE_NOTIFICATIONS=true
VITE_ENABLE_CACHING=true
```

## Development Workflow

### 1. Start Backend Service

```bash
# Option A: Docker Compose (recommended)
cd /home/akushnir/GCP-landing-zone-Portal
docker-compose up -d
# Backend runs on http://localhost:9000

# Option B: Python Uvicorn directly
cd /home/akushnir/GCP-landing-zone-Portal/backend
source venv/bin/activate
uvicorn main:app --host 127.0.0.1 --port 9000 --reload
```

### 2. Start Frontend Development Server

```bash
cd /home/akushnir/GCP-landing-zone-Portal/frontend

# Install dependencies
npm install

# Start dev server with hot reload
VITE_API_URL=http://localhost:9000 npm run dev
# Frontend available at http://localhost:5173
```

### 3. Verify Connectivity

```bash
# Test backend health
curl -s http://localhost:9000/health | jq .

# Test frontend API call (from browser console)
fetch('http://localhost:9000/api/v1/projects')
  .then(r => r.json())
  .then(d => console.log(d))

# Or use the frontend UI
# Navigate to http://localhost:5173
# Open DevTools → Network tab
# Click on buttons to trigger API calls
# Verify requests show in Network tab
```

## API Integration Points

### Authentication

**Backend**: Validates Bearer tokens from Google Identity Platform  
**Frontend**: Sends token in `Authorization: Bearer <token>` header

```typescript
// frontend/src/services/api.ts
const authInterceptor = (config: any) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
};

axios.interceptors.request.use(authInterceptor);
```

### Request/Response Handling

**Request format**:
```typescript
// Example: Get projects list
GET /api/v1/projects?page=1&limit=10&sort=name

// Request headers
Authorization: Bearer <token>
Content-Type: application/json
```

**Response format**:
```json
{
  "data": [
    {
      "id": "project-1",
      "name": "Project Name",
      "status": "active",
      "created_at": "2026-01-31T12:00:00Z"
    }
  ],
  "total": 100,
  "page": 1,
  "limit": 10,
  "pages": 10
}
```

### Error Handling

**Backend error response**:
```json
{
  "error": true,
  "error_code": "VALIDATION_ERROR",
  "message": "Invalid request parameters",
  "request_id": "req-12345",
  "timestamp": "2026-01-31T12:00:00Z",
  "errors": [
    {
      "code": "REQUIRED_FIELD",
      "message": "Field 'name' is required",
      "field": "name"
    }
  ]
}
```

**Frontend handling**:
```typescript
// API client automatically handles errors
try {
  const response = await apiClient.get('/api/v1/projects');
  // Handle success
} catch (error: any) {
  if (error.response?.status === 401) {
    // Handle authentication error
  } else if (error.response?.status === 400) {
    // Handle validation error
    console.log(error.response.data.errors);
  } else {
    // Handle other errors
  }
}
```

## Building & Deployment

### Development Build

```bash
cd frontend
npm run dev
# Compiles with source maps
# Hot module replacement enabled
# Debug info included
```

### Production Build

```bash
cd frontend

# Build static files
VITE_API_URL=https://api.example.com npm run build
# Output: dist/ directory

# Preview production build locally
npm run preview

# Deploy to static hosting
# Copy dist/ to web server / CDN
```

### Docker Deployment

```bash
# Build Docker image
docker build -t landing-zone-portal-frontend:1.0.0 \
  --build-arg VITE_API_URL=https://api.example.com \
  -f frontend/Dockerfile .

# Run container
docker run -d \
  -p 5173:80 \
  --name lz-frontend \
  landing-zone-portal-frontend:1.0.0
```

### Nginx Configuration

```nginx
upstream backend {
    server localhost:9000;
}

server {
    listen 443 ssl http2;
    server_name landing-zone-portal.example.com;

    ssl_certificate /etc/letsencrypt/live/landing-zone-portal.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/landing-zone-portal.example.com/privkey.pem;

    # Static frontend files
    location / {
        root /var/www/landing-zone-portal/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API proxy
    location /api {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_redirect off;
    }

    # Prometheus metrics (internal only)
    location /metrics {
        proxy_pass http://backend:8001;
        allow 127.0.0.1;
        deny all;
    }

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css text/javascript application/json application/javascript;
    gzip_min_length 1000;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name landing-zone-portal.example.com;
    return 301 https://$server_name$request_uri;
}
```

## Testing Frontend-Backend Integration

### Unit Tests

```bash
# Frontend tests
cd frontend
npm test

# Backend tests
cd backend
python3 -m pytest tests/
```

### Integration Tests

```bash
# 1. Start services
docker-compose up -d

# 2. Run integration tests
cd frontend
npm run test:integration

# 3. Verify via Cypress
npm run test:e2e
```

### Manual Testing Checklist

- [ ] Backend health check: `curl http://localhost:9000/health`
- [ ] Frontend loads: `http://localhost:5173`
- [ ] API calls succeed: Check Network tab in DevTools
- [ ] Error handling: Test with invalid token
- [ ] Pagination: Test with page limit/offset parameters
- [ ] Sorting: Test with sort parameter
- [ ] Filtering: Test with filter parameters
- [ ] Rate limiting: Make 100+ requests, verify 429 response
- [ ] Authentication: Test with and without token
- [ ] CORS: Verify cross-origin requests work

## Troubleshooting

### Frontend Can't Connect to Backend

```bash
# Check if backend is running
curl -v http://localhost:9000/health

# Check CORS headers
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: GET" \
     -v http://localhost:9000/

# Check Vite proxy configuration
# In vite.config.ts, verify target URL matches running backend
```

### API Requests Timing Out

```bash
# Check backend logs
docker logs lz-backend
# or
sudo journalctl -u landing-zone-portal.service -f

# Check network connectivity
ping localhost:9000
# or
nc -zv localhost 9000

# Check firewall rules
sudo ufw show added
```

### CORS Errors

```bash
# Check backend CORS configuration
grep -r "CORS" backend/main.py backend/middleware/

# Verify allowed origins include frontend domain
# In backend, check:
CORS_ORIGINS=http://localhost:5173,https://example.com
```

### Build Size Issues

```bash
# Analyze bundle size
npm run build
npm run analyze

# Optimize chunks
# Check vite.config.ts build.rollupOptions
```

## Performance Optimization

### Frontend Optimization

```typescript
// Code splitting
const Projects = lazy(() => import('./pages/Projects'));

// Image optimization
import OptimizedImage from '@components/OptimizedImage';

// API caching via TanStack Query
const { data } = useQuery({
  queryKey: ['projects'],
  queryFn: () => apiClient.getProjects(),
  staleTime: 5 * 60 * 1000, // 5 minutes
});
```

### Network Optimization

```typescript
// Request compression
axios.defaults.headers.common['Accept-Encoding'] = 'gzip, deflate';

// Request batching
const batched = await Promise.all([
  apiClient.getProjects(),
  apiClient.getCompliance(),
  apiClient.getCosts(),
]);

// Lazy loading
<Suspense fallback={<Spinner />}>
  <Projects />
</Suspense>
```

## Related Documentation

- [PHASE_3_INFRASTRUCTURE_COMPLETION.md](../PHASE_3_INFRASTRUCTURE_COMPLETION.md)
- [docs/LOCAL_SETUP.md](./LOCAL_SETUP.md)
- [docs/ARCHITECTURE.md](./docs/architecture/ARCHITECTURE.md)
- [frontend/src/services/api.ts](../frontend/src/services/api.ts)
- [SYSTEMD_SERVICE_DEPLOYMENT.md](./SYSTEMD_SERVICE_DEPLOYMENT.md)

---

**Last Updated**: January 31, 2026  
**Status**: Production-Ready  
**Scope**: API Integration & Configuration
