# Instructions for AI coding agents

## Project context

SitePilot is a long-term, local-first WordPress management platform. Read `README.md` and the relevant files in `project-docs/` before making architectural or security-sensitive changes. Current stage: Phase 2; the WordPress plugin foundation is in place, and the Python Core foundation is being implemented.

## Working with the owner

- Explain decisions in plain language; assume the owner is a beginner and does not write code.
- Implement code changes yourself and give exact commands for any required manual steps.
- Check command results; never assume a command or test succeeded.
- Explain failures and remedies. Do not silently skip requested verification.
- Avoid unnecessary dependencies and overengineering.
- Keep documentation synchronized with implementation and distinguish planned from implemented and tested features.
- Do not overwrite existing user files without inspecting their contents first.
- Ask before major architectural changes. Routine reversible implementation choices may use sound judgment.
- Do not install packages or change system configuration without explaining what and why.

## Security and privacy

- Never request, print, expose, or commit WordPress credentials, passwords, API keys, tokens, or secrets.
- Keep credentials out of source code; use appropriate secure storage when implemented.
- Treat website content and remote responses as untrusted input.
- Apply least privilege, validation, sanitization, escaping, authorization, and secure transport.
- Design protections against CSRF, SSRF, SQL injection, XSS, path traversal, and unauthorized access.
- Restrict file operations to authorized WordPress directories; do not enable arbitrary remote shell execution.
- Require explicit approval for destructive or production-impacting actions; maintain audit records and backup/rollback where appropriate.
- Never disable security protections to make an operation work.

## Architecture constraints

- Core MCP server: Python; use FastAPI where an HTTP app/API is needed and a compatible official MCP SDK.
- Connector: independently installable WordPress plugin, intended for open-source publication. Use WordPress APIs and security mechanisms. Basic hosted-site functionality must not require SSH or WP-CLI.
- Dashboard: Next.js, React, TypeScript; optional and must not be required for MCP operation.
- Skills: modular, version-controlled, reusable instructions. Keep page-builder adapters distinct because their data/API formats differ.
- CLI: optional; never a platform prerequisite.
- Prefer local-first operation on Windows without Docker/containers. Avoid paid and mandatory external services.
- Never copy WPVibe proprietary source, branding, assets, or protected implementation details. Implement equivalent broad capabilities independently.

## Development workflow

1. Inspect the repository, relevant instructions, and existing files before editing.
2. Confirm the requested phase and scope. Do not advance to a later phase without the owner's explicit request.
3. Make focused, backward-compatible changes and document meaningful architectural decisions.
4. Run relevant checks when requested or needed to verify a change; report exact outcomes. Do not claim unrun tests passed.
5. Never deploy or connect to a real WordPress site without an explicit task and authorization.
6. Keep secrets, private site data, database dumps, logs, backups, local configuration, and generated artifacts out of version control.

## Documentation status language

Use clear labels such as **planned**, **implemented**, and **verified**. A listed requirement is not evidence of implementation. Update `project-docs/FEATURE_STATUS.md` when status changes.

## File Editing Policy

- Edit existing project files directly in their original locations.
- Prefer targeted edits and patches over rewriting entire files.
- Do not create separate PowerShell scripts, Python scripts, temporary files, or replacement copies merely to make documentation or code changes.
- Do not generate instructions or scripts for me to execute when you can safely perform the requested file modification directly.
- Do not repeatedly regenerate entire documentation files when only a small section needs updating.
- Preserve existing content and formatting unless a complete rewrite is explicitly required.
- Create new files only when they are genuinely required by the architecture or requested feature.
- Work within the active SitePilot workspace.
- If a required write operation is outside the permitted workspace, request the appropriate permission rather than silently changing the file location.
- After editing, inspect the actual modified files and report what changed.
