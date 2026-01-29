"""
Workflows API router for infrastructure provisioning.
"""
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from models.schemas import BaseResponse, Workflow, WorkflowApproval, WorkflowRequest, WorkflowStatus

router = APIRouter(prefix="/api/v1/workflows", tags=["workflows"])

# In-memory storage (replace with database in production)
workflows_db: Dict[str, Workflow] = {}


@router.post("/", response_model=Workflow)
async def create_workflow(request: WorkflowRequest):
    """Create a new infrastructure workflow request."""
    workflow_id = str(uuid.uuid4())

    workflow = Workflow(
        id=workflow_id,
        type=request.type,
        title=request.title,
        description=request.description,
        requester=request.requester,
        resource_type=request.resource_type,
        configuration=request.configuration,
        justification=request.justification,
        cost_estimate=request.cost_estimate,
        compliance_review_required=request.compliance_review_required,
        status=WorkflowStatus.PENDING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        approvals=[],
        execution_logs=[],
    )

    workflows_db[workflow_id] = workflow

    # Log creation
    workflow.execution_logs.append(
        f"{datetime.utcnow().isoformat()} - Workflow created by {request.requester}"
    )

    return workflow


@router.get("/", response_model=List[Workflow])
async def list_workflows(
    status: Optional[WorkflowStatus] = None,
    requester: Optional[str] = None,
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
):
    """List all workflows with optional filtering."""
    filtered = list(workflows_db.values())

    if status:
        filtered = [w for w in filtered if w.status == status]

    if requester:
        filtered = [w for w in filtered if w.requester == requester]

    # Sort by created_at desc
    filtered.sort(key=lambda w: w.created_at, reverse=True)

    # Paginate
    start = (page - 1) * limit
    end = start + limit

    return filtered[start:end]


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(workflow_id: str):
    """Get workflow details."""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    return workflows_db[workflow_id]


@router.post("/{workflow_id}/approve", response_model=Workflow)
async def approve_workflow(workflow_id: str, approval: WorkflowApproval):
    """Approve or reject a workflow."""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflows_db[workflow_id]

    if workflow.status != WorkflowStatus.PENDING:
        raise HTTPException(
            status_code=400, detail=f"Cannot approve workflow in {workflow.status} status"
        )

    # Add approval
    workflow.approvals.append(approval)
    workflow.updated_at = datetime.utcnow()

    # Update status
    if approval.approved:
        workflow.status = WorkflowStatus.APPROVED
        workflow.execution_logs.append(
            f"{datetime.utcnow().isoformat()} - Approved by {approval.approver}"
        )

        # Auto-execute if no compliance review needed
        if not workflow.compliance_review_required:
            await execute_workflow(workflow_id)
    else:
        workflow.status = WorkflowStatus.REJECTED
        workflow.execution_logs.append(
            f"{datetime.utcnow().isoformat()} - Rejected by {approval.approver}: {approval.comments}"
        )

    return workflow


@router.post("/{workflow_id}/execute", response_model=Workflow)
async def execute_workflow(workflow_id: str):
    """Execute an approved workflow."""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflows_db[workflow_id]

    if workflow.status != WorkflowStatus.APPROVED:
        raise HTTPException(
            status_code=400, detail=f"Cannot execute workflow in {workflow.status} status"
        )

    # Update status
    workflow.status = WorkflowStatus.IN_PROGRESS
    workflow.updated_at = datetime.utcnow()
    workflow.execution_logs.append(f"{datetime.utcnow().isoformat()} - Execution started")

    # In production, this would:
    # 1. Generate Terraform plan
    # 2. Execute via Cloud Build or Terraform Cloud
    # 3. Monitor progress
    # 4. Update status

    # Simulate execution
    workflow.terraform_plan = f"""
Terraform will perform the following actions:

  # {workflow.resource_type}.{workflow.configuration.get('name', 'resource')} will be created
  + resource "{workflow.resource_type}" "main" {{
      + name   = "{workflow.configuration.get('name', 'resource')}"
      + region = "{workflow.configuration.get('region', 'us-central1')}"
      # ... more configuration
    }}

Plan: 1 to add, 0 to change, 0 to destroy.
"""

    workflow.execution_logs.append(f"{datetime.utcnow().isoformat()} - Terraform plan generated")

    # Simulate completion
    workflow.status = WorkflowStatus.COMPLETED
    workflow.execution_logs.append(
        f"{datetime.utcnow().isoformat()} - Execution completed successfully"
    )

    return workflow


@router.delete("/{workflow_id}", response_model=BaseResponse)
async def cancel_workflow(workflow_id: str):
    """Cancel a workflow."""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflows_db[workflow_id]

    if workflow.status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
        raise HTTPException(
            status_code=400, detail=f"Cannot cancel workflow in {workflow.status} status"
        )

    del workflows_db[workflow_id]

    return BaseResponse(success=True, message=f"Workflow {workflow_id} cancelled")


@router.get("/{workflow_id}/terraform-plan")
async def get_terraform_plan(workflow_id: str):
    """Get Terraform plan for a workflow."""
    if workflow_id not in workflows_db:
        raise HTTPException(status_code=404, detail="Workflow not found")

    workflow = workflows_db[workflow_id]

    if not workflow.terraform_plan:
        raise HTTPException(status_code=404, detail="Terraform plan not yet generated")

    return {
        "workflow_id": workflow_id,
        "plan": workflow.terraform_plan,
        "generated_at": workflow.updated_at,
    }
