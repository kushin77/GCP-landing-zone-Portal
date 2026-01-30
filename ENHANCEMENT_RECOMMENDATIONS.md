# GCP Landing Zone Portal - Enhancement Recommendations

**Date**: 2026-01-19
**Category**: Strategic Improvements for Scale, Security, and Operations
**Priority**: High-Impact Enhancements for Enterprise Readiness

---

## Executive Summary

This document outlines strategic enhancements to maximize the Portal's value as an enterprise landing zone. These recommendations build on the solid 5-layer foundation and focus on:

1. **Advanced Security** - Zero-trust, compliance automation
2. **Cost Optimization** - FinOps integration, allocation tracking
3. **Developer Experience** - Faster onboarding, self-service
4. **Operational Excellence** - Enhanced observability, SLOs
5. **Scalability** - Multi-region, high-availability patterns

---

## Category 1: Advanced Security Enhancements

### 1.1 Zero-Trust Network Architecture

**Current State**: Basic VPC firewall rules (foundation)
**Enhancement**: Implement VPC Service Controls + Binary Authorization

```hcl
# terraform/03-security/network-perimeter.tf (NEW)

resource "google_access_context_manager_access_policy" "policy" {
  parent = "organizations/${var.org_id}"
  title  = "Portal Zero-Trust Policy"
}

resource "google_access_context_manager_service_perimeter" "perimeter" {
  parent         = google_access_context_manager_access_policy.policy.name
  name           = "accessPolicies/${google_access_context_manager_access_policy.policy.name}/servicePerimeters/portal"
  title          = "Portal Service Perimeter"

  status {
    resources = [
      "projects/${var.project_id}"
    ]
    restricted_services = [
      "storage.googleapis.com",
      "compute.googleapis.com",
      "container.googleapis.com"
    ]
  }
}

# Enforce container image signing
resource "google_binary_authorization_policy" "policy" {
  project = var.project_id

  admission_whitelist_patterns {
    name_pattern = "gcr.io/${var.project_id}/*"
  }

  default_admission_rule {
    require_attestations_by = [google_container_analysis_note.portal.name]
    enforcement_mode        = "ENFORCED_BLOCK_AND_AUDIT_LOG"
  }

  kubernetes_namespace_admissions {
    name_pattern = "prod-*"
    mode         = "ALWAYS"
  }
}
```

**Benefits**:
- Prevent unauthorized workloads from running
- Control data egress with service perimeters
- Compliance with FedRAMP AC-3, AC-4

**Effort**: 2-3 weeks | **ROI**: Critical for regulated workloads

---

### 1.2 Secrets Rotation Automation

**Current State**: Manual Secret Manager management
**Enhancement**: Automated rotation with audit trail

```python
# scripts/security/secret-rotation.py (NEW)

import functions_framework
from google.cloud import secretmanager
from google.cloud import logging as cloud_logging
from datetime import datetime, timedelta

@functions_framework.http
def rotate_secrets(request):
    """Rotate secrets based on rotation policy"""
    client = secretmanager.SecretManagerServiceClient()
    logger = cloud_logging.Client().logger("secret-rotation")

    secrets_to_rotate = [
        ("db-password", 30),  # Rotate every 30 days
        ("api-key", 90),
        ("jwt-secret", 365),
    ]

    for secret_id, max_age_days in secrets_to_rotate:
        secret_path = f"projects/{project_id}/secrets/{secret_id}"

        # Get current version creation time
        response = client.get_secret(request={"name": secret_path})
        created = response.created_at
        age_days = (datetime.utcnow() - created).days

        if age_days > max_age_days:
            # Trigger rotation (implementation depends on secret type)
            logger.log_struct({
                "severity": "INFO",
                "message": f"Rotating {secret_id}",
                "age_days": age_days,
                "max_age_days": max_age_days,
                "timestamp": datetime.utcnow().isoformat()
            })
            # Call rotation handler (database-specific, etc.)
            rotate_secret(secret_id)

    return {"status": "rotation_complete"}
```

