# Backfill script

This folder contains a utility that consumes discovery output and prepares GitHub issue content for backfilling Portal entries.

Usage (dry-run):

```bash
python3 scripts/backfill/create_backfill_issues.py --source http://localhost:8080/api/v1/discovery/endpoints --dry-run
```

To actually create issues you must provide a `GITHUB_TOKEN` environment variable with least-privilege scope (repo:issues). The script is safe by default and requires `--create` to push changes.
