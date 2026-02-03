# GitHub Issue Delegation to Cloud Tasks

## Overview

The Task Delegation feature enables automated delegation of GitHub issues to cloud-based autonomous execution. This system fetches issues from GitHub repositories and creates GCP Cloud Tasks for distributed, scalable, and autonomous task processing.

## Philosophy

This implementation follows key principles:
- **Autonomy**: Tasks execute independently with minimal human intervention
- **Best Practices**: Enterprise-grade error handling, logging, and monitoring
- **Thorough Testing**: Comprehensive test coverage for all components
- **Scalability**: Leverages GCP Cloud Tasks for distributed execution

## Architecture

```
┌─────────────────┐
│  GitHub Issues  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐      ┌──────────────────┐
│ GitHub Service  │─────▶│  Task Delegation │
│  (Fetch Issues) │      │     Service      │
└─────────────────┘      └────────┬─────────┘
                                  │
                         ┌────────┴────────┐
                         │                 │
                         ▼                 ▼
                  ┌─────────────┐   ┌──────────────┐
                  │ GCP Cloud   │   │  Firestore   │
                  │   Tasks     │   │  (Tracking)  │
                  └─────────────┘   └──────────────┘
```

## Features

### 1. Issue Fetching
- Fetch all open issues from a repository
- Filter by specific issue numbers
- Filter by labels
- Pagination support for large repositories
- Excludes pull requests automatically

### 2. Task Delegation
- Create Cloud Tasks for each issue
- Auto-approve mode for immediate execution
- Manual review mode (pending status)
- Task status tracking in Firestore
- Comprehensive logging

### 3. GitHub Integration
- Automatic label addition (`delegated`)
- Comment posting with task status
- Label updates for tracking
- Support for private repositories

### 4. Task Management
- List tasks with filters (repository, status)
- Get individual task details
- Approve pending tasks
- Cancel queued tasks
- Status updates (pending → queued → running → completed/failed)

## API Endpoints

### POST /api/v1/task-delegation/delegate

Delegate GitHub issues to cloud tasks.

**Request Body:**
```json
{
  "repository": "owner/repo",
  "issue_numbers": [1, 2, 3],
  "labels": ["bug", "high-priority"],
  "auto_approve": false
}
```

**Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "message": "Successfully delegated 3 issues",
  "tasks_created": 3,
  "tasks": [
    {
      "id": "uuid",
      "issue_number": 1,
      "repository": "owner/repo",
      "title": "Fix critical bug",
      "status": "pending",
      "created_at": "2024-01-15T10:30:00Z",
      "logs": ["Task created from GitHub issue #1"]
    }
  ]
}
```

### GET /api/v1/task-delegation/tasks

List delegated tasks with optional filters.

**Query Parameters:**
- `repository` (optional): Filter by repository (e.g., "owner/repo")
- `status` (optional): Filter by status (pending, queued, running, completed, failed, cancelled)
- `limit` (optional, default: 100): Maximum number of tasks to return

**Response:**
```json
[
  {
    "id": "uuid",
    "issue_number": 1,
    "repository": "owner/repo",
    "title": "Fix bug",
    "status": "queued",
    "created_at": "2024-01-15T10:30:00Z",
    "logs": ["Task created", "Task queued"]
  }
]
```

### GET /api/v1/task-delegation/tasks/{task_id}

Get details of a specific task.

**Response:**
```json
{
  "id": "uuid",
  "issue_number": 1,
  "repository": "owner/repo",
  "title": "Fix bug",
  "description": "Detailed issue description",
  "status": "running",
  "cloud_task_name": "projects/.../tasks/...",
  "created_at": "2024-01-15T10:30:00Z",
  "started_at": "2024-01-15T10:31:00Z",
  "logs": [
    "Task created from GitHub issue #1",
    "Cloud Task created",
    "Status changed to running"
  ]
}
```

### POST /api/v1/task-delegation/tasks/{task_id}/approve

Approve a pending task for execution.

**Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "message": "Task uuid approved and queued for execution"
}
```