**Benefits**:
- Reduced risk of credential compromise
- Compliance with NIST AC-2, IA-4
- Audit trail for all rotations

**Effort**: 1-2 weeks | **ROI**: Essential for SOC 2 Type II

---

### 1.3 Policy-as-Code Enforcement

**Current State**: Static organization policies
**Enhancement**: Dynamic policy evaluation with Sentinel/OPA

```rego
# terraform/03-security/policies/gcp-policies.rego (NEW - OPA/Conftest)

package main

deny[msg] {
    input.resource_type == "compute.Instance"
    input.service_account == "default"
    msg := "Instances must not use default service account"
}

deny[msg] {
    input.resource_type == "storage.Bucket"
    input.encryption.algorithm != "AES256"
    msg := "Buckets must use AES256 encryption"
}

deny[msg] {
    input.resource_type == "sql.Instance"
    not input.ssl_require
    msg := "Cloud SQL instances must require SSL"
}

deny[msg] {
    input.resource_type == "compute.Firewall"
    input.direction == "INGRESS"
    input.source_ranges[_] == "0.0.0.0/0"
    input.allowed[_].protocol != "tcp"
    msg := "Ingress from 0.0.0.0/0 only allowed for TCP"
}
```

**Benefits**:
- Shift-left security (catch violations before deployment)
- Consistent policy enforcement across all layers
- Compliance automation

**Effort**: 2-3 weeks | **ROI**: Prevents 70% of common misconfigurations

---

## Category 2: Cost Optimization Enhancements

### 2.1 Detailed Cost Attribution & Chargeback

**Current State**: Basic cost tracking in 05-observability
**Enhancement**: Granular cost allocation to teams/projects

```hcl
# terraform/05-observability/cost-tracking.tf (ENHANCED)

# Enable BigQuery export of billing data
resource "google_billing_account_iam_member" "bq_agent" {
  billing_account_id = var.billing_account_id
  role               = "roles/billing.projectManager"
  member             = "serviceAccount:${google_bigquery_dataset_iam_member.bq.service_account}"
}

# Create cost analysis views
resource "google_bigquery_table" "cost_attribution" {
  project     = var.project_id
  dataset_id  = google_bigquery_dataset.costs.dataset_id
  table_id    = "cost_attribution"
  description = "Cost allocation by team and service"

  schema = jsonencode([
    {
      name        = "date"
      type        = "DATE"
      mode        = "REQUIRED"
      description = "Billing period date"
    },
    {
      name        = "team"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "Team from labels"
    },
    {
      name        = "service"
      type        = "STRING"
      mode        = "REQUIRED"
      description = "GCP service (compute, storage, etc.)"
    },
    {
      name        = "cost_usd"
      type        = "NUMERIC"
      mode        = "REQUIRED"
      description = "Cost in USD"
    },
    {
      name        = "project_id"
      type        = "STRING"
      mode        = "NULLABLE"
      description = "GCP project ID"
    }
  ])
}

# Create dashboard for cost visibility
resource "google_monitoring_dashboard" "cost_dashboard" {
  dashboard_json = jsonencode({
    displayName = "Cost Allocation by Team"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "billing.googleapis.com/month_to_date_cost | metric.service_description=~'Cloud SQL|Compute Engine|Cloud Storage'"
                }
              }
            }]
          }
        }
      ]
    }
  })
}
```

**Benefits**:
- **Chargeback**: Accurate cost allocation to teams
- **Optimization**: Identify expensive services
- **Budgeting**: Data-driven capacity planning

**Effort**: 2-3 weeks | **ROI**: 10-20% cost reduction through visibility

---

### 2.2 Commitment-Based Discounts Automation

**Current State**: Manual RIs/CUDs management
**Enhancement**: Automated analysis and purchasing recommendations

