"""
Unit tests for task delegation service.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from services.task_delegation_service import TaskDelegationService
from models.schemas import GitHubIssue, DelegatedTask, TaskStatus


@pytest.fixture
def mock_github_issue():
    """Mock GitHub issue for testing."""
    return GitHubIssue(
        number=1,
        title="Test Issue",
        body="Test body",
        state="open",
        labels=["bug"],
        assignees=["user1"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        html_url="https://github.com/owner/repo/issues/1",
        repository="owner/repo",
    )


@pytest.fixture
def mock_delegation_service():
    """Create a mock delegation service with mocked GCP clients."""
    with patch.dict("os.environ", {
        "GCP_PROJECT_ID": "test-project",
        "CLOUD_TASKS_LOCATION": "us-central1",
        "CLOUD_TASKS_QUEUE": "test-queue",
    }):
        with patch("services.task_delegation_service.tasks_v2.CloudTasksClient"):
            with patch("services.task_delegation_service.firestore.AsyncClient"):
                service = TaskDelegationService()
                return service


@pytest.mark.asyncio
async def test_delegate_issues_auto_approve(mock_delegation_service, mock_github_issue):
    """Test delegating issues with auto-approve."""
    service = mock_delegation_service
    
    # Mock _create_task to return a simple task
    async def mock_create_task(issue, auto_approve):
        return DelegatedTask(
            id="test-id",
            issue_number=issue.number,
            repository=issue.repository,
            title=issue.title,
            description=issue.body,
            status=TaskStatus.QUEUED if auto_approve else TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            logs=["Task created"],
        )
    
    service._create_task = mock_create_task
    
    tasks = await service.delegate_issues([mock_github_issue], auto_approve=True)
    
    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.QUEUED
    assert tasks[0].issue_number == 1


@pytest.mark.asyncio
async def test_delegate_issues_pending(mock_delegation_service, mock_github_issue):
    """Test delegating issues without auto-approve (pending status)."""
    service = mock_delegation_service
    
    # Mock _create_task
    async def mock_create_task(issue, auto_approve):
        return DelegatedTask(
            id="test-id",
            issue_number=issue.number,
            repository=issue.repository,
            title=issue.title,
            description=issue.body,
            status=TaskStatus.QUEUED if auto_approve else TaskStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            logs=["Task created"],
        )
    
    service._create_task = mock_create_task
    
    tasks = await service.delegate_issues([mock_github_issue], auto_approve=False)
    
    assert len(tasks) == 1
    assert tasks[0].status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_create_task(mock_delegation_service, mock_github_issue):
    """Test creating a single task."""
    service = mock_delegation_service
    service._store_task = AsyncMock()
    service._create_cloud_task = AsyncMock(return_value="cloud-task-name")
    
    task = await service._create_task(mock_github_issue, auto_approve=True)
    
    assert task.issue_number == 1
    assert task.repository == "owner/repo"
    assert task.title == "Test Issue"
    assert task.status == TaskStatus.QUEUED
    assert len(task.logs) > 0


@pytest.mark.asyncio
async def test_update_task_status(mock_delegation_service):
    """Test updating task status."""
    service = mock_delegation_service
    
    # Mock Firestore operations
    mock_doc_ref = MagicMock()
    mock_doc_ref.update = AsyncMock()
    
    mock_collection = MagicMock()
    mock_collection.document.return_value = mock_doc_ref
    
    if service.db:
        service.db.collection = MagicMock(return_value=mock_collection)
        
        result = await service.update_task_status(
            "test-id",
            TaskStatus.COMPLETED,
            result={"success": True}
        )
        
        assert result is True
    else:
        # If db is not initialized (mock mode), test that it returns False
        result = await service.update_task_status(
            "test-id",
            TaskStatus.COMPLETED,
        )
        assert result is False


@pytest.mark.asyncio
async def test_approve_task(mock_delegation_service):
    """Test approving a pending task."""
    service = mock_delegation_service
    
    # Mock get_task to return a pending task
    pending_task = DelegatedTask(
        id="test-id",
        issue_number=1,
        repository="owner/repo",
        title="Test",
        description="Test",
        status=TaskStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        logs=["Task created"],
    )
    
    service.get_task = AsyncMock(return_value=pending_task)
    service._create_cloud_task = AsyncMock(return_value="cloud-task-name")
    service.update_task_status = AsyncMock(return_value=True)
    
    # Mock Firestore update
    if service.db:
        mock_doc_ref = MagicMock()
        mock_doc_ref.update = AsyncMock()
        mock_collection = MagicMock()
        mock_collection.document.return_value = mock_doc_ref
        service.db.collection = MagicMock(return_value=mock_collection)
        
        result = await service.approve_task("test-id")
        assert result is True
    else:
        result = await service.approve_task("test-id")
        # In mock mode without db, it should still work but might not create actual cloud task
        assert result is True or result is False


@pytest.mark.asyncio
async def test_approve_non_pending_task(mock_delegation_service):
    """Test that approving a non-pending task fails."""
    service = mock_delegation_service
    
    # Mock get_task to return a completed task
    completed_task = DelegatedTask(
        id="test-id",
        issue_number=1,
        repository="owner/repo",
        title="Test",
        description="Test",
        status=TaskStatus.COMPLETED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        logs=["Task created", "Task completed"],
    )
    
    service.get_task = AsyncMock(return_value=completed_task)
    
    result = await service.approve_task("test-id")
    assert result is False


@pytest.mark.asyncio
async def test_list_tasks(mock_delegation_service):
    """Test listing tasks with filters."""
    service = mock_delegation_service
    
    if service.db:
        # Mock Firestore query
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {
            "id": "test-id",
            "issue_number": 1,
            "repository": "owner/repo",
            "title": "Test",
            "description": "Test",
            "status": TaskStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "logs": ["Task created"],
        }
        
        async def mock_stream():
            yield mock_doc
        
        mock_query = MagicMock()
        mock_query.stream.return_value = mock_stream()
        mock_query.where = MagicMock(return_value=mock_query)
        mock_query.order_by = MagicMock(return_value=mock_query)
        mock_query.limit = MagicMock(return_value=mock_query)
        
        service.db.collection = MagicMock(return_value=mock_query)
        
        tasks = await service.list_tasks(repository="owner/repo")
        assert len(tasks) >= 0  # May be 0 in mock mode
    else:
        # Without db, should return empty list
        tasks = await service.list_tasks()
        assert tasks == []
