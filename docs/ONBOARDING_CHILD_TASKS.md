# Onboarding Child Tasks — Final Index

This document maps the 12 onboarding child tasks created from the 6 parent epics.

## Access & Permissions (#87)
- [x] #96: Confirm GitHub/GCP access and roles — @kushin77
- [x] #97: Add Access Request template — @kushin77

## Local Dev Environment (#89)
- [x] #102: Document local setup and test commands — @kushin77
- [x] #103: Add devcontainer.json and docker-compose.dev.yml — @kushin77

## Secrets & IAM (#90)
- [x] #104: Rotate compromised token (CRITICAL) — @kushin77
- [x] #105: Migrate CI/runtime secrets to Google Secret Manager — @kushin77

## CI/CD & Tests (#88)
- [x] #106: Verify CI pipelines and add CI checklist — @kushin77
- [x] #107: Document test commands and add pytest workflow — @kushin77

## Docs & Readme (#92)
- [x] #108: Add docs-acknowledgement template and checklist — @kushin77
- [x] #109: Update README Quick Start with links to required docs — @kushin77

## Automation Scripts & Baseline Checks (#91)
- [x] #111: Add --help examples and docs for normalize_issues.py — @kushin77
- [x] #112: Document ci_monitoring.py usage and sample runs — @kushin77

## Priority Order for Execution
1. **CRITICAL:** #104 (Token rotation) — blocks all other security work
2. **HIGH:** #105 (GSM migration) — required for CI stability
3. **HIGH:** #106, #107 (CI/Tests validation) — ensure build pipeline works
4. **MEDIUM:** #108, #109 (Docs) — enable contributor onboarding
5. **MEDIUM:** #102, #103 (Local Dev) — enable local development
6. **LOW:** #96, #97 (Access templates) — access already in place
7. **LOW:** #111, #112 (Automation docs) — support tooling documentation

## Closed Issues (Duplicates)
- #98, #99, #100, #101 — closed as duplicates

---
**Last Updated:** 2026-01-29
**Created on branch:** feat/discovery-prototype
**Status:** All 12 child issues created and assigned to @kushin77