```python
# scripts/cost-optimization/commitment-analyzer.py (NEW)

import pandas as pd
from google.cloud import billing_v1
from google.cloud import bigquery

def analyze_commitments(project_id, lookback_days=90):
    """Analyze usage patterns and recommend commitments"""

    bq = bigquery.Client()

    # Query usage patterns
    query = f"""
    SELECT
      service.description as service,
      resource.labels.region as region,
      SUM(usage.amount) as total_usage,
      SUM(cost) as total_cost,
      COUNT(DISTINCT DATE(usage_start_time)) as days_used
    FROM `{project_id}.billing.gcp_billing_export_v1`
    WHERE usage_start_time >= TIMESTAMP(DATE_SUB(CURRENT_DATE(), INTERVAL {lookback_days} DAY))
      AND service.description IN ('Compute Engine', 'Cloud SQL', 'Cloud Storage')
    GROUP BY 1, 2
    ORDER BY total_cost DESC
    """

    df = bq.query(query).to_dataframe()

    # Recommend commitments
    recommendations = []
    for _, row in df.iterrows():
        if row['days_used'] > lookback_days * 0.8:  # 80%+ utilization
            annual_cost = row['total_cost'] * 365 / lookback_days
            discount = 0.25 if row['service'] == 'Compute Engine' else 0.20
            savings = annual_cost * discount

            recommendations.append({
                'service': row['service'],
                'region': row['region'],
                'annual_cost': annual_cost,
                'potential_savings': savings,
                'discount_percent': discount * 100,
                'confidence': 'high' if row['days_used'] == lookback_days else 'medium'
            })

    return pd.DataFrame(recommendations).sort_values('potential_savings', ascending=False)

# Generate report
if __name__ == "__main__":
    report = analyze_commitments(project_id)
    print(report.to_string())
    # Send to finance team
    send_email_report(report)
```

**Benefits**:
- **Savings**: 25-30% discount on committed resources
- **Automation**: Remove manual analysis
- **Forecasting**: Accurate budget projections

**Effort**: 1-2 weeks | **ROI**: 20-30% cost reduction on compute/storage

---

## Category 3: Developer Experience Enhancements

### 3.1 Self-Service Infrastructure Templates

**Current State**: Manual Terraform layer setup
**Enhancement**: Guided templates via service catalog

```hcl
# terraform/modules/templates/gke-cluster.tf (NEW)

# Reusable, opinionated GKE cluster template
variable "cluster_config" {
  description = "GKE cluster configuration"
  type = object({
    name              = string
    region            = string
    node_count        = number
    machine_type      = string
    enable_gce_pd     = bool
    enable_binary_auth = bool
  })
}

resource "google_container_cluster" "cluster" {
  name     = var.cluster_config.name
  location = var.cluster_config.region

  # Sensible defaults for security
  initial_node_count       = var.cluster_config.node_count
  remove_default_node_pool = true

  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.subnet.name

  # Network policy for zero-trust
  network_policy {
    enabled  = true
    provider = "PROVIDER_UNSPECIFIED"
  }

  # Workload identity for Pod-to-GCP auth
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Binary authorization enforcement
  binary_authorization {
    evaluation_mode = var.cluster_config.enable_binary_auth ? "PROJECT_SINGLETON_POLICY_ENFORCE" : "DISABLED"
  }

  # Security defaults
  master_auth {
    client_certificate_config {
      issue_client_certificate = false
    }
  }

  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }
}

# Node pool with auto-scaling
resource "google_container_node_pool" "primary" {
  name       = "${var.cluster_config.name}-primary"
  cluster    = google_container_cluster.cluster.name
  location   = var.cluster_config.region
  node_count = var.cluster_config.node_count

  autoscaling {
    min_node_count = 1
    max_node_count = 10
  }

  node_config {
    machine_type = var.cluster_config.machine_type

    # Security hardening
    service_account = google_service_account.gke_nodes.email
    oauth_scopes = [
      "https://www.googleapis.com/auth/cloud-platform"
    ]

    # Use preemptible for cost savings
    preemptible = true

    # Security patches
    metadata = {
      disable-legacy-endpoints = "true"
    }

    labels = {
      managed_by = "terraform"
      tier       = "primary"
    }
  }
}

output "cluster_endpoint" {
  value = google_container_cluster.cluster.endpoint
}
```

