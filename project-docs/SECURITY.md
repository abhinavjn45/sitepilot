# Security Principles and Threat Considerations

Security is foundational. This file records design requirements, not a claim that controls have already been implemented.

## Required controls

- Never expose WordPress credentials to AI conversations. Never put passwords, tokens, or API keys in source or version control.
- Use appropriate secure local credential storage/encryption and least-privilege authentication.
- Validate inputs and authorize every operation. Treat site content, plugin responses, and remote data as untrusted.
- Use secure transport for remote sites.
- Apply WordPress capabilities, nonces where applicable, sanitization, validation, and output escaping.
- Restrict file operations to authorized WordPress directories and prevent path traversal.
- Do not provide arbitrary remote shell execution. Basic connector functionality must not depend on SSH/WP-CLI.
- Require explicit approval for destructive or production-impacting actions; maintain audit logs.
- Back up important data before risky changes and support rollback where feasible.
- Never expose administrative tools publicly without authentication or disable protections to make an operation work.

## Threats to address

Unauthorized users or compromised credentials; malicious prompts or site content; CSRF against browser-facing endpoints; SSRF through user-supplied URLs; SQL injection; XSS; unsafe file writes; privilege escalation; supply-chain risks; secret leakage through logs, errors, or commits; accidental destructive changes; insecure transport; and denial of service from long-running or repeated actions.

## Risk-sensitive workflows

Theme edits use a separate draft, validation, preview, review, explicit approval, backup, publication, and rollback. Plugin/theme/core updates, imports, database operations, user/role changes, and deletion require careful capability checks, impact disclosure, and approval policy. Exact controls and recovery limits must be documented as each feature is built and verified.
