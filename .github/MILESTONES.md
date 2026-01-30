# Milestones

Create these Milestones in the repository to track program phases.

Recommended milestones:

- Discovery — Goals: gather requirements, inventory endpoints, define scope. Estimate: 2 weeks.
- Hardening — Goals: security remediations, secret migration, CI hardening. Estimate: 2-4 weeks.
- Integration — Goals: integrate observability, CI/CD gates, dev DX. Estimate: 2-4 weeks.
- Rollout — Goals: promote to staging/production, runbooks, SLOs. Estimate: 1-2 weeks.
- Compliance — Goals: documentation, audits, sign-offs. Estimate: 1 week.

How to create (UI): Repository → Issues → Milestones → New milestone

gh CLI example:

```bash
gh milestone create "Discovery" --repo kushin77/GCP-landing-zone-Portal --description "Gather requirements and inventory endpoints"
gh milestone create "Hardening" --repo kushin77/GCP-landing-zone-Portal --description "Security remediations, secret migration, CI hardening"
gh milestone create "Integration" --repo kushin77/GCP-landing-zone-Portal --description "Integrate observability and CI/CD gates"
gh milestone create "Rollout" --repo kushin77/GCP-landing-zone-Portal --description "Promotion to staging/production and runbooks"
gh milestone create "Compliance" --repo kushin77/GCP-landing-zone-Portal --description "Documentation and audits"
```

Usage:
- Assign issues to milestones when they belong to a program phase.
- Use milestone due dates for planning and delivery tracking.