**Usage Example**:
```hcl
# In your project's main.tf
module "gke_cluster" {
  source = "../../modules/templates/gke-cluster"

  cluster_config = {
    name               = "prod-api-cluster"
    region             = "us-central1"
    node_count         = 3
    machine_type       = "n2-standard-4"
    enable_gce_pd      = true
    enable_binary_auth = true
  }

  project_id = var.project_id
}
```

**Benefits**:
- **Speed**: Deploy infrastructure in hours, not days
- **Consistency**: Enforce security by default
- **Learning**: Embedded best practices

**Effort**: 2-3 weeks | **ROI**: 50% reduction in onboarding time

---

### 3.2 Interactive Onboarding CLI Tool

**Current State**: Manual documentation following
**Enhancement**: Interactive CLI guide with validation

```bash
#!/bin/bash
# scripts/bootstrap/portal-setup-interactive.sh (NEW)

set -euo pipefail

# Color codes
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}╔════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   GCP Landing Zone Portal Setup Tool   ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Collect inputs
echo -e "${YELLOW}Step 1: Project Configuration${NC}"
read -p "Enter GCP Project ID: " PROJECT_ID
read -p "Enter Organization ID: " ORG_ID
read -p "Enter Billing Account ID: " BILLING_ID
read -p "Enter Deployment Environment (dev/staging/prod): " ENVIRONMENT

# Validate inputs
validate_project() {
    if gcloud projects describe $PROJECT_ID >/dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} Project $PROJECT_ID found"
    else
        echo -e "${RED}✗${NC} Project $PROJECT_ID not found"
        exit 1
    fi
}

validate_project

# Step 2: Enable APIs
echo -e "\n${YELLOW}Step 2: Enabling Required APIs${NC}"
apis=(
    "cloudresourcemanager.googleapis.com"
    "compute.googleapis.com"
    "container.googleapis.com"
    "sqladmin.googleapis.com"
    "cloudbuild.googleapis.com"
    "artifactregistry.googleapis.com"
)

for api in "${apis[@]}"; do
    echo "Enabling $api..."
    gcloud services enable $api --project=$PROJECT_ID
done

echo -e "${GREEN}✓${NC} All APIs enabled"

# Step 3: Configure Terraform
echo -e "\n${YELLOW}Step 3: Preparing Terraform${NC}"

cat > terraform/terraform.tfvars << EOF
project_id           = "$PROJECT_ID"
organization_id      = "$ORG_ID"
billing_account_id   = "$BILLING_ID"
environment          = "$ENVIRONMENT"
region              = "us-central1"
EOF

echo -e "${GREEN}✓${NC} terraform.tfvars created"

# Step 4: Initialize Terraform
echo -e "\n${YELLOW}Step 4: Initializing Terraform${NC}"
cd terraform/01-foundation
terraform init
terraform validate

echo -e "${GREEN}✓${NC} Terraform initialized and validated"

# Step 5: Review plan
echo -e "\n${YELLOW}Step 5: Review Deployment Plan${NC}"
terraform plan -out=tfplan.out

read -p "Continue with deployment? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Step 6: Deploy
echo -e "\n${YELLOW}Step 6: Deploying Infrastructure${NC}"
terraform apply tfplan.out

echo -e "\n${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Setup Complete!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"

echo -e "\n${YELLOW}Next Steps:${NC}"
echo "1. Deploy Layer 2 (Network): terraform -chdir=../02-network init && terraform -chdir=../02-network apply"
echo "2. Review DEPLOYMENT.md for detailed procedures"
echo "3. Check status: ./run.sh status"
```

