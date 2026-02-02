# Landing Zone PMO Enforcement Gates

**Document Version**: 1.0
**Last Updated**: 2026-01-26
**Owner**: Platform Engineering
**Status**: Operational

---

## Overview

This document defines the mandatory PMO enforcement gates that all spoke repositories (including GCP-landing-zone-Portal) must pass before onboarding to the Landing Zone hub. These gates ensure compliance with the Mandatory Cleanup Policy and governance standards.

---

## Enforcement Gates Summary

| Gate | Phase | Severity | Blocks Onboarding | Validation | Status |
|------|-------|----------|-------------------|-----------|--------|
| Phase 1: Structural Cleanup | 1 | Medium | ❌ No | `scripts/validation/validate-repo.sh` | ✅ PASS |
| Phase 2: Documentation | 2 | Medium | ✅ YES | 4 canonical docs required | ✅ PASS |
| Phase 3: Security & GPG | 3 | High | ✅ YES | 100% commit signing | ⚠️ PENDING |
| Phase 4: 5-Layer Folder Depth | 4 | High | ✅ YES | `scripts/validation/folder-hierarchy-validation.sh` | ✅ PASS |
| Phase 5: Governance & Evidence | 5 | Medium | ❌ No | pmo.yaml + conventional commits | ✅ PASS |

---

## Gate Details

### Phase 1: Structural Cleanup ✅ PASS

**Purpose**: Ensure repository hygiene and enforce size constraints

**Requirements**:
- Repository size must be < 500KB
- No `.bak`, `.old`, or orphaned artifact files
- No commented-out code bloat
- All external dependencies pinned (versions specified)
- No build artifacts or temporary files in version control

**Validation**:
```bash
bash scripts/validation/validate-repo.sh
```

**Current Status**: ✅ **PASSED**
- Repository size: 440KB (compliant)
- Gitleaks findings: 0
- All dependencies pinned in `requirements.txt` and `package.json`

---

### Phase 2: Documentation Consolidation ✅ PASS

**Purpose**: Mandate canonical documentation for all infrastructure components

**Required Documents**:

1. **`API.md`** - REST/gRPC API reference
   - Authentication & JWT token management
   - All endpoints with request/response examples
   - Error handling and status codes
   - Rate limiting and versioning strategy
   - Integration examples (cURL, Python)

2. **`ARCHITECTURE.md`** - System design and 5-layer overview
   - Foundation through Observability layers
   - Component architecture diagram
   - Technology stack rationale
   - 3+ architectural decision records (ADRs)
   - Scalability and HA considerations
   - Security posture analysis

3. **`DEPLOYMENT.md`** - Terraform layer deployment guide
   - Layer-by-layer deployment instructions
   - Deployment order and dependencies
   - Environment configuration (dev, staging, prod)
   - CI/CD integration with Cloud Build
   - Troubleshooting and rollback procedures

4. **`RUNBOOKS.md`** - Operational playbooks
   - P1/P2 incident response procedures
   - Disaster recovery with RTO/RPO targets
   - Routine maintenance schedules
   - Standard and canary deployment procedures
   - Troubleshooting guide for common issues

**Validation**:
```bash
test -f API.md && test -f ARCHITECTURE.md && test -f DEPLOYMENT.md && test -f RUNBOOKS.md && echo "✅ All 4 canonical docs present"
```

**Current Status**: ✅ **PASSED**
- All 4 canonical documents created and present
- Each document meets content requirements

---

### Phase 3: Security & GPG Signing ⚠️ PENDING

**Purpose**: Enforce security scanning and cryptographic commit verification

**Requirements**:
- Gitleaks secret scanning: 0 findings
- Private key detection: enabled
- Pre-commit hooks: enforced
- **GPG Commit Signing**: 100% of commits in last 50 must be signed
- All commits include commit signatures (`git log --pretty=format:"%G?"`  shows 'G')

**Pre-commit Hook Coverage**:

