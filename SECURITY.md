# Security Policy

## Reporting Vulnerabilities

If you discover a security vulnerability in mixin-suite, please report it privately using GitHub's security vulnerability reporting feature.

### How to Report

1. Navigate to the repository's **Security** tab
2. Click **Report a vulnerability**
3. Provide details of the vulnerability and steps to reproduce (if applicable)

I appreciate responsible disclosure and will acknowledge receipt of your report promptly.

## Security Considerations

- All adapter inputs (headers, event data, queue messages) are validated for injection attacks (CRLF, control characters, length limits)
- Correlation IDs are treated as untrusted user input and sanitized before use
- No sensitive data is logged by default

For detailed security implementation, see the adapter documentation in `docs/mixin_logging/apps/adapters/` and classifier documentation in `docs/mixin_sensitivity/apps/decorators/`.
