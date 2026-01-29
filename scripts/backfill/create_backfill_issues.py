#!/usr/bin/env python3
"""Create GitHub issues for discovered endpoints missing owners or requiring onboarding.

Safe defaults (dry-run). Requires `GITHUB_TOKEN` to actually create issues.
"""
import argparse
import os
import sys
from typing import List

import requests

ISSUE_TEMPLATE = """
Backfill: Onboard endpoint `{name}`

Detected resource: {id}

Type: {type}
Project: {project}
Public DNS: {public_dns}
Owner: {owner}

Action: Please confirm owner and add onboarding details.
"""


def fetch_endpoints(source: str):
    r = requests.get(source, timeout=10)
    r.raise_for_status()
    return r.json()


def make_issue_body(item: dict) -> str:
    return ISSUE_TEMPLATE.format(
        name=item.get("name"),
        id=item.get("id"),
        type=item.get("type"),
        project=item.get("id", "").split("/")[1] if "/" in item.get("id", "") else "",
        public_dns=item.get("public_dns") or "",
        owner=item.get("owner") or "(unassigned)",
    )


def create_issue(repo: str, title: str, body: str, token: str):
    url = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}", "Accept": "application/vnd.github+json"}
    payload = {"title": title, "body": body, "labels": ["backfill"]}
    r = requests.post(url, json=payload, headers=headers, timeout=10)
    r.raise_for_status()
    return r.json()


def main(argv: List[str]):
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Discovery endpoint or JSON file path")
    parser.add_argument(
        "--repo", default="kushin77/GCP-landing-zone-Portal", help="GitHub repo to open issues in"
    )
    parser.add_argument(
        "--dry-run", action="store_true", default=True, help="Show payloads but don't create issues"
    )
    parser.add_argument(
        "--create", action="store_true", help="Create issues (requires GITHUB_TOKEN)"
    )
    args = parser.parse_args(argv)

    if args.source.startswith("http"):
        items = fetch_endpoints(args.source)
    else:
        # assume local JSON file
        import json

        with open(args.source, "r") as f:
            items = json.load(f)

    token = os.getenv("GITHUB_TOKEN")

    to_create = []
    for item in items:
        # Identify candidates: missing owner or public_dns
        if not item.get("owner") or not item.get("public_dns"):
            title = f"Backfill: Onboard endpoint {item.get('name')}"
            body = make_issue_body(item)
            to_create.append((title, body))

    if not to_create:
        print("No backfill candidates found.")
        return

    for title, body in to_create:
        print("---\nTitle:\n", title)
        print("Body:\n", body)
        if args.create:
            if not token:
                print("GITHUB_TOKEN required to create issues. Set env var and retry.")
                sys.exit(1)
            resp = create_issue(args.repo, title, body, token)
            print(f"Created issue: {resp.get('html_url')}")


if __name__ == "__main__":
    main(sys.argv[1:])
