# Portal Deployment Guide

## Overview

This guide describes how to deploy the GCP Landing Zone Portal across all five infrastructure layers using Terraform. The portal follows a phased deployment strategy to manage dependencies and enable parallel development.

## Prerequisites

### Required Tools

```bash
# Verify installations
terraform -version          # >= 1.7.0
gcloud --version           # >= 400+
git --version              # >= 2.37+

# Install gcloud SDK if needed
curl https://sdk.cloud.google.com | bash
```

### GCP Setup

```bash
# Set project
export PROJECT_ID="your-gcp-project"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable \
  cloudresourcemanager.googleapis.com \
  compute.googleapis.com \
  container.googleapis.com \
  servicenetworking.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com
```

### Authentication

```bash
# Authenticate with GCP
gcloud auth login
gcloud auth application-default login

# Configure Terraform
export GOOGLE_PROJECT=$PROJECT_ID
export GOOGLE_REGION=us-central1
```

---

## 5-Layer Deployment Strategy

### Deployment Order

Layers must be deployed sequentially due to dependencies:

```
1️⃣  Foundation (01-foundation)
    ↓
2️⃣  Network (02-network)
    ↓
3️⃣  Security (03-security)
    ↓
4️⃣  Workloads (04-workloads)  ← Can run parallel with...
5️⃣  Observability (05-observability)
```

### Layer Dependencies

| Layer | Depends On | Provides |
|-------|-----------|----------|
| **01-Foundation** | None | Project, APIs, IAM base, CI/CD |
| **02-Network** | Foundation | VPC, Networking, Firewall |
| **03-Security** | Foundation, Network | IAM, Secrets, KMS, Compliance |
| **04-Workloads** | Foundation, Network, Security | Backend API, Frontend, Database |
| **05-Observability** | All previous | Logging, Monitoring, Alerting |

---

## Detailed Deployment Instructions

### Layer 1: Foundation (01-foundation)

**Purpose**: Bootstrap GCP organization, enable APIs, set up CI/CD

**Deployment Time**: ~15 minutes

#### Step 1: Initialize Terraform

```bash
cd terraform/01-foundation

# Initialize state backend
terraform init

# Review plan
terraform plan -out=tfplan.out

# View what will be created
terraform show tfplan.out
```

#### Step 2: Apply Configuration

```bash
# Apply changes
terraform apply tfplan.out

# Save outputs for next layer
terraform output -json > ../foundation-outputs.json

# Capture key values
PROJECT_ID=$(terraform output -raw project_id)
TERRAFORM_BUCKET=$(terraform output -raw terraform_state_bucket)
```

#### Verification

```bash
# Check Cloud Build pipeline
gcloud builds list --limit=5

# Verify service accounts created
gcloud iam service-accounts list

# Confirm APIs enabled
gcloud services list --enabled | grep -E "compute|container|build"
```

---

### Layer 2: Network (02-network)

**Purpose**: VPC, subnets, firewall, Cloud NAT

**Deployment Time**: ~20 minutes

#### Step 1: Prepare Inputs

```bash
cd terraform/02-network

# Reference foundation outputs
terraform init \
  -backend-config="bucket=$TERRAFORM_BUCKET" \
  -backend-config="prefix=02-network"

# Create terraform.tfvars from foundation outputs
cat > terraform.tfvars << EOF
project_id = "$(jq -r '.project_id.value' ../foundation-outputs.json)"
region = "us-central1"
environment = "prod"
EOF
```

#### Step 2: Plan & Apply

```bash
# Review plan
terraform plan -out=tfplan.out

# Apply
terraform apply tfplan.out

# Save outputs
terraform output -json > ../network-outputs.json
```

#### Network Configuration

**VPC Structure**:
```
GCP Project
└── prod-vpc (10.0.0.0/16)
    ├── prod-subnet-a (10.0.1.0/24) - us-central1-a
    ├── prod-subnet-b (10.0.2.0/24) - us-central1-b
    └── prod-subnet-c (10.0.3.0/24) - us-central1-c
```