**Benefits**:
- **Guidance**: Reduce human error in setup
- **Validation**: Catch issues early
- **Documentation**: Interactive learning tool

**Effort**: 1-2 weeks | **ROI**: 70% reduction in setup support tickets

---

## Category 4: Operational Excellence Enhancements

### 4.1 SLO/SLI Framework

**Current State**: Basic uptime monitoring
**Enhancement**: Structured SLO tracking with error budgets

```hcl
# terraform/05-observability/slo-framework.tf (NEW)

# Define SLOs for Portal API
resource "google_monitoring_slo" "api_availability" {
  display_name       = "Portal API Availability"
  goal               = 0.9995  # 99.95% SLO
  rolling_period_days = 30

  service_level_indicator {
    request_based_sli {
      good_filter = "metric.type=\"serviceruntime.googleapis.com/api/consumer/quota_used_count\" AND resource.service=\"portal-backend.run.app\" AND metric.response_code_class=\"2xx\""
      total_filter = "metric.type=\"serviceruntime.googleapis.com/api/consumer/quota_used_count\" AND resource.service=\"portal-backend.run.app\""
    }
  }
}

# Error budget tracking
resource "google_monitoring_alert_policy" "error_budget_burn" {
  display_name = "Error Budget Burn Rate (API)"
  combiner     = "OR"

  conditions {
    display_name = "Burn rate > 1 (30-day window)"

    condition_threshold {
      filter          = "resource.type=\"api\" AND metric.type=\"serviceruntime.googleapis.com/api/error_count\""
      comparison      = "COMPARISON_GT"
      threshold_value = 0.01  # 1% of monthly budget
      duration        = "300s"
    }
  }

  notification_channels = [google_monitoring_notification_channel.pagerduty.id]
}

# SLI Dashboard
resource "google_monitoring_dashboard" "slo_dashboard" {
  dashboard_json = jsonencode({
    displayName = "SLO Dashboard"
    mosaicLayout = {
      columns = 12
      tiles = [
        {
          width  = 6
          height = 4
          xyChart = {
            dataSets = [{
              timeSeriesQuery = {
                timeSeriesFilter = {
                  filter = "metric.type=\"serviceruntime.googleapis.com/api/producer/quota_used_count\""
                }
              }
            }]
            yAxis = {
              label = "Error Rate"
              scale = "LINEAR"
            }
          }
        },
        {
          width  = 6
          height = 4
          scorecard = {
            timeSeriesQuery = {
              timeSeriesFilter = {
                filter = "metric.type=\"serviceruntime.googleapis.com/api/producer/quota_used_count\""
              }
            }
            sparkChart = {
              chartType = "SPARK_LINE"
            }
            thresholds = [
              { value = 0.95 }
            ]
          }
        }
      ]
    }
  })
}
```

**Benefits**:
- **Accountability**: Clear performance targets
- **Burn Rate**: Proactive alert on trend changes
- **Trade-off**: Deploy with confidence when budget available

**Effort**: 1-2 weeks | **ROI**: 40% reduction in post-incident recovery time

---

### 4.2 Automated Incident Remediation

**Current State**: Manual runbook execution
**Enhancement**: Self-healing automation for common issues

