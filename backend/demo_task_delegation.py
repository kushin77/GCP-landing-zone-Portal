#!/usr/bin/env python3
"""
Quick example demonstrating GitHub issue delegation to cloud tasks.

This script demonstrates the core functionality without requiring actual
GCP credentials or GitHub tokens.
"""
import asyncio
from datetime import datetime, timezone


async def demo_github_service():
    """Demonstrate GitHub service usage."""
    print("\n=== GitHub Service Demo ===\n")
    
    from services.github_service import GitHubService
    
    # Initialize service (no token for demo)
    service = GitHubService()
    print(f"✓ GitHub service initialized")
    print(f"  Base URL: {service.base_url}")
    print(f"  Has token: {bool(service.token)}")
    
    # In a real scenario, you would fetch issues like this:
    # issues = await service.fetch_issues("owner/repo", state="open")
    print("\nNote: Set GITHUB_TOKEN environment variable to fetch real issues")


async def demo_task_delegation():
    """Demonstrate task delegation service usage."""
    print("\n=== Task Delegation Service Demo ===\n")
    
    from services.task_delegation_service import TaskDelegationService
    from models.schemas import GitHubIssue
    
    # Initialize service
    service = TaskDelegationService()
    print(f"✓ Task delegation service initialized")
    print(f"  Project ID: {service.project_id}")
    print(f"  Location: {service.location}")
    print(f"  Queue: {service.queue_name}")
    
    # Create a mock GitHub issue
    mock_issue = GitHubIssue(
        number=1,
        title="Example: Implement feature X",
        body="This is a demonstration issue",
        state="open",
        labels=["feature", "demo"],
        assignees=["demo-user"],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        html_url="https://github.com/example/repo/issues/1",
        repository="example/repo",
    )
    
    print(f"\n✓ Mock issue created:")
    print(f"  #{mock_issue.number}: {mock_issue.title}")
    print(f"  Labels: {', '.join(mock_issue.labels)}")
    
    # In a real scenario, you would delegate issues like this:
    # tasks = await service.delegate_issues([mock_issue], auto_approve=False)
    print("\nNote: Configure GCP_PROJECT_ID to create real Cloud Tasks")


async def demo_api_usage():
    """Demonstrate API usage examples."""
    print("\n=== API Usage Examples ===\n")
    
    print("1. Delegate all open issues from a repository:")
    print("""
    curl -X POST http://localhost:8080/api/v1/task-delegation/delegate \\
      -H "Content-Type: application/json" \\
      -d '{
        "repository": "owner/repo",
        "auto_approve": false
      }'
    """)
    
    print("\n2. Delegate specific issues with auto-approval:")
    print("""
    curl -X POST http://localhost:8080/api/v1/task-delegation/delegate \\
      -H "Content-Type: application/json" \\
      -d '{
        "repository": "owner/repo",
        "issue_numbers": [1, 2, 3],
        "auto_approve": true
      }'
    """)
    
    print("\n3. List delegated tasks:")
    print("""
    curl "http://localhost:8080/api/v1/task-delegation/tasks?status=queued"
    """)
    
    print("\n4. Get task details:")
    print("""
    curl "http://localhost:8080/api/v1/task-delegation/tasks/{task_id}"
    """)
    
    print("\n5. Approve a pending task:")
    print("""
    curl -X POST "http://localhost:8080/api/v1/task-delegation/tasks/{task_id}/approve"
    """)


async def main():
    """Run all demos."""
    print("=" * 70)
    print("GitHub Issue Delegation to Cloud Tasks - Demo")
    print("=" * 70)
    
    await demo_github_service()
    await demo_task_delegation()
    await demo_api_usage()
    
    print("\n" + "=" * 70)
    print("For full documentation, see: docs/TASK_DELEGATION.md")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