| Hook | Purpose | Enforced |
|------|---------|----------|
| `conventional-commits` | Enforce conventional commit messages (feat:, fix:, etc.) | ✅ Yes |
| `gitleaks` | Detect and prevent secrets in code | ✅ Yes |
| `detect-private-key` | Detect private key credentials | ✅ Yes |
| `end-of-file-fixer` | Ensure files end with newline | ✅ Yes |
| `trailing-whitespace` | Remove trailing whitespace | ✅ Yes |
| `black` | Python code formatting | ✅ Yes |
| `isort` | Python import sorting | ✅ Yes |
| `flake8` | Python linting | ✅ Yes |
| `eslint` | JavaScript/TypeScript linting | ✅ Yes |
| `prettier` | JS/TS/JSON formatting | ✅ Yes |
| `tflint` | Terraform linting | ✅ Yes |

**Validation**:
```bash
# Check gitleaks
gitleaks detect --verbose

# Verify commit signatures
git log --pretty=format:"%h %G? %s" | head -50

# Run pre-commit hooks
pre-commit run --all-files
```

**Current Status**: ⚠️ **PENDING - PARTIALLY IMPLEMENTED**
- ✅ Gitleaks scan: 0 findings
- ✅ Private key detection: enabled
- ✅ Pre-commit hooks: configured and functional
- ⚠️ **GPG Commit Signing**: Partially implemented (some commits signed, 53 unsigned commits in history)

**To Complete This Gate**:
```bash
# 1. Verify GPG key is properly configured
gpg --list-keys

# 2. Ensure signing key is set
git config user.signingkey

# 3. For future commits, signing is enabled
git config commit.gpgsign

# 4. To sign existing commits (requires force push - use with caution)
# git rebase --exec 'git commit --amend --no-edit -S' <commit-range>
```

**Note**: GPG signing is enabled for new commits. Historical commits may remain unsigned as amending would require force push to shared repository.

# 3. Force push with signatures
git push --force-with-lease origin main

# 4. Verify all commits are signed
git log --pretty=format:"%h %G? %s" | head -10
```

---

### Phase 4: 5-Layer Folder Depth Mandate ✅ PASS

**Purpose**: Enforce standard Terraform organization pattern for scalability and governance

**Required Structure**:

```
terraform/
├── 01-foundation/      [BOOTSTRAP + ORG + CI/CD]
│   └── main.tf, variables.tf, outputs.tf
├── 02-network/         [VPC, SUBNETS, FIREWALL, NAT]
│   ├── vpc/
│   ├── firewall/
│   └── nat/
├── 03-security/        [IAM, SECRETS, KMS, COMPLIANCE]
│   ├── iam/
│   ├── secrets/
│   └── compliance/
├── 04-workloads/       [APPLICATIONS, SERVICES, DATABASES]
│   ├── api/
│   ├── frontend/
│   ├── database/
│   └── services/
├── 05-observability/   [MONITORING, LOGGING, ALERTING]
│   ├── monitoring/
│   ├── logging/
│   └── alerting/
└── modules/            [REUSABLE COMPONENTS]
    ├── network/
    ├── security/
    └── compute/
```

**Scripts Organization** (8 required categories):

```
scripts/
├── automation/         [CI/CD orchestration]
├── bootstrap/          [Initial setup & provisioning]
├── deployment/         [Deploy scripts & procedures]
├── lib/                [Shared libraries & utilities]
├── maintenance/        [Cleanup, optimization]
├── monitoring/         [Observability & health checks]
├── security/           [Scans, audits, compliance]
└── validation/         [Checks, tests, validation]
    ├── folder-hierarchy-validation.sh
    ├── terraform/
    │   └── hcl-syntax-check.sh
    └── validate-repo.sh
```

**Validation**:
```bash
bash scripts/validation/folder-hierarchy-validation.sh
```

**Current Status**: ✅ **PASSED**
- All 5 Terraform layers present with correct naming
- Modules directory created
- All 8 script categories organized
- Validation script passes

---

### Phase 5: Governance & Evidence ✅ PASS

**Purpose**: Ensure governance tracking and decision audit trail

**Requirements**:
- `pmo.yaml` exists with complete governance metadata
- Conventional commit messages enforced (`feat:`, `fix:`, `docs:`, etc.)
- Session logging enabled in Git history
- GitHub issue tracking for all changes
- Compliance tier and NIST controls documented

**pmo.yaml Requirements**:
```yaml
project:
  name: "[Project Name]"
  repository: "[GitHub URL]"

ownership:
  owner: "[Team Name]"
  owner_email: "[Team Email]"

governance:
  compliance_tier: "[tier-1|tier-2|tier-3]"
  nist_controls: [list of controls]

