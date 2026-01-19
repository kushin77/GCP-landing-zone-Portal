# 🚀 Quick Start Guide

## Overview

This guide will get you up and running with the Landing Zone Portal in minutes.

## Prerequisites

- **Node.js** 20+ and npm
- **Python** 3.11+
- **GCP Project** with the following:
  - Billing enabled
  - BigQuery dataset for billing export
  - Appropriate IAM permissions

## Step 1: Clone the Repository

```bash
git clone https://github.com/kushin77/GCP-landing-zone-Portal.git
cd GCP-landing-zone-Portal
```

## Step 2: Set Up Backend

### Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### Configure Environment

Create a `.env` file in the `backend` directory:

```env
# GCP Configuration
GCP_PROJECT_ID=your-landing-zone-project
BILLING_DATASET=billing_export

# Application
SERVICE_NAME=Landing Zone Portal
SERVICE_VERSION=1.0.0
ENVIRONMENT=development

# Logging
LOG_LEVEL=INFO
```

### Set Up GCP Credentials

```bash
# Authenticate with your GCP account
gcloud auth application-default login

# Or use a service account
export GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account-key.json
```

### Run Backend

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8080

# Production mode
python main.py
```

Backend is now running at:
- **API**: http://localhost:8080
- **Docs**: http://localhost:8080/docs
- **ReDoc**: http://localhost:8080/redoc

## Step 3: Set Up Frontend

### Install Dependencies

```bash
cd ../frontend
npm install
```

### Configure Environment

Create a `.env.development` file (already created):

```env
VITE_API_URL=http://localhost:8080
```

### Run Frontend

```bash
npm run dev
```

Frontend is now running at: http://localhost:5173

## Step 4: Verify Installation

1. Open http://localhost:5173 in your browser
2. You should see the Landing Zone Portal dashboard
3. Navigate through different sections:
   - Dashboard
   - Projects
   - Costs
   - Compliance
   - Workflows
   - AI Assistant

## Architecture at a Glance

```
┌─────────────────────────────────────────┐
│  Browser (http://localhost:5173)       │
│  React App                              │
└──────────────┬──────────────────────────┘
               │ HTTP/REST
┌──────────────┴──────────────────────────┐
│  Backend API (http://localhost:8080)    │
│  FastAPI                                │
└──────────────┬──────────────────────────┘
               │ GCP APIs
┌──────────────┴──────────────────────────┐
│  Google Cloud Platform                  │
│  • BigQuery (costs)                     │
│  • Resource Manager (projects)          │
│  • Cloud Asset Inventory (resources)    │
│  • Cloud Monitoring (metrics)           │
└─────────────────────────────────────────┘
```

## Key Features

### 1. **Dashboard**
- Real-time cost overview
- Compliance score
- Resource counts
- Recent activity

### 2. **AI Assistant**
Try asking:
- "What are my biggest cost drivers?"
- "Show me compliance violations"
- "List all idle VMs"
- "How can I reduce costs?"

### 3. **Cost Management**
- Current month spending
- Cost breakdown by service
- AI-powered optimization recommendations
- Potential savings tracker

### 4. **Compliance**
- NIST 800-53 monitoring
- FedRAMP readiness
- Control status tracking
- Automated scanning

### 5. **Workflows**
- Self-service infrastructure requests
- Approval pipeline
- Terraform plan generation
- Audit trail

## API Endpoints

### Health
- `GET /health` - Health check
- `GET /ready` - Readiness check

### Dashboard
- `GET /api/v1/dashboard` - Main dashboard data

### Projects
- `GET /api/v1/projects` - List projects
- `GET /api/v1/projects/{id}` - Get project details
- `GET /api/v1/projects/{id}/costs` - Project costs

### Costs
- `GET /api/v1/costs/summary` - Cost summary
- `GET /api/v1/costs/breakdown` - Detailed breakdown
- `GET /api/v1/costs/optimizations` - AI recommendations

### Compliance
- `GET /api/v1/compliance/status` - Compliance status
- `GET /api/v1/compliance/frameworks` - Supported frameworks
- `POST /api/v1/compliance/scan` - Trigger scan

### Workflows
- `POST /api/v1/workflows/` - Create workflow
- `GET /api/v1/workflows/` - List workflows
- `POST /api/v1/workflows/{id}/approve` - Approve/reject
- `POST /api/v1/workflows/{id}/execute` - Execute

### AI Assistant
- `POST /api/v1/ai/query` - Query AI
- `GET /api/v1/ai/suggestions` - Get suggestions
- `GET /api/v1/ai/examples` - Example queries

## Development Tips

### Backend

```bash
# Run with auto-reload
uvicorn main:app --reload --log-level debug

# Run tests
pytest

# Format code
black .
```

### Frontend

```bash
# Development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Type check
npm run type-check

# Lint
npm run lint
```

## Troubleshooting

### Backend won't start
- Check Python version: `python --version` (should be 3.11+)
- Verify GCP credentials: `gcloud auth application-default login`
- Check environment variables in `.env`

### Frontend won't start
- Check Node version: `node --version` (should be 20+)
- Clear node_modules: `rm -rf node_modules && npm install`
- Check API URL in `.env.development`

### No data showing
- Ensure BigQuery billing export is configured
- Verify GCP project ID is correct
- Check backend logs for API errors

### Permission errors
- Ensure service account has required roles:
  - `roles/bigquery.dataViewer` (for cost data)
  - `roles/resourcemanager.organizationViewer` (for projects)
  - `roles/cloudasset.viewer` (for resources)

## Next Steps

1. **Configure BigQuery Billing Export**
   - Go to GCP Console → Billing → Billing export
   - Enable BigQuery export
   - Note the dataset name

2. **Set up Cloud Asset Inventory**
   - Enable Cloud Asset API
   - Grant necessary permissions

3. **Deploy to Production**
   - See [DEPLOYMENT.md](DEPLOYMENT.md) for production deployment

4. **Customize**
   - Add your organization's branding
   - Configure additional frameworks
   - Set up alerting

## Support

- **Documentation**: See all `.md` files in the repo
- **Issues**: Create a GitHub issue
- **Questions**: Contact the platform team

---

**You're all set! 🎉**

Start by exploring the Dashboard and asking the AI Assistant questions about your infrastructure.