```python
# scripts/automation/auto-remediation.py (NEW)

import functions_framework
from google.cloud import monitoring_v3
from google.cloud import compute_v1
import logging

logger = logging.getLogger(__name__)

@functions_framework.cloud_event
def auto_remediate(cloud_event):
    """Automatically remediate common infrastructure issues"""

    pubsub_message = cloud_event.data["message"]["data"]
    alert_data = json.loads(pubsub_message)

    alert_policy = alert_data.get("incident", {}).get("policy_name")

    # Route to appropriate handler
    if "high-cpu" in alert_policy:
        handle_high_cpu(alert_data)
    elif "memory-pressure" in alert_policy:
        handle_memory_pressure(alert_data)
    elif "disk-full" in alert_policy:
        handle_disk_full(alert_data)
    elif "pod-crash" in alert_policy:
        handle_pod_crash(alert_data)

def handle_high_cpu(alert_data):
    """Auto-scale on high CPU"""
    instance_group = alert_data.get("resource", {}).get("instance_group")

    if instance_group:
        compute = compute_v1.InstanceGroupManagersClient()

        # Get current target size
        response = compute.get(
            project=alert_data["project"],
            zone=alert_data["zone"],
            instance_group_manager=instance_group
        )

        current_size = response.target_size
        new_size = min(current_size + 2, response.auto_scaling_policy.max_num_replicas)

        # Update target size
        compute.resize(
            project=alert_data["project"],
            zone=alert_data["zone"],
            instance_group_manager=instance_group,
            size=new_size
        )

        logger.info(f"Scaled {instance_group} from {current_size} to {new_size}")

def handle_pod_crash(alert_data):
    """Remediate pod crashes"""
    namespace = alert_data.get("resource", {}).get("namespace")
    pod = alert_data.get("resource", {}).get("pod")

    # Get pod details
    kubectl_cmd = f"kubectl describe pod {pod} -n {namespace}"
    output = subprocess.run(kubectl_cmd, shell=True, capture_output=True, text=True)

    # Check for common issues
    if "OOMKilled" in output.stdout:
        logger.warning(f"Pod {pod} OOM killed - increasing memory limit")
        # Update pod memory limits
    elif "CrashLoopBackOff" in output.stdout:
        logger.error(f"Pod {pod} in crash loop - check logs")
        # Send alert to on-call engineer
```

**Benefits**:
- **Speed**: MTTR reduced from hours to seconds
- **Reliability**: Consistent response to known issues
- **Learning**: Data for process improvement

**Effort**: 2-3 weeks | **ROI**: 80% reduction in MTTR for common issues

---

## Category 5: Scalability & Multi-Region Enhancements

### 5.1 Multi-Region Architecture Pattern

**Current State**: Single-region deployment
**Enhancement**: Active-active multi-region with cross-region replication

```hcl
# terraform/02-network/global-load-balancing.tf (NEW)

# Global load balancer for multi-region failover
resource "google_compute_global_forwarding_rule" "https" {
  name       = "portal-https-lb"
  ip_version = "IPV4"

  load_balancing_scheme = "EXTERNAL"
  target               = google_compute_target_https_proxy.default.id

  ip_address = google_compute_global_address.https.id
}

# Create backend services for each region
resource "google_compute_backend_service" "api_us_central" {
  name                            = "portal-api-us-central1"
  protocol                        = "HTTPS"
  port_name                       = "https"
  timeout_sec                     = 10
  health_checks                   = [google_compute_health_check.api.id]
  load_balancing_scheme          = "EXTERNAL"
  session_affinity                = "CLIENT_IP"
  affinity_cookie_ttl_sec        = 600

  backend {
    group           = google_compute_instance_group.api_us_central.id
    balancing_mode  = "RATE"
    max_rate_per_instance = 1000
  }

  depends_on = [google_compute_instance_group.api_us_central]
}

resource "google_compute_backend_service" "api_europe_west" {
  name                     = "portal-api-europe-west1"
  protocol                 = "HTTPS"
  port_name                = "https"
  timeout_sec              = 10
  health_checks            = [google_compute_health_check.api_eu.id]
  load_balancing_scheme    = "EXTERNAL"

  backend {
    group          = google_compute_instance_group.api_europe.id
    balancing_mode = "RATE"
    max_rate_per_instance = 1000
  }
}

# URL Map for routing
resource "google_compute_url_map" "default" {
  name            = "portal-https-lb-map"
  default_service = google_compute_backend_service.api_us_central.id

  host_rule {
    hosts        = ["portal-eu.example.com"]
    path_matcher = "europe"
  }

  path_matcher {
    name            = "europe"
    default_service = google_compute_backend_service.api_europe_west.id

    path_rule {
      paths   = ["/*"]
      service = google_compute_backend_service.api_europe_west.id
    }
  }
}

# Cross-region database replication
resource "google_sql_database_instance" "replica_europe" {
  name               = "portal-db-eu-replica"
  database_version   = "POSTGRES_15"
  region             = "europe-west1"

  master_instance_name = google_sql_database_instance.primary.name
}
```

