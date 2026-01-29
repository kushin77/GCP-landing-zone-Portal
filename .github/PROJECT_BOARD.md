# Project Board: Portal Program

This repository uses a GitHub Project board to track Portal work.

Recommended columns:
- Backlog
- Ready
- In Progress
- Review
- Blocked
- Done

Checklist to create the board (UI or `gh`):

UI: Repository → Projects → New project → Board (classic) → Name: "Portal Program"

gh CLI example:

```bash
# Create a classic project board
gh project create "Portal Program" --body "Program-level board for Portal work" --repo kushin77/GCP-landing-zone-Portal

# Add columns
gh api -X POST repos/kushin77/GCP-landing-zone-Portal/projects/{project_id}/columns -f name='Backlog'
gh api -X POST repos/kushin77/GCP-landing-zone-Portal/projects/{project_id}/columns -f name='Ready'
gh api -X POST repos/kushin77/GCP-landing-zone-Portal/projects/{project_id}/columns -f name='In Progress'
gh api -X POST repos/kushin77/GCP-landing-zone-Portal/projects/{project_id}/columns -f name='Review'
gh api -X POST repos/kushin77/GCP-landing-zone-Portal/projects/{project_id}/columns -f name='Blocked'
gh api -X POST repos/kushin77/GCP-landing-zone-Portal/projects/{project_id}/columns -f name='Done'
```

How to use:
- Create or link issues to the board and move cards across columns as work progresses.
- Use automation rules (if desired) to move cards on PR open/close.
- Assign `assignees` and `labels` in issues for filtering on the board.

Owners: PMO / Platform