**Firewall Rules**:
- Allow internal (10.0.0.0/8)
- Allow health checks (35.191.0.0/16)
- Block outbound except approved destinations

**Cloud NAT**:
- Outbound internet via Cloud NAT
- Auto IP allocation
- Log all connections

#### Verification

```bash
# Check VPC
gcloud compute networks list
gcloud compute networks describe prod-vpc

# Check subnets
gcloud compute networks subnets list --network=prod-vpc

# Check firewall
gcloud compute firewall-rules list --filter="network:prod-vpc"

# Test connectivity
gcloud compute instances create test-vm \
  --zone=us-central1-a \
  --network=prod-vpc \
  --subnet=prod-subnet-a

# Connect and test
gcloud compute ssh test-vm --zone=us-central1-a
ping 8.8.8.8  # Should work via Cloud NAT
```

---

### Layer 3: Security (03-security)

**Purpose**: IAM roles, secrets, KMS encryption, compliance policies

**Deployment Time**: ~25 minutes

#### Step 1: Setup IAM

```bash
cd terraform/03-security

terraform init \
  -backend-config="bucket=$TERRAFORM_BUCKET" \
  -backend-config="prefix=03-security"

# Create variables
cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
network_name = "prod-vpc"
environment = "prod"
EOF
```

#### Step 2: Apply Security Configuration

```bash
terraform plan -out=tfplan.out
terraform apply tfplan.out
terraform output -json > ../security-outputs.json
```

#### Security Components

**Service Accounts** (Least Privilege):
```
portal-backend@PROJECT.iam.gserviceaccount.com
  ├── roles/cloudsql.client (DB access)
  ├── roles/secretmanager.secretAccessor (Secrets)
  └── roles/storage.objectViewer (Cloud Storage)

portal-frontend@PROJECT.iam.gserviceaccount.com
  ├── roles/artifactregistry.reader (Image pull)
  └── roles/logging.logWriter (Logging)
```

**Secrets Created**:
- `db-password`: Cloud SQL root password
- `jwt-secret`: Backend JWT signing key
- `api-key`: Third-party API credentials

**KMS Keys**:
- `portal-kms-key`: Encryption key for sensitive data

#### Verification

```bash
# List service accounts
gcloud iam service-accounts list

# Check IAM bindings
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.role:roles/*"

# List secrets
gcloud secrets list

# Check KMS keys
gcloud kms keys list --location=us --keyring=portal-keyring
```

---

### Layer 4: Workloads (04-workloads)

**Purpose**: Deploy backend API, frontend SPA, database

**Deployment Time**: ~40 minutes

#### Step 1: Build Container Images

```bash
# Build backend image
cd backend
gcloud builds submit --tag=gcr.io/$PROJECT_ID/portal-backend:latest
cd ..

# Build frontend image
cd frontend
npm run build
gsutil -m cp -r dist/* gs://$PROJECT_ID-frontend/
cd ..
```

#### Step 2: Deploy Infrastructure

```bash
cd terraform/04-workloads

terraform init \
  -backend-config="bucket=$TERRAFORM_BUCKET" \
  -backend-config="prefix=04-workloads"

# Create variables
cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
region = "us-central1"
backend_image = "gcr.io/$PROJECT_ID/portal-backend:latest"
database_tier = "db-custom-2-8192"
environment = "prod"
EOF

# Plan and apply
terraform plan -out=tfplan.out
terraform apply tfplan.out
terraform output -json > ../workloads-outputs.json
```

#### Workload Configuration

**Backend (Cloud Run)**:
```
portal-backend Cloud Run Service
├── Memory: 2GB
├── CPU: 2 vCPU
├── Min instances: 1
├── Max instances: 10
├── Timeout: 60s
└── Environment Variables:
    ├── DB_HOST: cloudsql
    ├── DB_USER: postgres
    ├── DB_PASSWORD: (from Secret Manager)
    └── JWT_SECRET: (from Secret Manager)
```

**Frontend (Cloud Storage + CDN)**:
```
gs://PROJECT_ID-frontend/
├── index.html
├── static/
│   ├── js/
│   └── css/
└── assets/

Cloud CDN:
├── Cache: 3600s
├── Compress: gzip
└── Custom domain: portal.example.com
```

