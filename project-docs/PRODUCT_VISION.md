# Product Vision

## Purpose

SitePilot is a personal, self-hosted, AI-powered WordPress management platform. It will let compatible AI coding assistants (including Codex and Claude Code) manage one or more WordPress websites through natural language and MCP, while the owner retains control of the software and data.

The long-term aim is broad functional similarity to the category of WordPress management assistants, implemented independently. SitePilot must not copy proprietary source code, copyrighted assets, branding, or protected implementation details from WPVibe or any other product.

## Product qualities

- Modular, extensible, maintainable, and suitable for open-source development.
- Local-first, able to run on Windows without Docker or containers.
- Secure by default, with least privilege, approvals, audit history, backups, and rollback for risky operations.
- Useful with local and remotely hosted WordPress sites.
- No mandatory paid service, paid model/API, paid hosting, database, SaaS, or paid plugin.
- The dashboard and CLI are optional; the MCP server remains independently usable.

## Components

1. **SitePilot Core:** Python MCP server; connection and authorization management, tool registry, approval workflows, audit logs, skills, long-running work, and structured errors. FastAPI is for HTTP needs; use a compatible official MCP SDK.
2. **SitePilot Connect:** modular, independently installable WordPress plugin. It provides authenticated REST integration using WordPress capabilities and security APIs. Basic functionality cannot depend on SSH or remote WP-CLI.
3. **Dashboard:** optional Next.js/React/TypeScript interface for sites, status, tools, approvals, audit, skills, integrations, themes, operations, and health.
4. **Skills:** version-controlled, modular workflows reusable across compatible agents.
5. **CLI:** optional configuration, site, health, tool, skill, diagnostic, and history commands.

## Long-term experience

An authorized agent should be able to inspect a site, make supported changes through explicit tools, explain the proposed impact, request approval where needed, and provide an auditable result. Theme work should use a separate draft or working copy, validation, preview/review, approval, backup, publication, and rollback rather than editing the active production theme by default.

Page-builder support is adapter-based. Gutenberg, Elementor, Divi, Bricks, Beaver Builder, and Breakdance have distinct formats and compatibility requirements; they must not be treated as interchangeable.

## Current boundary

The current work is Phase 0: repository structure and documentation. There is no implemented MCP server, plugin, dashboard, CLI, skills runtime, WordPress connection, or feature behavior yet.
