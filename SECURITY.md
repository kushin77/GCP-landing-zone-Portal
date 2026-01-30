# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability, **do NOT** create a public GitHub issue.

Instead:
1. Email security@landing-zone-portal.io with details
2. Include: affected version, impact, proof of concept
3. **Do NOT** disclose publicly until patch is released
4. We will acknowledge receipt within 24 hours
5. We aim to release patches within 48 hours for critical issues

## Security Standards

### Authentication & Authorization
- ✅ OAuth 2.0 with MFA (hardware keys preferred)
- ✅ Identity-Aware Proxy (IAP) for all endpoints
- ✅ Service account authentication via Workload Identity (no JSON keys)
- ✅ Role-based access control (RBAC) with least privilege
- ✅ Session timeout: 30 minutes inactivity
- ✅ All auth events logged and monitored

### Data Security
- ✅ Encryption at rest using Customer-Managed Keys (CMEK)
- ✅ Encryption in transit via TLS 1.3
- ✅ Database audit logging enabled (Cloud Audit Logs)
- ✅ Data residency: Multi-region within US (configurable)
- ✅ Backups encrypted with CMEK
- ✅ PII data minimization (collect only necessary data)
- ✅ Data retention policies enforced (see Compliance docs)

### Secret Management
- ✅ All secrets stored in Secret Manager (encrypted, access controlled)
- ✅ No secrets in code, environment variables, or logs
- ✅ Automatic secret rotation (90-day max lifetime)
- ✅ Secrets accessed via Workload Identity (not files)
- ✅ All secret access audited

### Vulnerability Management
- ✅ Dependency scanning (Snyk) on every commit
- ✅ Container image scanning before deployment
- ✅ Code scanning (SAST) on all PRs
- ✅ Patch critical/high vulnerabilities within 48 hours
- ✅ Quarterly penetration testing
- ✅ Bug bounty program active

### Network Security
- ✅ Private network by default (no public IPs)
- ✅ VPC Service Controls for boundary protection
- ✅ Cloud Armor DDoS protection on all endpoints
- ✅ WAF rules for API protection
- ✅ VPC Flow Logs enabled and monitored
- ✅ No internet routing except via Cloud NAT (egress only)

### Infrastructure Security
- ✅ Infrastructure as Code (Terraform) reviewed before deployment
- ✅ Cloud KMS for key management (CMEK)
- ✅ OS Login required (no SSH keys in metadata)
- ✅ Serial port access disabled
- ✅ VM instances have minimal attack surface (no packages except essentials)
- ✅ Cloud Armor on all public endpoints
- ✅ Binary Authorization for container deployments

### Compliance & Audit
- ✅ NIST 800-53 controls implemented (IA-2, AC-2, SC-7, SC-28, AU-2, SI-4)
- ✅ FedRAMP Moderate baseline ready
- ✅ SOC 2 Type II audit trail
- ✅ All administrative actions logged to Cloud Audit Logs
- ✅ 7-year log retention
- ✅ Real-time alerting for suspicious activity

### Development Security
- ✅ Code review required for all changes (2+ approvers)
- ✅ Automated security scanning on PRs (SAST, dependency scanning)
- ✅ Pre-commit hooks (secret scanning, linting)
- ✅ GPG-signed commits required
- ✅ No hardcoded secrets or credentials
- ✅ Secrets only via environment variables or Secret Manager

### Incident Response
- ✅ Incident response plan documented and tested quarterly
- ✅ 24/7 on-call security team via PagerDuty
- ✅ <5 minute detection-to-alert SLA
- ✅ <1 hour containment SLA for critical incidents
- ✅ Post-mortem and lessons learned documented
- ✅ All incidents tracked and reported to Hub platform

## Security Checklist for Contributors

Before submitting a PR, verify:

- [ ] No secrets in code (API keys, passwords, credentials)
- [ ] No hardcoded IPs or configuration
- [ ] All inputs validated and sanitized
- [ ] All outputs properly encoded/escaped
- [ ] Error messages don't leak sensitive information
- [ ] Logging doesn't capture secrets or PII
- [ ] Type checking enabled (TypeScript strict mode)
- [ ] CORS policy is restrictive
- [ ] Dependency versions pinned
- [ ] Dependency licenses reviewed
- [ ] Security headers included (CSP, HSTS, X-Frame-Options)
- [ ] Rate limiting implemented where applicable
- [ ] Tests include security scenarios
- [ ] Snyk scan passes with no high/critical vulnerabilities
- [ ] Commit is GPG signed
- [ ] PR includes security impact assessment (in description)

## Security Headers

All HTTP responses include:

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), microphone=(), camera=()
```

## Dependency Management

### Frontend Dependencies
- Review Snyk advisories on every dependency bump
- Use npm audit to check for vulnerabilities
- Pin versions in package-lock.json
- Audit licenses (no GPL in production code)

### Backend Dependencies
- Review Snyk advisories on every dependency bump
- Use pip-audit to check for vulnerabilities
- Pin versions in requirements.txt
- Audit licenses

### Dependency Updates
- Update dependencies monthly (security updates)
- Update major versions quarterly (with testing)
- All updates go through PR review and security scanning

## DDoS & Rate Limiting

- Cloud Armor enabled with rate limiting (100 req/min per IP)
- Captcha challenge for suspicious traffic
- Bot detection enabled
- Geographic restrictions (if applicable)

## Data Privacy

- GDPR compliant (if processing EU resident data)
- CCPA compliant (if processing CA resident data)
- Data retention policies enforced
- Right to erasure implemented
- Privacy policy available at `/privacy`

## Third-Party Services

Approved third-party services (security-reviewed):

- **GCP Services**: Cloud Run, Firestore, Secret Manager, Cloud KMS, IAP, Cloud Armor
- **Monitoring**: Google Cloud Monitoring (proprietary)
- **Logging**: Google Cloud Logging (proprietary)
- **Authentication**: Google Identity, OAuth 2.0
- **Dependency Scanning**: Snyk
- **Code Scanning**: Cloud Code, Cloud Build

All third-party services have data processing agreements in place.

## Security Training

All contributors must:
- ✅ Complete security awareness training (annual)
- ✅ Review OWASP Top 10 (annual)
- ✅ Understand company security policies
- ✅ Know incident reporting procedures

## Questions?

- 📖 See SECURITY.md in this repo
- 📧 Email security@landing-zone-portal.io
- 📞 Ask @platform-engineering

---

**Last Updated**: 2026-01-18
**Next Review**: 2026-04-18
