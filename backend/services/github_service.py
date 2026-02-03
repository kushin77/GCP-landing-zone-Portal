"""
GitHub service for fetching and managing issues.

This service integrates with the GitHub API to fetch issues from repositories
and prepare them for delegation to cloud tasks.
"""
import logging
import os
from datetime import datetime, timezone
from typing import List, Optional

import httpx
from models.schemas import GitHubIssue

logger = logging.getLogger(__name__)


class GitHubService:
    """Service for interacting with GitHub API."""

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub service.
        
        Args:
            token: GitHub personal access token. If not provided, reads from GITHUB_TOKEN env var.
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        if not self.token:
            logger.warning("No GitHub token provided. API rate limits will be very restrictive.")
        
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GCP-Landing-Zone-Portal"
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    async def fetch_issues(
        self,
        repository: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
        issue_numbers: Optional[List[int]] = None,
    ) -> List[GitHubIssue]:
        """
        Fetch issues from a GitHub repository.
        
        Args:
            repository: Repository in format "owner/repo"
            state: Issue state (open, closed, all)
            labels: Filter by labels
            issue_numbers: Specific issue numbers to fetch (if provided, other filters are ignored)
            
        Returns:
            List of GitHub issues
        """
        logger.info(f"Fetching issues from {repository} with state={state}, labels={labels}")
        
        # If specific issue numbers are provided, fetch them individually
        if issue_numbers:
            return await self._fetch_specific_issues(repository, issue_numbers)
        
        # Otherwise, fetch all issues matching the criteria
        return await self._fetch_all_issues(repository, state, labels)

    async def _fetch_specific_issues(
        self,
        repository: str,
        issue_numbers: List[int]
    ) -> List[GitHubIssue]:
        """Fetch specific issues by number."""
        issues = []
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for number in issue_numbers:
                try:
                    url = f"{self.base_url}/repos/{repository}/issues/{number}"
                    response = await client.get(url, headers=self.headers)
                    response.raise_for_status()
                    
                    data = response.json()
                    issue = self._parse_issue(data, repository)
                    issues.append(issue)
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to fetch issue #{number}: {e}")
                except Exception as e:
                    logger.error(f"Error fetching issue #{number}: {e}")
        
        return issues

    async def _fetch_all_issues(
        self,
        repository: str,
        state: str = "open",
        labels: Optional[List[str]] = None,
    ) -> List[GitHubIssue]:
        """Fetch all issues matching criteria."""
        issues = []
        page = 1
        per_page = 100
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            while True:
                try:
                    url = f"{self.base_url}/repos/{repository}/issues"
                    params = {
                        "state": state,
                        "per_page": per_page,
                        "page": page,
                    }
                    if labels:
                        params["labels"] = ",".join(labels)
                    
                    response = await client.get(url, headers=self.headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    if not data:
                        break
                    
                    # Filter out pull requests (they appear in issues endpoint)
                    for item in data:
                        if "pull_request" not in item:
                            issue = self._parse_issue(item, repository)
                            issues.append(issue)
                    
                    # Check if there are more pages
                    if len(data) < per_page:
                        break
                    
                    page += 1
                    
                except httpx.HTTPStatusError as e:
                    logger.error(f"Failed to fetch issues page {page}: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error fetching issues page {page}: {e}")
                    break
        
        logger.info(f"Fetched {len(issues)} issues from {repository}")
        return issues

    def _parse_issue(self, data: dict, repository: str) -> GitHubIssue:
        """Parse GitHub API response into GitHubIssue model."""
        return GitHubIssue(
            number=data["number"],
            title=data["title"],
            body=data.get("body"),
            state=data["state"],
            labels=[label["name"] for label in data.get("labels", [])],
            assignees=[assignee["login"] for assignee in data.get("assignees", [])],
            created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
            updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
            html_url=data["html_url"],
            repository=repository,
        )

    async def update_issue_labels(
        self,
        repository: str,
        issue_number: int,
        labels: List[str]
    ) -> bool:
        """
        Update labels on a GitHub issue.
        
        Args:
            repository: Repository in format "owner/repo"
            issue_number: Issue number
            labels: List of label names
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/repos/{repository}/issues/{issue_number}/labels"
                response = await client.put(
                    url,
                    headers=self.headers,
                    json={"labels": labels}
                )
                response.raise_for_status()
                logger.info(f"Updated labels for issue #{issue_number} in {repository}")
                return True
        except Exception as e:
            logger.error(f"Failed to update labels for issue #{issue_number}: {e}")
            return False

    async def add_issue_comment(
        self,
        repository: str,
        issue_number: int,
        comment: str
    ) -> bool:
        """
        Add a comment to a GitHub issue.
        
        Args:
            repository: Repository in format "owner/repo"
            issue_number: Issue number
            comment: Comment text
            
        Returns:
            True if successful, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/repos/{repository}/issues/{issue_number}/comments"
                response = await client.post(
                    url,
                    headers=self.headers,
                    json={"body": comment}
                )
                response.raise_for_status()
                logger.info(f"Added comment to issue #{issue_number} in {repository}")
                return True
        except Exception as e:
            logger.error(f"Failed to add comment to issue #{issue_number}: {e}")
            return False
