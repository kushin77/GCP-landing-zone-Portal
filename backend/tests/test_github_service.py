"""
Unit tests for GitHub service.
"""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from services.github_service import GitHubService
from models.schemas import GitHubIssue


@pytest.fixture
def mock_github_response():
    """Mock GitHub API response for issues."""
    return [
        {
            "number": 1,
            "title": "Test Issue 1",
            "body": "Test body 1",
            "state": "open",
            "labels": [{"name": "bug"}, {"name": "high-priority"}],
            "assignees": [{"login": "user1"}],
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-02T00:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/1",
        },
        {
            "number": 2,
            "title": "Test Issue 2",
            "body": "Test body 2",
            "state": "open",
            "labels": [{"name": "feature"}],
            "assignees": [],
            "created_at": "2024-01-03T00:00:00Z",
            "updated_at": "2024-01-04T00:00:00Z",
            "html_url": "https://github.com/owner/repo/issues/2",
        },
    ]


@pytest.mark.asyncio
async def test_fetch_all_issues(mock_github_response):
    """Test fetching all issues from a repository."""
    service = GitHubService(token="test-token")
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=mock_github_response)
        mock_response.raise_for_status = MagicMock()
        
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        issues = await service.fetch_issues("owner/repo")
        
        assert len(issues) == 2
        assert issues[0].number == 1
        assert issues[0].title == "Test Issue 1"
        assert issues[0].labels == ["bug", "high-priority"]
        assert issues[0].repository == "owner/repo"
        assert issues[1].number == 2


@pytest.mark.asyncio
async def test_fetch_specific_issues(mock_github_response):
    """Test fetching specific issues by number."""
    service = GitHubService(token="test-token")
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(side_effect=mock_github_response)
        mock_response.raise_for_status = MagicMock()
        
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        issues = await service.fetch_issues("owner/repo", issue_numbers=[1, 2])
        
        assert len(issues) == 2


@pytest.mark.asyncio
async def test_fetch_issues_with_labels(mock_github_response):
    """Test fetching issues with label filter."""
    service = GitHubService(token="test-token")
    
    # Filter response to only bug label
    filtered_response = [mock_github_response[0]]
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = MagicMock()
        mock_response.json = MagicMock(return_value=filtered_response)
        mock_response.raise_for_status = MagicMock()
        
        mock_get = AsyncMock(return_value=mock_response)
        mock_client.return_value.__aenter__.return_value.get = mock_get
        
        issues = await service.fetch_issues("owner/repo", labels=["bug"])
        
        assert len(issues) == 1
        assert issues[0].labels == ["bug", "high-priority"]


@pytest.mark.asyncio
async def test_update_issue_labels():
    """Test updating issue labels."""
    service = GitHubService(token="test-token")
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.put = AsyncMock(return_value=mock_response)
        
        result = await service.update_issue_labels("owner/repo", 1, ["bug", "delegated"])
        
        assert result is True


@pytest.mark.asyncio
async def test_add_issue_comment():
    """Test adding a comment to an issue."""
    service = GitHubService(token="test-token")
    
    with patch("httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
        
        result = await service.add_issue_comment("owner/repo", 1, "Test comment")
        
        assert result is True


@pytest.mark.asyncio
async def test_fetch_issues_no_token():
    """Test that service works without token (with warning)."""
    service = GitHubService()
    
    assert service.token is None
    assert "Authorization" not in service.headers


@pytest.mark.asyncio
async def test_parse_issue():
    """Test parsing GitHub API response into GitHubIssue model."""
    service = GitHubService()
    
    data = {
        "number": 1,
        "title": "Test",
        "body": "Body",
        "state": "open",
        "labels": [{"name": "bug"}],
        "assignees": [{"login": "user1"}],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-02T00:00:00Z",
        "html_url": "https://github.com/owner/repo/issues/1",
    }
    
    issue = service._parse_issue(data, "owner/repo")
    
    assert issue.number == 1
    assert issue.title == "Test"
    assert issue.body == "Body"
    assert issue.state == "open"
    assert issue.labels == ["bug"]
    assert issue.assignees == ["user1"]
    assert issue.repository == "owner/repo"