**Database (Cloud SQL)**:
```
portal-db (PostgreSQL 15)
├── Tier: db-custom-2-8192 (2 vCPU, 8GB)
├── Storage: 100GB
├── Backups: Daily, 30-day retention
├── High availability: Regional failover
└── Backups: Automated
```

#### Step 3: Run Database Migrations

```bash
# Connect to database
gcloud sql connect portal-db --user=postgres

# Run migrations
psql -h INSTANCE_IP -U postgres -d portal -f docs/db/migrations/001_init.sql

# Verify schema
psql -h INSTANCE_IP -U postgres -d portal -c "\dt"
```

#### Verification

```bash
# Check Cloud Run service
gcloud run services describe portal-backend --region=us-central1

# Test API
curl https://BACKEND_URL/api/v1/health

# Check database
gcloud sql instances describe portal-db

# Test frontend
curl https://portal.example.com/

# Check Cloud CDN
gcloud compute backend-buckets describe portal-frontend
```

---

### Layer 5: Observability (05-observability)

**Purpose**: Logging, monitoring, alerting, cost tracking

**Deployment Time**: ~20 minutes

#### Step 1: Setup Monitoring

```bash
cd terraform/05-observability

terraform init \
  -backend-config="bucket=$TERRAFORM_BUCKET" \
  -backend-config="prefix=05-observability"

# Variables
cat > terraform.tfvars << EOF
project_id = "$PROJECT_ID"
alert_email = "ops@example.com"
environment = "prod"
EOF

# Apply
terraform plan -out=tfplan.out
terraform apply tfplan.out
```

#### Observability Stack

**Cloud Logging**:
- Aggregates logs from all services
- Log sinks to BigQuery for analysis
- 30-day retention

**Cloud Monitoring**:
- Dashboards for key metrics
- Custom metrics from application
- SLO tracking

**Alert Policies**:
- Backend error rate > 1%
- API latency p95 > 500ms
- Database CPU > 80%
- Database disk > 80%

**Cost Tracking**:
- Daily cost reports to email
- Budget alerts at 80%, 100%
- Cost attribution by service

#### Verification

```bash
# List monitoring dashboards
gcloud monitoring dashboards list

# Create test alert
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="Test Alert"

# Check logs
gcloud logging read "resource.type=cloud_run_revision" --limit=10

# View metrics
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/request_count"'
```

---

## Post-Deployment Validation

## Public Endpoint and OAuth Protection (/lz)

The Landing Zone Portal is served under the public base path `/lz` and should be protected by your Load Balancer using OAuth via Google IAP.

### Application Configuration

```bash
# Backend (FastAPI) base path
export BASE_PATH=/lz

# IAP audience (example)
export IAP_AUDIENCE="/projects/${PROJECT_NUMBER}/global/backendServices/${BACKEND_SERVICE_ID}"
export REQUIRE_AUTH=true
export OAUTH_ALLOWED_DOMAINS=yourdomain.com
```

### Frontend Configuration (Production)

```bash
# Already set in frontend/.env.production
VITE_PUBLIC_BASE_PATH=/lz/
VITE_API_URL=https://elevatediq.ai/lz
```

### Load Balancer + IAP (Recommended)

- Use a GCP HTTPS Global Load Balancer in front of Cloud Run or GKE services.
- Enable IAP on the backend service to enforce OAuth at the edge.
- IAP forwards the JWT via `x-goog-iap-jwt-assertion`; the backend validates it automatically.
- Ensure the LB forwards `X-Forwarded-Prefix: /lz` so the app serves correctly under the base path.

### Routing Layout

- Public frontend: `https://elevatediq.ai/lz` → SPA assets
- Backend API: `https://elevatediq.ai/lz/api/*` → FastAPI (root_path=/lz)
- Health: `https://elevatediq.ai/lz/health`, `https://elevatediq.ai/lz/ready`

### Optional Nginx Reverse Proxy (non-GCP environments)

