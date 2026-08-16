# Security Policy

## Reporting a Vulnerability

**DO NOT** open a public issue for security vulnerabilities.

Instead, report directly to:
- **Telegram:** [@LightYagami28](https://t.me/LightYagami28)
- **Email:** ceo@retechrevive.it

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will respond within 48 hours and work on a fix immediately.

## Security Features

- ✅ No shell injection vulnerabilities (subprocess.run with argument lists)
- ✅ Input validation on all user inputs
- ✅ Path traversal protection (Path.resolve + relative_to validation)
- ✅ Docker resource isolation (memory/CPU limits)
- ✅ Non-root execution in containers
- ✅ Comprehensive logging and audit trail

## Supported Versions

| Version | Status | Support Ends |
|---------|--------|-------------|
| 1.3.0   | ✅ Current | 2027-08-17 |
| 1.2.0   | ⚠️ EOL | 2026-08-17 |

## Dependency Management

Security updates are applied automatically via:
- **Dependabot** — weekly scans
- **GitHub Security Advisories** — continuous monitoring
- **Manual audits** — regular reviews

## CVE History

No CVEs recorded for this project.

---

For full security details, see [SECURITY.md](../../SECURITY.md)
