# Automation Scripts Documentation

This document describes the automation scripts available in the project and how to use them.

## Table of Contents

1. [normalize_issues.py](#normalize_issuespy)
2. [ci_monitoring.py](#ci_monitoringpy)
3. [disaster_recovery.sh](#disaster_recoverysh)
4. [Common Usage Patterns](#common-usage-patterns)

---

## normalize_issues.py

**Location:** `scripts/automation/normalize_issues.py`

Normalizes and standardizes GitHub issues in the repository, ensuring consistent formatting, labels, and metadata across all issues.

### Overview

The script processes GitHub issues and:
- Validates issue format (title, body, labels)
- Applies standard labels based on issue content
- Updates milestone assignments
- Normalizes issue descriptions
- Checks for required fields

### Installation

```bash
# Install dependencies
pip install PyGithub pyyaml

# Or use the provided setup
cd scripts/automation
pip install -r requirements.txt
```

### Basic Usage

```bash
# Display help
python normalize_issues.py --help

# Dry-run mode (preview changes without making them)
python normalize_issues.py --repo kushin77/GCP-landing-zone-Portal --dry-run

# Apply normalization to all issues
python normalize_issues.py --repo kushin77/GCP-landing-zone-Portal --apply

# Target specific issues
python normalize_issues.py --repo kushin77/GCP-landing-zone-Portal --issue-numbers 87,88,89,90 --apply

# Normalize only open issues
python normalize_issues.py --repo kushin77/GCP-landing-zone-Portal --state open --apply

# Normalize only closed issues
python normalize_issues.py --repo kushin77/GCP-landing-zone-Portal --state closed --apply
```

### Advanced Usage

```bash
# Normalize with custom configuration
python normalize_issues.py \
  --repo kushin77/GCP-landing-zone-Portal \
  --config scripts/automation/config.yaml \
  --apply \
  --verbose

# Generate report without changes
python normalize_issues.py \
  --repo kushin77/GCP-landing-zone-Portal \
  --report \
  --output issues_report.json

# Check specific label consistency
python normalize_issues.py \
  --repo kushin77/GCP-landing-zone-Portal \
  --validate-labels \
  --dry-run
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--help` | Show help message | `python normalize_issues.py --help` |
| `--repo` | GitHub repository | `--repo kushin77/GCP-landing-zone-Portal` |
| `--token` | GitHub token (or use GITHUB_TOKEN env var) | `--token ghp_xxx` |
| `--dry-run` | Preview changes without applying | `--dry-run` |
| `--apply` | Apply changes to repository | `--apply` |
| `--issue-numbers` | Comma-separated issue numbers | `--issue-numbers 87,88,89` |
| `--state` | Filter by state: open, closed, all | `--state open` |
| `--config` | Configuration file path | `--config config.yaml` |
| `--report` | Generate report | `--report` |
| `--output` | Output file for report | `--output report.json` |
| `--verbose` | Verbose logging | `--verbose` |
| `--validate-labels` | Only validate labels | `--validate-labels` |

### Sample Output

**Dry-Run Output:**
```
Fetching issues from kushin77/GCP-landing-zone-Portal...
Processing 15 issues...

Issue #87 (Access & Permissions)
  Current labels: epic, onboarding
  Suggested labels: epic, onboarding, access-control
  Missing milestone: Q1 2026

Issue #88 (CI/CD & Tests)
  Current labels: epic, onboarding
  Suggested labels: epic, onboarding, ci-cd
  Status: OK

Report saved to issues_report.json
Changes: 2 label updates, 1 milestone assignment
```

### Configuration File

**Example:** `scripts/automation/config.yaml`

```yaml
labels:
  epic:
    color: "0075ca"
    description: "Major feature or initiative"
  onboarding:
    color: "a2eeef"
    description: "Onboarding task"
  task:
    color: "c5def5"
    description: "Actionable task"
  security:
    color: "d73a49"
    description: "Security-related issue"

milestones:
  Q1-2026:
    due_date: "2026-03-31"
    description: "Q1 2026 goals"

label_rules:
  - pattern: "^Epic:"
    labels: ["epic"]
  - pattern: "security"
    labels: ["security"]
  - pattern: "urgent|critical"
    labels: ["priority-high"]

title_requirements:
  min_length: 10
  max_length: 100
  required_prefix: false
```

---

## ci_monitoring.py

**Location:** `scripts/automation/ci_monitoring.py`

Monitors CI/CD pipeline status, collects build metrics, and provides insights into pipeline health.

### Overview

The script:
- Fetches recent build history from Cloud Build
- Analyzes build success/failure rates
- Calculates pipeline metrics (avg duration, pass rate)
- Exports metrics to monitoring systems
- Generates CI health reports

### Installation

```bash
# Install dependencies
pip install google-cloud-build google-cloud-monitoring

# Or use the provided setup
cd scripts/automation
pip install -r requirements.txt
```

### Basic Usage

```bash
# Display help
python ci_monitoring.py --help

# Get latest build status
python ci_monitoring.py --latest

# View build history (last 10 builds)
python ci_monitoring.py --history --limit 10

# Export metrics to Prometheus
python ci_monitoring.py --export prometheus --output metrics.txt

# Generate CI health report
python ci_monitoring.py --report --output report.html
```

### Advanced Usage

```bash
# Monitor specific time period
python ci_monitoring.py \
  --history \
  --since "2026-01-20" \
  --until "2026-01-29" \
  --format json \
  --output builds.json

# Calculate metrics with thresholds
python ci_monitoring.py \
  --metrics \
  --threshold-success-rate 95 \
  --threshold-max-duration 3600 \
  --alert

# Export to multiple formats
python ci_monitoring.py \
  --export prometheus \
  --export datadog \
  --output /var/lib/monitoring/

# Watch builds in real-time
python ci_monitoring.py --watch --interval 30
```

### Command-Line Options

| Option | Description | Example |
|--------|-------------|---------|
| `--help` | Show help | `python ci_monitoring.py --help` |
| `--project` | GCP project ID | `--project my-project` |
| `--latest` | Show latest build | `--latest` |
| `--history` | Show build history | `--history --limit 20` |
| `--since` | Start date for history | `--since "2026-01-20"` |
| `--until` | End date for history | `--until "2026-01-29"` |
| `--metrics` | Calculate metrics | `--metrics` |
| `--export` | Export format | `--export prometheus` |
| `--output` | Output file/directory | `--output metrics.txt` |
| `--report` | Generate HTML report | `--report` |
| `--format` | Output format: json, text, table | `--format json` |
| `--alert` | Enable alerting | `--alert` |
| `--watch` | Watch in real-time | `--watch` |
| `--interval` | Update interval (seconds) | `--interval 30` |
| `--verbose` | Verbose logging | `--verbose` |

### Sample Output

**Build Status Output:**
```
Latest Build Status
===================
Build ID: abc123def456
Status: SUCCESS
Duration: 12m 34s
Triggered by: feat/new-feature
Commit: abc123 (New feature implementation)
Started: 2026-01-29 14:30:00 UTC
Ended: 2026-01-29 14:42:34 UTC

Build History (Last 10)
=======================
abc123def456  SUCCESS   12m 34s   2026-01-29 14:30:00
xyz789abc123  SUCCESS   13m 01s   2026-01-29 13:15:00
def456ghi789  FAILURE   8m 15s    2026-01-29 11:45:00
...

Pipeline Metrics
================
Success Rate: 92.3% (12/13 builds)
Avg Duration: 12m 48s
Median Duration: 12m 30s
Max Duration: 15m 45s
Min Duration: 8m 15s
Failure Count: 1 (last 24h)
```

**Metrics Export (Prometheus Format):**
```
# HELP ci_build_success_rate Build success rate
# TYPE ci_build_success_rate gauge
ci_build_success_rate{project="kushin77/GCP-landing-zone-Portal"} 0.923

# HELP ci_build_duration_seconds Build duration in seconds
# TYPE ci_build_duration_seconds histogram
ci_build_duration_seconds_bucket{project="kushin77/GCP-landing-zone-Portal",le="300"} 0
ci_build_duration_seconds_bucket{project="kushin77/GCP-landing-zone-Portal",le="600"} 5
ci_build_duration_seconds_bucket{project="kushin77/GCP-landing-zone-Portal",le="900"} 12
```

---

## disaster_recovery.sh

**Location:** `scripts/disaster_recovery.sh`

Provides disaster recovery procedures for backing up and restoring critical data and configurations.

### Overview

Functionality:
- Backup database and configurations
- Export Cloud resources
- Create snapshots
- Restore from backups
- Validate backup integrity

### Usage

```bash
# Display help
./scripts/disaster_recovery.sh --help

# Create backup
./scripts/disaster_recovery.sh backup --full

# Create incremental backup
./scripts/disaster_recovery.sh backup --incremental

# List backups
./scripts/disaster_recovery.sh list-backups

# Restore from backup
./scripts/disaster_recovery.sh restore --backup-id abc123

# Validate backup
./scripts/disaster_recovery.sh validate --backup-id abc123

# Export to cloud storage
./scripts/disaster_recovery.sh export --destination gs://my-bucket/backups/
```

---

## Common Usage Patterns

### Pattern 1: Pre-Commit Validation

Run normalization before committing:

```bash
# In your pre-commit hook
python scripts/automation/normalize_issues.py \
  --repo kushin77/GCP-landing-zone-Portal \
  --validate-labels \
  --dry-run

if [ $? -eq 0 ]; then
  echo "Issue validation passed"
else
  echo "Issue validation failed - fix issues before committing"
  exit 1
fi
```

### Pattern 2: Scheduled Maintenance

Run daily normalization via cron:

```bash
# In crontab: run daily at 2 AM UTC
0 2 * * * cd /home/kushin77/GCP-landing-zone-Portal && python scripts/automation/normalize_issues.py --repo kushin77/GCP-landing-zone-Portal --apply >> logs/normalize.log 2>&1
```

### Pattern 3: CI Pipeline Integration

Include in cloudbuild.yaml:

```yaml
steps:
  - name: 'gcr.io/cloud-builders/python'
    args:
      - pip
      - install
      - -r
      - scripts/automation/requirements.txt
  
  - name: 'gcr.io/cloud-builders/python'
    args:
      - python
      - scripts/automation/normalize_issues.py
      - --repo
      - kushin77/GCP-landing-zone-Portal
      - --apply
```

### Pattern 4: Monitoring Setup

Export metrics to Prometheus:

```bash
# Create systemd service for monitoring
cat > /etc/systemd/system/ci-monitor.service << EOF
[Unit]
Description=CI Monitoring Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/kushin77/GCP-landing-zone-Portal
ExecStart=/usr/bin/python scripts/automation/ci_monitoring.py \
  --export prometheus \
  --output /var/lib/prometheus/ci_metrics.txt \
  --watch \
  --interval 60

Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable ci-monitor
systemctl start ci-monitor
```

---

## Troubleshooting

### Common Issues

**Issue:** Authentication failed
- **Solution:** Set `GITHUB_TOKEN` environment variable
- **Command:** `export GITHUB_TOKEN="ghp_your_token_here"`

**Issue:** Project not found
- **Solution:** Verify project ID: `gcloud config get-value project`
- **Solution:** Set explicitly: `python ci_monitoring.py --project your-project-id`

**Issue:** Permission denied
- **Solution:** Ensure service account has required permissions
- **Solution:** Check IAM roles: `gcloud projects get-iam-policy PROJECT_ID`

### Debug Mode

Run with verbose logging:

```bash
# normalize_issues.py
python normalize_issues.py --verbose --dry-run

# ci_monitoring.py
python ci_monitoring.py --verbose --latest
```

---

## Getting Help

- Run `--help` flag on any script
- Check GitHub Issues for known problems
- Review examples in this documentation
- Contact @kushin77 for assistance

---

**Last Updated:** 2026-01-29  
**Scripts Version:** 1.0  
**Python Version:** 3.11+
