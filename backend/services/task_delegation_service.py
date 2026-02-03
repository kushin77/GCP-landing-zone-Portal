"""
Task delegation service for managing cloud-based task execution.

This service handles the delegation of GitHub issues to GCP Cloud Tasks,
tracking their status, and managing the task lifecycle.
"""
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from google.cloud import firestore, tasks_v2
from google.protobuf import duration_pb2, timestamp_pb2
from models.schemas import DelegatedTask, GitHubIssue, TaskStatus

logger = logging.getLogger(__name__)


class TaskDelegationService:
    """Service for delegating tasks to cloud execution."""

    def __init__(self):
        """Initialize task delegation service."""
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.location = os.getenv("CLOUD_TASKS_LOCATION", "us-central1")
        self.queue_name = os.getenv("CLOUD_TASKS_QUEUE", "github-issue-delegation")
        
        # Initialize Cloud Tasks client
        self.tasks_client = None
        try:
            self.tasks_client = tasks_v2.CloudTasksClient()
            self.queue_path = self.tasks_client.queue_path(
                self.project_id, self.location, self.queue_name
            )
            logger.info(f"Initialized Cloud Tasks client for queue: {self.queue_path}")
        except Exception as e:
            logger.warning(f"Cloud Tasks client initialization failed: {e}. Running in mock mode.")
        
        # Initialize Firestore for task tracking
        self.db = None
        try:
            self.db = firestore.AsyncClient()
            self.collection_name = "delegated_tasks"
            logger.info("Initialized Firestore client for task tracking")
        except Exception as e:
            logger.warning(f"Firestore client initialization failed: {e}. Task tracking disabled.")

    async def delegate_issues(
        self,
        issues: List[GitHubIssue],
        auto_approve: bool = False,
    ) -> List[DelegatedTask]:
        """
        Delegate GitHub issues to cloud tasks.
        
        Args:
            issues: List of GitHub issues to delegate
            auto_approve: If True, immediately queue tasks; otherwise mark as pending
            
        Returns:
            List of created delegated tasks
        """
        tasks = []
        
        for issue in issues:
            try:
                task = await self._create_task(issue, auto_approve)
                tasks.append(task)
            except Exception as e:
                logger.error(f"Failed to delegate issue #{issue.number}: {e}")
        
        logger.info(f"Delegated {len(tasks)} out of {len(issues)} issues")
        return tasks

    async def _create_task(
        self,
        issue: GitHubIssue,
        auto_approve: bool = False,
    ) -> DelegatedTask:
        """Create a delegated task for a GitHub issue."""
        task_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        
        # Determine initial status
        status = TaskStatus.QUEUED if auto_approve else TaskStatus.PENDING
        
        # Create task object
        task = DelegatedTask(
            id=task_id,
            issue_number=issue.number,
            repository=issue.repository,
            title=issue.title,
            description=issue.body,
            status=status,
            created_at=now,
            updated_at=now,
            logs=[f"{now.isoformat()} - Task created from GitHub issue #{issue.number}"],
        )
        
        # If auto-approved, create Cloud Task
        if auto_approve and self.tasks_client:
            try:
                cloud_task_name = await self._create_cloud_task(task)
                task.cloud_task_name = cloud_task_name
                task.logs.append(f"{now.isoformat()} - Cloud Task created: {cloud_task_name}")
            except Exception as e:
                logger.error(f"Failed to create Cloud Task: {e}")
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
        
        # Store in Firestore
        if self.db:
            try:
                await self._store_task(task)
            except Exception as e:
                logger.error(f"Failed to store task in Firestore: {e}")
        
        return task

    async def _create_cloud_task(self, task: DelegatedTask) -> str:
        """Create a Cloud Task for execution."""
        # Create the Cloud Task payload
        task_payload = {
            "task_id": task.id,
            "issue_number": task.issue_number,
            "repository": task.repository,
            "title": task.title,
            "description": task.description,
        }
        
        # Create the task
        cloud_task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": os.getenv("TASK_HANDLER_URL", "https://example.com/handle-task"),
                "headers": {
                    "Content-Type": "application/json",
                },
                "body": str(task_payload).encode(),
            }
        }
        
        # Set task execution time (immediate)
        schedule_time = timestamp_pb2.Timestamp()
        schedule_time.GetCurrentTime()
        cloud_task["schedule_time"] = schedule_time
        
        # Create the task
        response = self.tasks_client.create_task(
            request={
                "parent": self.queue_path,
                "task": cloud_task,
            }
        )
        
        logger.info(f"Created Cloud Task: {response.name}")
        return response.name

    async def _store_task(self, task: DelegatedTask) -> None:
        """Store task in Firestore."""
        doc_ref = self.db.collection(self.collection_name).document(task.id)
        await doc_ref.set(task.model_dump(mode="json"))

    async def get_task(self, task_id: str) -> Optional[DelegatedTask]:
        """Get a delegated task by ID."""
        if not self.db:
            logger.warning("Firestore not initialized, cannot fetch task")
            return None
        
        try:
            doc_ref = self.db.collection(self.collection_name).document(task_id)
            doc = await doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return DelegatedTask(**data)
            
            return None
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {e}")
            return None

    async def list_tasks(
        self,
        repository: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        limit: int = 100,
    ) -> List[DelegatedTask]:
        """
        List delegated tasks with optional filters.
        
        Args:
            repository: Filter by repository
            status: Filter by status
            limit: Maximum number of tasks to return
            
        Returns:
            List of delegated tasks
        """
        if not self.db:
            logger.warning("Firestore not initialized, returning empty list")
            return []
        
        try:
            query = self.db.collection(self.collection_name)
            
            # Apply filters
            if repository:
                query = query.where("repository", "==", repository)
            if status:
                query = query.where("status", "==", status.value)
            
            # Order by creation time and limit
            query = query.order_by("created_at", direction=firestore.Query.DESCENDING)
            query = query.limit(limit)
            
            # Execute query
            docs = query.stream()
            
            tasks = []
            async for doc in docs:
                data = doc.to_dict()
                tasks.append(DelegatedTask(**data))
            
            return tasks
        except Exception as e:
            logger.error(f"Failed to list tasks: {e}")
            return []

    async def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        error_message: Optional[str] = None,
        result: Optional[dict] = None,
    ) -> bool:
        """
        Update task status.
        
        Args:
            task_id: Task ID
            status: New status
            error_message: Error message if failed
            result: Task result if completed
            
        Returns:
            True if successful, False otherwise
        """
        if not self.db:
            logger.warning("Firestore not initialized, cannot update task")
            return False
        
        try:
            doc_ref = self.db.collection(self.collection_name).document(task_id)
            now = datetime.now(timezone.utc)
            
            update_data = {
                "status": status.value,
                "updated_at": now,
            }
            
            if status == TaskStatus.RUNNING:
                update_data["started_at"] = now
            elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                update_data["completed_at"] = now
            
            if error_message:
                update_data["error_message"] = error_message
            
            if result:
                update_data["result"] = result
            
            # Add log entry
            log_entry = f"{now.isoformat()} - Status changed to {status.value}"
            if error_message:
                log_entry += f": {error_message}"
            
            await doc_ref.update({
                **update_data,
                "logs": firestore.ArrayUnion([log_entry])
            })
            
            logger.info(f"Updated task {task_id} status to {status.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {e}")
            return False

    async def approve_task(self, task_id: str) -> bool:
        """
        Approve a pending task and queue it for execution.
        
        Args:
            task_id: Task ID
            
        Returns:
            True if successful, False otherwise
        """
        task = await self.get_task(task_id)
        if not task:
            logger.error(f"Task {task_id} not found")
            return False
        
        if task.status != TaskStatus.PENDING:
            logger.error(f"Task {task_id} is not in pending status")
            return False
        
        # Create Cloud Task
        if self.tasks_client:
            try:
                cloud_task_name = await self._create_cloud_task(task)
                
                # Update task status
                await self.update_task_status(
                    task_id,
                    TaskStatus.QUEUED,
                )
                
                # Update cloud task name
                doc_ref = self.db.collection(self.collection_name).document(task_id)
                await doc_ref.update({"cloud_task_name": cloud_task_name})
                
                return True
            except Exception as e:
                logger.error(f"Failed to approve task {task_id}: {e}")
                await self.update_task_status(
                    task_id,
                    TaskStatus.FAILED,
                    error_message=str(e),
                )
                return False
        else:
            logger.warning("Cloud Tasks client not initialized, marking as queued without actual task")
            await self.update_task_status(task_id, TaskStatus.QUEUED)
            return True
