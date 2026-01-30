"""
Pydantic models for API request/response schemas.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# Enums
class ResourceType(str, Enum):
    PROJECT = "project"
    VPC = "vpc"
    SUBNET = "subnet"
    INSTANCE = "instance"
    SERVICE_ACCOUNT = "service_account"
    BUCKET = "bucket"
    DATABASE = "database"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ComplianceFramework(str, Enum):
    NIST_800_53 = "NIST 800-53"
    FEDRAMP = "FedRAMP"
    CIS = "CIS"
    PCI_DSS = "PCI DSS"
    HIPAA = "HIPAA"
    SOC2 = "SOC 2"


# Base Models
def get_utc_now():
    return datetime.now(timezone.utc)


class BaseResponse(BaseModel):
    """Base response model with common fields."""

    success: bool = True
    timestamp: datetime = Field(default_factory=get_utc_now)
    message: Optional[str] = None


class PaginationParams(BaseModel):
    """Pagination parameters."""

    page: int = Field(1, ge=1)
    limit: int = Field(10, ge=1, le=100)
    offset: int = 0

    @model_validator(mode="after")
    def calculate_offset(self) -> "PaginationParams":
        self.offset = (self.page - 1) * self.limit
        return self


class PaginatedResponse(BaseModel):
    """Paginated response wrapper."""

    data: List[Any]
    total: int
    page: int
    limit: int
    pages: int

    @model_validator(mode="after")
    def calculate_pages(self) -> "PaginatedResponse":
        self.pages = (self.total + self.limit - 1) // self.limit if self.limit > 0 else 0
        return self


# Resource Models
class ResourceBase(BaseModel):
    """Base resource model."""

    id: str
    name: str
    type: ResourceType
    project_id: Optional[str] = None
    region: Optional[str] = None
    labels: Dict[str, str] = {}
    created_at: datetime
    updated_at: Optional[datetime] = None


class Resource(ResourceBase):
    """Full resource with metadata."""

    status: str
    owner: Optional[str] = None
    cost_center: Optional[str] = None
    compliance_tags: List[str] = []
    metadata: Dict[str, Any] = {}


class ResourceListResponse(PaginatedResponse):
    """Resource list response."""

    data: List[Resource]


# Project Models
class Project(BaseModel):
    """GCP Project model."""

    id: str
    project_id: str
    name: str
    number: str
    state: str
    parent: Optional[Dict[str, str]] = None
    created_at: datetime
    labels: Dict[str, str] = {}
    billing_account: Optional[str] = None


class ProjectCreateRequest(BaseModel):
    """Project creation request."""

    project_id: str = Field(..., pattern=r"^[a-z][-a-z0-9]{4,28}[a-z0-9]$")
    name: str
    parent_folder: Optional[str] = None
    billing_account: Optional[str] = None
    labels: Dict[str, str] = {}
    justification: str


# Cost Models
class CostBreakdown(BaseModel):
    """Cost breakdown by service."""

    service: str
    cost: float
    currency: str = "USD"
    usage: Optional[float] = None
    unit: Optional[str] = None


class CostSummary(BaseModel):
    """Cost summary with trends."""

    current_month: float
    previous_month: float
    trend_percentage: float
    forecast_end_of_month: float
    budget: Optional[float] = None
    budget_status: str = "on-track"
    breakdown: List[CostBreakdown] = []
    top_projects: List[Dict[str, Any]] = []
    recommendations: List[str] = []


class CostOptimization(BaseModel):
    """Cost optimization recommendation."""

    id: str
    title: str
    description: str
    potential_savings: float
    confidence: float
    resource_type: ResourceType
    resource_id: str
    action: str
    priority: str  # high, medium, low


# Compliance Models
class ComplianceControl(BaseModel):
    """Individual compliance control."""

    id: str
    name: str
    framework: ComplianceFramework
    status: str  # compliant, non-compliant, partial
    severity: str  # critical, high, medium, low
    description: str
    remediation: Optional[str] = None


class ComplianceStatus(BaseModel):
    """Overall compliance status."""

    score: float
    framework: ComplianceFramework
    controls_total: int
    controls_compliant: int
    controls_non_compliant: int
    last_assessed: datetime
    findings: List[ComplianceControl] = []


# Workflow Models
class WorkflowRequest(BaseModel):
    """Infrastructure workflow request."""

    type: str  # vm, project, database, network
    title: str
    description: str
    requester: str
    resource_type: ResourceType
    configuration: Dict[str, Any]
    justification: str
    cost_estimate: Optional[float] = None
    compliance_review_required: bool = False


class WorkflowApproval(BaseModel):
    """Workflow approval/rejection."""

    approved: bool
    approver: str
    comments: Optional[str] = None
    conditions: List[str] = []


class Workflow(WorkflowRequest):
    """Full workflow with status."""

    id: str
    status: WorkflowStatus
    created_at: datetime
    updated_at: Optional[datetime] = None
    approvals: List[WorkflowApproval] = []
    terraform_plan: Optional[str] = None
    execution_logs: List[str] = []


# AI Assistant Models
class AIQuery(BaseModel):
    """AI assistant query."""

    query: str
    context: Optional[Dict[str, Any]] = None
    include_recommendations: bool = True


class AIResponse(BaseModel):
    """AI assistant response."""

    answer: str
    confidence: float
    sources: List[str] = []
    recommendations: List[Dict[str, Any]] = []
    follow_up_questions: List[str] = []


# Security Models
class SecurityFinding(BaseModel):
    """Security finding."""

    id: str
    severity: str
    category: str
    resource: str
    finding: str
    recommendation: str
    status: str
    discovered_at: datetime


class SecurityPosture(BaseModel):
    """Overall security posture."""

    score: float
    critical_findings: int
    high_findings: int
    medium_findings: int
    low_findings: int
    findings: List[SecurityFinding] = []


# Audit Models
class AuditLog(BaseModel):
    """Audit log entry."""

    id: str
    timestamp: datetime
    user: str
    action: str
    resource_type: str
    resource_id: str
    status: str
    details: Dict[str, Any] = {}
    ip_address: Optional[str] = None


# Metrics Models
class MetricDataPoint(BaseModel):
    """Single metric data point."""

    timestamp: datetime
    value: float
    labels: Dict[str, str] = {}


class MetricSeries(BaseModel):
    """Time series metric data."""

    metric: str
    unit: str
    data_points: List[MetricDataPoint]
    aggregation: str = "avg"  # avg, sum, max, min


# User Models
class User(BaseModel):
    """User model."""

    id: str
    email: str
    name: str
    roles: List[str] = []
    projects: List[str] = []
    created_at: datetime
    last_login: Optional[datetime] = None


class UserPermissions(BaseModel):
    """User permissions."""

    user_id: str
    can_create_projects: bool = False
    can_approve_workflows: bool = False
    can_view_costs: bool = True
    can_modify_compliance: bool = False
    max_monthly_budget: Optional[float] = None