See `nginx/nginx.prod.conf` for an example that:
- Routes `/lz/api/*` to the backend service
- Serves `/lz/*` as the SPA
- Preserves forwarded headers and the IAP JWT header if present

### Verification

```bash
curl -I https://elevatediq.ai/lz/health
curl -I https://elevatediq.ai/lz/ready
# API docs (dev only): https://elevatediq.ai/lz/docs
```

### CI/CD Automation (Cloud Build)

- The pipeline in `cloudbuild.yaml` plans the `/lz` LB+IAP stack (terraform/04-workloads) using tfvars from Secret Manager.
- Secret required: `PORTAL_WORKLOADS_TFVARS` (store the tfvars content). It is injected as `TFVARS_WORKLOADS`.
- To automatically apply in CI, set substitution `_APPLY_WORKLOADS=true` on the build trigger. Default is plan-only.
- Ensure tfvars includes: project_id, region, domain, frontend_bucket, cloud_run_service_name, iap_client_id, iap_client_secret.

---

## Rollback Procedures

### Rollback Layer (if deployment fails)

```bash
cd terraform/LAYER_NUMBER

# View previous state
terraform state list

# Plan destruction
terraform plan -destroy -out=destroy.tfplan

# Destroy resources
terraform apply destroy.tfplan

# Fix Terraform code
# Then re-apply:
terraform apply -out=tfplan.out
terraform apply tfplan.out
```

### Rollback Application

```bash
# Get previous revision
PREV_REV=$(gcloud run services describe portal-backend \
  --region=us-central1 \
  --format='value(status.traffic[1].revision.name)')

# Switch traffic
gcloud run services update-traffic portal-backend \
  --to-revisions=$PREV_REV=100 \
  --region=us-central1
```

---

## CI/CD Integration

### Automated Deployment Pipeline

Cloud Build automatically deploys on push to main:

```yaml
# cloudbuild.yaml
steps:
  # 1. Validate Terraform
  - name: 'gcr.io/cloud-builders/terraform'
    args: ['validate']
    dir: 'terraform/01-foundation'

  # 2. Format check
  - name: 'gcr.io/cloud-builders/terraform'
    args: ['fmt', '-check', '-recursive', '.']
    dir: 'terraform'

  # 3. Build backend
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/portal-backend:$SHORT_SHA', 'backend']

  # 4. Deploy Terraform
  - name: 'gcr.io/cloud-builders/terraform'
    args: ['apply', '-auto-approve', '-out=tfplan']
    dir: 'terraform/01-foundation'

  # 5. Deploy backend
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args: ['run', '--filename=k8s/', '--location=us-central1']
```

---

## Environment-Specific Configuration

### Development

```hcl
environment = "dev"
db_tier = "db-f1-micro"
min_instances = 0
max_instances = 1
```

### Staging

```hcl
environment = "staging"
db_tier = "db-custom-1-4096"
min_instances = 1
max_instances = 5
```

### Production

```hcl
environment = "prod"
db_tier = "db-custom-4-16384"
min_instances = 2
max_instances = 10
```

---

## Troubleshooting

### Terraform State Lock

```bash
# If deployment hangs
gcloud storage objects list gs://$TERRAFORM_BUCKET

# Force unlock (use with caution)
terraform force-unlock LOCK_ID
```

### Cloud Build Failures

```bash
# View build logs
gcloud builds log BUILD_ID --stream

# Re-run build
gcloud builds submit
```

### Deployment Verification

```bash
# Comprehensive check
./scripts/deployment/verify-deployment.sh

# Manual checks
gcloud run services describe portal-backend
gcloud sql instances describe portal-db
gcloud storage buckets describe gs://$PROJECT_ID-frontend/
```

---

## References

- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [RUNBOOKS.md](RUNBOOKS.md) - Incident response
- [Terraform Registry - Google Cloud](https://registry.terraform.io/providers/hashicorp/google)
- [GCP Deployment Manager Best Practices](https://cloud.google.com/docs/terraform/best-practices)

---

**Version**: 1.0  
**Last Updated**: 2026-01-19  
**Owner**: Platform Engineering Team