**Benefits**:
- **Availability**: 99.99% uptime with failover
- **Latency**: Serve users from closest region
- **Compliance**: Keep data in specific regions

**Effort**: 3-4 weeks | **ROI**: Access to new markets, compliance requirements

---

### 5.2 Disaster Recovery as Code

**Current State**: Manual backup & recovery procedures
**Enhancement**: Automated, tested DR with terraform

```hcl
# terraform/modules/dr/dr-automation.tf (NEW)

# Automated daily snapshots
resource "google_compute_snapshot_schedule" "daily" {
  name = "portal-daily-snapshots"

  schedule {
    daily_schedule {
      days_in_cycle = 1
      start_time    = "03:00"  # 3 AM UTC
    }
  }

  snapshot_properties {
    labels = {
      dr_plan = "daily"
      recovery_point = "daily"
    }
    storage_locations = ["us"]
  }

  source_disks = [
    google_compute_disk.database.id,
    google_compute_disk.application.id
  ]
}

# Cross-region backup of database
resource "google_sql_backup_run" "backup" {
  instance = google_sql_database_instance.primary.name
  description = "Daily backup for DR"
  backup_kind = "SNAPSHOT"  # vs. AUTOMATED

  depends_on = [google_sql_database_instance.primary]
}

# DR simulation (monthly)
resource "google_scheduler_job" "dr_test" {
  name             = "portal-dr-test"
  description      = "Monthly DR simulation"
  schedule         = "0 0 5 * *"  # 5th of each month
  time_zone        = "UTC"
  attempt_deadline = "320s"
  region           = "us-central1"

  http_target {
    http_method = "POST"
    uri         = "https://cloudscheduler.googleapis.com/v1/projects/${var.project_id}/locations/us-central1/jobs/portal-dr-test/pause"

    oidc_token {
      service_account_email = google_service_account.dr_automation.email
    }
  }
}

# Automated DR recovery script
resource "null_resource" "dr_recovery_runbook" {
  provisioner "file" {
    source      = "${path.module}/dr-recovery.sh"
    destination = "/tmp/dr-recovery.sh"

    connection {
      type = "ssh"
      user = "ubuntu"
      host = google_compute_instance.dr_host.network_interface[0].nat_ip
    }
  }
}
```

**Benefits**:
- **Confidence**: DR procedures tested monthly
- **Speed**: Recovery in < 2 hours
- **Compliance**: Audit-ready process documentation

**Effort**: 2-3 weeks | **ROI**: Regulatory compliance, customer trust

---

## Category 6: Governance & Compliance Enhancements

### 6.1 Automated Compliance Reporting

**Current State**: Manual compliance documentation
**Enhancement**: Automated FedRAMP/SOC 2 evidence collection