pmo_mandates:
  [all 5 phases documented]

enforcement_gates:
  [all gates with validation rules]
```

**Validation**:
```bash
# Check pmo.yaml exists
test -f pmo.yaml && echo "✅ pmo.yaml present"

# Check conventional commits in pre-commit config
grep -q "conventional-commits" .pre-commit-config.yaml && echo "✅ Conventional commits enforced"

# Check commit history
git log --oneline | head -10
```

**Current Status**: ✅ **PASSED**
- pmo.yaml exists with complete governance metadata
- Conventional commits enforced via pre-commit hooks
- Git history captures all decisions
- NIST controls documented (IA-2, AC-2, SC-7, SC-28, AU-2, SI-4)

---

## Onboarding Checklist

Before submitting to the hub for onboarding, complete the following:

- [ ] **Phase 1**: Run `scripts/validation/validate-repo.sh` - must pass
- [ ] **Phase 2**: Verify all 4 canonical docs exist (API.md, ARCHITECTURE.md, DEPLOYMENT.md, RUNBOOKS.md)
- [ ] **Phase 3**: Sign all commits with GPG and verify `git log --pretty=format:"%h %G? %s"` shows 'G' for all commits
- [ ] **Phase 4**: Run `scripts/validation/folder-hierarchy-validation.sh` - must pass
- [ ] **Phase 5**: Verify `pmo.yaml` exists and contains all required fields
- [ ] **Final Validation**: Run `pre-commit run --all-files` with zero failures
- [ ] **Hub Integration**: Verify `.pre-commit-config.yaml` includes all hub enforcement hooks
- [ ] **Approval**: Obtain written approval from Platform Engineering team
- [ ] **PR Opening**: Create onboarding PR with complete checklist attached

---

## Validation Commands

Run these commands locally before submitting for onboarding:

```bash
# 1. Validate repository structure
bash scripts/validation/validate-repo.sh

# 2. Validate folder hierarchy
bash scripts/validation/folder-hierarchy-validation.sh

# 3. Check for secrets
gitleaks detect --verbose

# 4. Verify commit signatures
git log --pretty=format:"%h %G? %s" | head -50

# 5. Run all pre-commit hooks
pre-commit run --all-files

# 6. Validate Terraform syntax
terraform validate

# 7. Check pmo.yaml
test -f pmo.yaml && echo "✅ pmo.yaml present"
```

---

## Exemption Policy

**Exception requests** may be granted for specific mandates under the following conditions:

- **Approval Level**: CTO authorization required
- **Valid Reasons**:
  - Security risk with compliance
  - Critical business timeline pressure
  - Technical infeasibility with documented justification

- **Duration**: Maximum 90 days from approval date
- **Tracking**: All exemptions logged in `docs/governance/EXEMPTION_LOG.md`
- **Template**: [EXEMPTION_REQUEST_TEMPLATE.md](docs/governance/templates/EXEMPTION_REQUEST_TEMPLATE.md)

**To Request an Exemption**:
1. Document the specific mandate and reason for waiver
2. Fill out exemption request template
3. Submit to platform-eng@example.com with escalation to CTO
4. Log approval and expiration date in exemption log

---

## Enforcement Timeline

| Date | Milestone | Status |
|------|-----------|--------|
| 2026-01-19 | Enforcement audit completed | ✅ Complete |
| 2026-01-20 | Documentation & folder structure remediation | ✅ Complete |
| 2026-01-21 | GPG commit signing & final validation | 🔄 In Progress |
| 2026-01-22 | Onboarding PR submission | ⏳ Pending |
| 2026-01-23 | Hub review and approval | ⏳ Pending |
| 2026-01-24 | Spoke onboarding complete | ⏳ Pending |

---

## References

- **pmo.yaml** - Complete PMO mandate definitions
- **LANDING_ZONE_ENFORCEMENT_AUDIT.md** - Detailed audit findings
- **PRE_ONBOARDING_CHECKLIST.md** - Step-by-step completion guide
- **Mandatory Cleanup Policy** - Hub governance standards

---

## Contact & Support

**Questions about enforcement gates?**
- Slack: #platform-engineering
- Email: platform-eng@example.com
- Escalation: CTO (for mandate waivers)

**Document Review Cycle**: Quarterly
**Last Reviewed**: 2026-01-26
**Next Review**: 2026-04-26
