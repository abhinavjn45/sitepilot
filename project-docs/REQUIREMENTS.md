# Requirements

Status: long-term product requirements. Unless explicitly marked otherwise in `FEATURE_STATUS.md`, these are not implemented.

## Product and operations

- Support multiple local or remote WordPress connections through a local-first Python MCP server.
- Support Codex, Claude Code, and other compatible MCP clients.
- Provide centralized tools, authentication/authorization, approvals, audit history, structured errors, and long-running operation handling.
- Run on Windows without mandatory containers. Dashboard and CLI are optional.
- No paid or mandatory external service dependencies.

## WordPress management scope

Over time provide supported operations for posts/pages, media, categories/tags, users/roles, plugins/themes, options/settings, menus/widgets, custom post types/taxonomies/fields, comments, and environment/site health.

Advanced integrations may include ACF and WooCommerce. Database inspection and maintenance, search/replace, export/import, cache/transients, rewrite rules, and core/plugin/theme update operations must use appropriate WordPress APIs or carefully controlled mechanisms with clear limitations and safety checks.

## Connector

- Independently installable, modular WordPress plugin intended for open-source release, preferably GPL-2.0-or-later subject to license verification.
- Authenticated REST endpoints using capabilities, validation, sanitization, escaping, and applicable nonce/security protections.
- Basic functionality must not require SSH or WP-CLI on the host. Optional WP-CLI integration may be considered when available.
- Restrict file operations to authorized WordPress paths.

## Theme workflow

Support active theme inspection and file reading, separate draft/working copy, file creation/modification, PHP syntax and risk checks, previews, review, explicit approval, publication, backup, and rollback. Never edit the active production theme directly as the default. Report hosting limitations and safe alternatives.

## Page builders and skills

Each integration must be a separate adapter because the builders use different APIs, storage formats, editor behavior, and rendering pipelines. The following compatibility and testing requirements apply per builder:

- **Gutenberg / WordPress Block Editor:** Detect the WordPress core and editor versions and relevant block/theme support. Test discovery and read/write behavior for supported core blocks, serialization and persistence of block markup, editor loading, and front-end rendering on the tested WordPress version. Treat third-party blocks as unsupported unless separately identified and tested.
- **Elementor:** Detect the Elementor version and whether Elementor Pro is installed, including its version when applicable. Test supported document/layout inspection and changes, persistence through Elementor's APIs, editor loading, and front-end rendering. Declare Free and Pro coverage separately where behavior differs.
- **Divi:** Detect the installed Divi generation/version and whether the site uses Divi Builder with a compatible theme or plugin setup. Test the supported content representation and save path, editor loading, and front-end rendering for each claimed generation; do not assume Divi 4 and Divi 5 formats or behavior are interchangeable.
- **Bricks Builder:** Detect the Bricks version and confirm the supported content type/template context. Test reading and modifying supported builder data, persistence, editor loading, and front-end rendering on that installed version.
- **Beaver Builder:** Detect the Beaver Builder plugin/version and whether the Lite or premium edition is installed. Test supported layout inspection/modification, persistence, editor loading, and front-end rendering. Document edition-specific limits and claim coverage only for tested editions.
- **Breakdance:** Detect the installed Breakdance version and supported page/template context. Test reading and modifying supported builder data, persistence, editor loading, and front-end rendering on that installed version.

For every adapter, record the WordPress, PHP, builder, and relevant edition/version combination actually tested, along with the tested operations and known limitations. Compatibility may be claimed only for builder versions and configurations tested against an actual installation of those versions; documentation review, mocks, or inferred compatibility alone are insufficient. Re-run the relevant checks when supported versions or adapter behavior change. Unsupported versions and formats must be reported clearly and left unmodified.

- Skills are modular, documented, version-controlled, reusable across clients, and make no unsupported compatibility claims.
- Planned workflows: site inspection/debugging, plugin management, theme development/modification, builder development, WooCommerce, ACF, performance/security inspection, and database inspection.
## Security and non-functional requirements

- Never expose credentials to AI conversations or commit secrets.
- Secure credential storage/encryption as appropriate; least privilege; secure transport.
- Validate all requests; treat remote site data as untrusted.
- Address CSRF, SSRF, SQL injection, XSS, path traversal, and unauthorized access.
- No arbitrary remote shell execution; do not disable security controls.
- Explicit approval for destructive changes; operation logs; backups and rollback for risky operations.
- Modular, maintainable, extensible code; clear errors and limitations; documentation consistent with tested behavior.

## Future dashboard

Provide site connections/status, WordPress overview, available tools, approvals, audit logs, skills, integrations, theme and builder information, operation history, and system health.

## Future CLI

Provide configuration, site connection management, health, tool/skill inspection, diagnostics, and operation history. It remains optional.