```python
# scripts/governance/compliance-evidence-collector.py (NEW)

import functions_framework
from google.cloud import logging as cloud_logging
from google.cloud import audit_log
from datetime import datetime, timedelta
import json

@functions_framework.http
def collect_compliance_evidence(request):
    """Automatically collect evidence for compliance reports"""

    logger = cloud_logging.Client().logger("compliance-evidence")

    evidence = {
        "timestamp": datetime.utcnow().isoformat(),
        "controls": {}
    }

    # AC-1: Access Control Policy
    evidence["controls"]["AC-1"] = collect_ac1_evidence()

    # AC-2: User Registration
    evidence["controls"]["AC-2"] = collect_ac2_evidence()

    # AC-3: Access Enforcement
    evidence["controls"]["AC-3"] = collect_ac3_evidence()

    # AU-2: Audit Logging
    evidence["controls"]["AU-2"] = collect_au2_evidence()

    # SC-7: Boundary Protection
    evidence["controls"]["SC-7"] = collect_sc7_evidence()

    # Store in secure location
    store_evidence(evidence)

    logger.log_struct({
        "severity": "INFO",
        "message": "Compliance evidence collection complete",
        "controls_collected": len(evidence["controls"])
    })

    return {"status": "success", "controls": len(evidence["controls"])}

def collect_ac2_evidence():
    """Collect user registration evidence"""
    logs = cloud_logging.Client().list_entries(
        filter_="resource.type=cloud_function AND jsonPayload.event_type=user_created"
    )

    return {
        "control": "AC-2",
        "title": "User Registration",
        "evidence": [
            {
                "date": entry.timestamp.isoformat(),
                "user": entry.payload.get("user_id"),
                "action": "user_created"
            }
            for entry in logs
        ]
    }

def collect_au2_evidence():
    """Collect audit logging evidence"""
    # Query Cloud Audit Logs
    query = """
    SELECT
      timestamp,
      protoPayload.authenticationInfo.principalEmail as user,
      protoPayload.methodName as action,
      resource.name as resource
    FROM `[PROJECT].cloudaudit_googleapis_com.activity`
    WHERE timestamp >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 30 DAY)
    ORDER BY timestamp DESC
    """

    # Return summary statistics
    return {
        "control": "AU-2",
        "title": "Audit Logging",
        "evidence": {
            "period": "30_days",
            "total_log_entries": get_log_count(),
            "services_monitored": get_monitored_services(),
            "retention_days": 400
        }
    }
```

**Benefits**:
- **Audit Ready**: Evidence collection on-demand
- **Efficiency**: Reduce manual documentation
- **Accuracy**: Complete, timestamped evidence

**Effort**: 2-3 weeks | **ROI**: FedRAMP authorization acceleration

---

## Implementation Roadmap

### Phase 1 (Q1 2026): Security & Cost
- [ ] 1.1 Zero-Trust Network (VPC Service Controls)
- [ ] 1.2 Secrets Rotation Automation
- [ ] 2.1 Cost Attribution Framework

**Effort**: 4-5 weeks | **Impact**: High

### Phase 2 (Q2 2026): Developer Experience
- [ ] 3.1 Infrastructure Templates
- [ ] 3.2 Interactive Onboarding CLI
- [ ] 4.1 SLO Framework

**Effort**: 4-5 weeks | **Impact**: High

### Phase 3 (Q3 2026): Scalability & Governance
- [ ] 5.1 Multi-Region Architecture
- [ ] 5.2 Disaster Recovery Automation
- [ ] 6.1 Compliance Evidence Collection

**Effort**: 5-6 weeks | **Impact**: Medium-High

---

## Success Metrics

| Enhancement | Metric | Target |
|-------------|--------|--------|
| Zero-Trust | Policy violations caught | 100% |
| Cost Optimization | Cost reduction | 20-30% |
| Developer Experience | Onboarding time | < 2 hours |
| SLOs | API availability | 99.95% |
| Multi-Region | Regional failover time | < 30 sec |
| DR | Recovery time objective | < 2 hours |
| Compliance | Evidence collection | Automated |

---

## Next Steps

1. **Prioritize**: Discuss with stakeholders which enhancements align with roadmap
2. **Estimate**: Refine effort estimates with team
3. **Schedule**: Plan implementation across quarters
4. **Execute**: Start with Phase 1 highest-impact items

---

**Document Version**: 1.0
**Last Updated**: 2026-01-19
**Owner**: Platform Engineering
**Review Cycle**: Quarterly