### POST /api/v1/task-delegation/tasks/{task_id}/cancel

Cancel a pending or queued task.

**Response:**
```json
{
  "success": true,
  "timestamp": "2024-01-15T10:30:00Z",
  "message": "Task uuid cancelled"
}
```

### GET /api/v1/task-delegation/repositories/{owner}/{repo}/issues

List issues from a GitHub repository (preview mode).

**Query Parameters:**
- `state` (optional, default: "open"): Issue state (open, closed, all)
- `labels` (optional): Comma-separated list of labels

**Response:**
```json
[
  {
    "number": 1,
    "title": "Fix bug",
    "body": "Description",
    "state": "open",
    "labels": ["bug"],
    "assignees": ["user1"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "html_url": "https://github.com/owner/repo/issues/1",
    "repository": "owner/repo"
  }
]
```

## Configuration

### Environment Variables

Add the following to your `.env` file:

```bash
# GitHub Integration
GITHUB_TOKEN=ghp_your_personal_access_token

# GCP Cloud Tasks
GCP_PROJECT_ID=your-gcp-project
CLOUD_TASKS_LOCATION=us-central1
CLOUD_TASKS_QUEUE=github-issue-delegation
TASK_HANDLER_URL=https://your-handler.run.app/handle-task
```

### GitHub Token Setup

1. Go to GitHub Settings → Developer settings → Personal access tokens
2. Generate new token (classic) with scopes:
   - `repo` (for private repositories)
   - `public_repo` (for public repositories only)
3. Copy token and add to `.env` file

### Cloud Tasks Setup

1. Enable Cloud Tasks API:
   ```bash
   gcloud services enable cloudtasks.googleapis.com
   ```

2. Create a Cloud Tasks queue:
   ```bash
   gcloud tasks queues create github-issue-delegation \
     --location=us-central1 \
     --max-dispatches-per-second=10 \
     --max-concurrent-dispatches=100
   ```

3. Deploy a task handler service (Cloud Run, Cloud Functions, etc.)

### Firestore Setup

1. Enable Firestore API:
   ```bash
   gcloud services enable firestore.googleapis.com
   ```

2. Create Firestore database (if not already created):
   ```bash
   gcloud firestore databases create --region=us-central1
   ```

3. The service automatically creates the `delegated_tasks` collection.

## Task Lifecycle

```
┌─────────┐
│ PENDING │ (Initial state for manual review)
└────┬────┘
     │ approve()
     ▼
┌─────────┐
│ QUEUED  │ (Cloud Task created)
└────┬────┘
     │ Cloud Tasks dispatcher
     ▼
┌─────────┐
│ RUNNING │ (Task executing)
└────┬────┘
     │
     ├─▶ ┌───────────┐
     │   │ COMPLETED │ (Success)
     │   └───────────┘
     │
     └─▶ ┌─────────┐
         │ FAILED  │ (Error)
         └─────────┘

(cancel() available from PENDING and QUEUED states)
```

## Usage Examples

### Example 1: Delegate All Open Issues

```bash
curl -X POST http://localhost:8080/api/v1/task-delegation/delegate \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "kushin77/ElevatedIQ-Mono-Repo",
    "auto_approve": false
  }'
```

### Example 2: Auto-Approve High-Priority Bugs

```bash
curl -X POST http://localhost:8080/api/v1/task-delegation/delegate \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "kushin77/ElevatedIQ-Mono-Repo",
    "labels": ["bug", "high-priority"],
    "auto_approve": true
  }'
```

### Example 3: Delegate Specific Issues

```bash
curl -X POST http://localhost:8080/api/v1/task-delegation/delegate \
  -H "Content-Type: application/json" \
  -d '{
    "repository": "kushin77/ElevatedIQ-Mono-Repo",
    "issue_numbers": [1, 5, 10],
    "auto_approve": true
  }'
```

### Example 4: List Tasks for Repository

