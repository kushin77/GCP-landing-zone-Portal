-- BigQuery materialized views for Portal
-- These should be created in the billing_export dataset

-- 1. Daily project cost summary (15-minute refresh)
CREATE OR REPLACE MATERIALIZED VIEW `{PROJECT_ID}.billing_export.project_daily_costs` AS
SELECT
    DATE(usage_start_time) as cost_date,
    project.id as project_id,
    service.description as service,
    resource.global_name as resource_type,
    SUM(cost) as daily_cost,
    SUM(usage.amount) as usage_quantity,
    COUNT(DISTINCT resource.global_name) as resource_count,
    CURRENT_TIMESTAMP() as last_updated
FROM `{PROJECT_ID}.billing_export.gcp_billing_export_v1`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY cost_date, project_id, service, resource_type
ORDER BY cost_date DESC, daily_cost DESC;

---
-- 2. Project monthly costs aggregated
CREATE OR REPLACE MATERIALIZED VIEW `{PROJECT_ID}.billing_export.project_monthly_costs` AS
SELECT
    TIMESTAMP_TRUNC(usage_start_time, MONTH) as month,
    project.id as project_id,
    SUM(cost) as monthly_cost,
    AVG(cost) as avg_daily_cost,
    COUNT(*) as transaction_count,
    CURRENT_TIMESTAMP() as last_updated
FROM `{PROJECT_ID}.billing_export.gcp_billing_export_v1`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 12 MONTH)
GROUP BY month, project_id
ORDER BY month DESC;

---
-- 3. Service-level cost breakdown by day
CREATE OR REPLACE MATERIALIZED VIEW `{PROJECT_ID}.billing_export.daily_service_costs` AS
SELECT
    DATE(usage_start_time) as cost_date,
    service.description as service,
    SUM(cost) as daily_cost,
    COUNT(DISTINCT project.id) as project_count,
    CURRENT_TIMESTAMP() as last_updated
FROM `{PROJECT_ID}.billing_export.gcp_billing_export_v1`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY cost_date, service
ORDER BY cost_date DESC, daily_cost DESC;

---
-- 4. Cost trends (7-day rolling average)
CREATE OR REPLACE MATERIALIZED VIEW `{PROJECT_ID}.billing_export.cost_trends` AS
SELECT
    DATE(usage_start_time) as cost_date,
    project.id as project_id,
    SUM(cost) as daily_cost,
    AVG(SUM(cost)) OVER (
        PARTITION BY project.id
        ORDER BY DATE(usage_start_time)
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) as rolling_7day_avg,
    CURRENT_TIMESTAMP() as last_updated
FROM `{PROJECT_ID}.billing_export.gcp_billing_export_v1`
WHERE DATE(usage_start_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
GROUP BY cost_date, project_id
ORDER BY cost_date DESC;

---
-- 5. Compliance resource inventory snapshot
CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.portal.compliance_resources_inventory` (
    scan_timestamp TIMESTAMP NOT NULL,
    project_id STRING NOT NULL,
    resource_type STRING NOT NULL,
    resource_id STRING NOT NULL,
    resource_name STRING,
    labels JSON,
    compliance_status STRING,
    created_time TIMESTAMP,
    updated_time TIMESTAMP
)
PARTITION BY DATE(scan_timestamp)
CLUSTER BY project_id, resource_type
OPTIONS(
    description="Portal compliance resource inventory",
    require_partition_filter=true
);

---
-- 6. Audit log for Portal actions
CREATE TABLE IF NOT EXISTS `{PROJECT_ID}.portal.audit_logs` (
    event_timestamp TIMESTAMP NOT NULL,
    trace_id STRING,
    user_id STRING,
    action STRING,
    resource_type STRING,
    resource_id STRING,
    status STRING,
    error_message STRING,
    request_id STRING,
    user_email STRING,
    ip_address STRING,
    user_agent STRING
)
PARTITION BY DATE(event_timestamp)
CLUSTER BY user_id, resource_type, action
OPTIONS(
    description="Portal audit logs for compliance",
    require_partition_filter=true,
    expiration_ms=7776000000  -- 90 days
);

---
-- Indexes for common queries
CREATE INDEX idx_project_costs ON `{PROJECT_ID}.billing_export.project_daily_costs`(
    project_id, cost_date DESC
);

CREATE INDEX idx_service_costs ON `{PROJECT_ID}.billing_export.daily_service_costs`(
    service, cost_date DESC
);

CREATE INDEX idx_compliance_project ON `{PROJECT_ID}.portal.compliance_resources_inventory`(
    project_id, resource_type
);

CREATE INDEX idx_audit_user ON `{PROJECT_ID}.portal.audit_logs`(
    user_id, event_timestamp DESC
);
