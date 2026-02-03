"""
Task delegation API router.

Provides endpoints for delegating GitHub issues to cloud tasks,
monitoring their status, and managing the task lifecycle.
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from models.schemas import (
    BaseResponse,
    DelegatedTask,
    DelegationRequest,
    DelegationResponse,
    GitHubIssue,
    TaskStatus,
)
from services.github_service import GitHubService
from services.task_delegation_service import TaskDelegationService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/task-delegation", tags=["task-delegation"])


@router.post("/delegate", response_model=DelegationResponse)
async def delegate_issues(request: DelegationRequest):
    """
    Delegate GitHub issues to cloud tasks.
    
    This endpoint fetches issues from the specified GitHub repository and
    creates cloud tasks for autonomous execution. Tasks can be auto-approved
    for immediate execution or marked as pending for manual review.
    
    Args:
        request: Delegation request with repository, filters, and options
        
    Returns:
        Response with created tasks
    """
    logger.info(f"Delegating issues from {request.repository}")
    
    try:
        # Initialize services
        github_service = GitHubService()
        delegation_service = TaskDelegationService()
        
        # Fetch issues from GitHub
        issues = await github_service.fetch_issues(
            repository=request.repository,
            state="open",
            labels=request.labels,
            issue_numbers=request.issue_numbers,
        )
        
        if not issues:
            return DelegationResponse(
                success=True,
                message="No issues found matching the criteria",
                tasks_created=0,
                tasks=[],
            )
        
        # Delegate issues to cloud tasks
        tasks = await delegation_service.delegate_issues(
            issues=issues,
            auto_approve=request.auto_approve,
        )
        
        # Add labels to GitHub issues to indicate delegation
        for issue in issues:
            try:
                existing_labels = issue.labels.copy()
                if "delegated" not in existing_labels:
                    existing_labels.append("delegated")
                    await github_service.update_issue_labels(
                        repository=issue.repository,
                        issue_number=issue.number,
                        labels=existing_labels,
                    )
                
                # Add comment to issue
                status_text = "auto-approved and queued" if request.auto_approve else "pending manual review"
                comment = (
                    f"🤖 **Automated Task Delegation**\n\n"
                    f"This issue has been delegated to cloud-based autonomous execution.\n\n"
                    f"**Status**: {status_text}\n"
                    f"**Philosophy**: Autonomy, best practices, thorough testing\n\n"
                    f"The task will be executed with comprehensive testing and review before completion."
                )
                await github_service.add_issue_comment(
                    repository=issue.repository,
                    issue_number=issue.number,
                    comment=comment,
                )
            except Exception as e:
                logger.error(f"Failed to update GitHub issue #{issue.number}: {e}")
        
        return DelegationResponse(
            success=True,
            message=f"Successfully delegated {len(tasks)} issues",
            tasks_created=len(tasks),
            tasks=tasks,
        )
        
    except Exception as e:
        logger.error(f"Failed to delegate issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks", response_model=List[DelegatedTask])
async def list_tasks(
    repository: Optional[str] = Query(None, description="Filter by repository"),
    status: Optional[TaskStatus] = Query(None, description="Filter by status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of tasks to return"),
):
    """
    List delegated tasks with optional filters.
    
    Args:
        repository: Filter by repository (format: owner/repo)
        status: Filter by task status
        limit: Maximum number of tasks to return
        
    Returns:
        List of delegated tasks
    """
    try:
        delegation_service = TaskDelegationService()
        tasks = await delegation_service.list_tasks(
            repository=repository,
            status=status,
            limit=limit,
        )
        return tasks
    except Exception as e:
        logger.error(f"Failed to list tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}", response_model=DelegatedTask)
async def get_task(task_id: str):
    """
    Get details of a specific delegated task.
    
    Args:
        task_id: Task ID
        
    Returns:
        Task details
    """
    try:
        delegation_service = TaskDelegationService()
        task = await delegation_service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/approve", response_model=BaseResponse)
async def approve_task(task_id: str):
    """
    Approve a pending task for execution.
    
    This endpoint approves a task that is in pending status and queues it
    for cloud execution.
    
    Args:
        task_id: Task ID
        
    Returns:
        Success response
    """
    try:
        delegation_service = TaskDelegationService()
        success = await delegation_service.approve_task(task_id)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to approve task")
        
        return BaseResponse(
            success=True,
            message=f"Task {task_id} approved and queued for execution",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to approve task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/{task_id}/cancel", response_model=BaseResponse)
async def cancel_task(task_id: str):
    """
    Cancel a task.
    
    This endpoint cancels a task that is in pending or queued status.
    Running tasks cannot be cancelled.
    
    Args:
        task_id: Task ID
        
    Returns:
        Success response
    """
    try:
        delegation_service = TaskDelegationService()
        task = await delegation_service.get_task(task_id)
        
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            raise HTTPException(status_code=400, detail=f"Task is already in terminal state: {task.status}")
        
        if task.status == TaskStatus.RUNNING:
            raise HTTPException(status_code=400, detail="Cannot cancel a running task")
        
        success = await delegation_service.update_task_status(
            task_id,
            TaskStatus.CANCELLED,
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel task")
        
        return BaseResponse(
            success=True,
            message=f"Task {task_id} cancelled",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel task {task_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/repositories/{owner}/{repo}/issues", response_model=List[GitHubIssue])
async def list_repository_issues(
    owner: str,
    repo: str,
    state: str = Query("open", pattern="^(open|closed|all)$"),
    labels: Optional[str] = Query(None, description="Comma-separated list of labels"),
):
    """
    List issues from a GitHub repository.
    
    This endpoint fetches issues from GitHub without delegating them,
    useful for previewing what would be delegated.
    
    Args:
        owner: Repository owner
        repo: Repository name
        state: Issue state (open, closed, all)
        labels: Comma-separated list of labels to filter by
        
    Returns:
        List of GitHub issues
    """
    try:
        github_service = GitHubService()
        repository = f"{owner}/{repo}"
        
        label_list = None
        if labels:
            label_list = [label.strip() for label in labels.split(",")]
        
        issues = await github_service.fetch_issues(
            repository=repository,
            state=state,
            labels=label_list,
        )
        
        return issues
    except Exception as e:
        logger.error(f"Failed to list repository issues: {e}")
        raise HTTPException(status_code=500, detail=str(e))