```bash
curl "http://localhost:8080/api/v1/task-delegation/tasks?repository=kushin77/ElevatedIQ-Mono-Repo&status=queued"
```

### Example 5: Approve a Pending Task

```bash
curl -X POST http://localhost:8080/api/v1/task-delegation/tasks/uuid-here/approve
```

## Testing

### Unit Tests

```bash
cd backend
pytest tests/test_github_service.py -v
pytest tests/test_task_delegation_service.py -v
```

### Integration Tests

```bash
# Set up test environment variables
export GITHUB_TOKEN=test-token
export GCP_PROJECT_ID=test-project

# Run integration tests
pytest tests/test_task_delegation_service.py -v -m integration
```

### Manual Testing

1. Start the development server:
   ```bash
   ./run.sh dev
   ```

2. Test issue fetching:
   ```bash
   curl "http://localhost:8080/api/v1/task-delegation/repositories/owner/repo/issues"
   ```

3. Test delegation:
   ```bash
   curl -X POST http://localhost:8080/api/v1/task-delegation/delegate \
     -H "Content-Type: application/json" \
     -d '{"repository": "owner/repo", "auto_approve": false}'
   ```

## Monitoring

### Logs

All operations are logged with structured logging:

```
2024-01-15T10:30:00 - services.github_service - INFO - [req-123] - Fetching issues from owner/repo
2024-01-15T10:30:01 - services.task_delegation_service - INFO - [req-123] - Delegated 5 out of 5 issues
```

### Metrics

Key metrics to monitor:
- Task creation rate
- Task completion rate
- Task failure rate
- Average task duration
- Cloud Tasks queue depth

### Health Checks

The task delegation service is integrated with the portal's health check system:

```bash
curl http://localhost:8080/health
```

## Security Considerations

1. **GitHub Token Security**:
   - Store in Google Secret Manager (not in .env for production)
   - Use minimal required scopes
   - Rotate regularly

2. **Cloud Tasks Authentication**:
   - Use Workload Identity for GCP authentication
   - Ensure task handler validates requests
   - Use HTTPS only

3. **Firestore Security**:
   - Configure appropriate IAM roles
   - Use security rules to restrict access
   - Enable audit logging

4. **Rate Limiting**:
   - GitHub API has rate limits (5000 requests/hour with token)
   - Cloud Tasks has quota limits
   - Implement appropriate backoff strategies

## Troubleshooting

### Issue: GitHub API rate limit exceeded

**Solution**: Ensure `GITHUB_TOKEN` is configured. Unauthenticated requests have a limit of 60/hour.

### Issue: Cloud Tasks creation fails

**Solution**: 
1. Verify Cloud Tasks API is enabled
2. Check IAM permissions for service account
3. Ensure queue exists: `gcloud tasks queues describe github-issue-delegation --location=us-central1`

### Issue: Tasks not appearing in Firestore

**Solution**:
1. Verify Firestore is initialized
2. Check service account permissions
3. Review application logs for errors

### Issue: Tasks stuck in queued state

**Solution**:
1. Verify task handler URL is correct
2. Check task handler is deployed and healthy
3. Review Cloud Tasks logs: `gcloud tasks queues describe github-issue-delegation --location=us-central1`

## Future Enhancements

- [ ] Support for GitHub webhooks (real-time delegation)
- [ ] Advanced filtering (assignees, milestones, projects)
- [ ] Task prioritization and scheduling
- [ ] Retry policies for failed tasks
- [ ] Task execution timeout configuration
- [ ] Integration with GitHub Actions
- [ ] Dashboard UI for task management
- [ ] Notification system (email, Slack, etc.)
- [ ] Batch operations (approve/cancel multiple tasks)
- [ ] Task templates for common workflows

## Support

For issues or questions:
1. Check the logs: `docker-compose logs -f backend`
2. Review this documentation
3. Check existing GitHub issues
4. Contact the platform team

## License

This feature is part of the GCP Landing Zone Portal and follows the same license.
