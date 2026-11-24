# SitePilot

SitePilot is a planned personal, self-hosted platform for managing one or more WordPress websites through AI assistants using the Model Context Protocol (MCP). It aims to offer independent, open-source functionality comparable in broad purpose to WordPress management assistants while keeping the owner in control of code, data, and hosting.

**Project stage:** Phase 2 — Python Core and MCP server foundation.

## Planned components

- **SitePilot Core** (`sitepilot-core/`): Python MCP server, with FastAPI for HTTP APIs when needed.
- **SitePilot Connect** (`wordpress-plugin/`): independently installable WordPress plugin and authenticated integration layer.
- **Dashboard** (`dashboard/`): optional Next.js, React, and TypeScript web interface. MCP use must not depend on it.
- **Skills** (`skills/`): reusable, versioned agent instructions and workflows.
- **CLI** (`cli/`): optional command-line tools; never a prerequisite for using the platform.

See [PRODUCT_VISION](project-docs/PRODUCT_VISION.md), [ARCHITECTURE](project-docs/ARCHITECTURE.md), and [DEVELOPMENT_PLAN](project-docs/DEVELOPMENT_PLAN.md) for details.

## Development status

The WordPress plugin status endpoint is installed and activated in the local test site; the owner reports successful administrator and unauthenticated REST checks. The Python Core has read-only `site_status`, `site_info`, `list_plugins`, `list_themes`, `list_posts`, `list_pages`, `list_users`, `list_media`, `list_comments`, `list_categories`, and `list_tags` MCP tools. The owner reports the original six tools have been tested against the local WordPress site. The users, media, comments, categories, and tags tools and plugin routes are implemented and mock-tested or syntax-checked, but need installation/update and live verification before use against WordPress. The dashboard, CLI, and broader WordPress management features remain planned.

## Principles

- Local-first operation, including Windows without Docker.
- Secure, least-privilege access and explicit approval for destructive actions.
- WordPress APIs for basic remote operations; no requirement for remote SSH or WP-CLI.
- Modular architecture, auditable operations, and safe backups/rollback.
- No paid or mandatory external service dependencies.
- Independent implementation; do not copy proprietary source, branding, or protected assets.

## Current setup

The local WordPress test site is available at `http://localhost/sitepilot-test/`. Git is initialized as a single project repository on branch `main`; the initial commit is `14691ea` (`first commit`), and the branch tracks `origin/main`. The Python Core dependencies are installed in the project `.venv` only.

## Documentation

- [Requirements](project-docs/REQUIREMENTS.md)
- [Architecture](project-docs/ARCHITECTURE.md)
- [Technology choices](project-docs/TECH_STACK.md)
- [Security](project-docs/SECURITY.md)
- [Decisions](project-docs/DECISIONS.md)
- [Feature status](project-docs/FEATURE_STATUS.md)
- [Development plan](project-docs/DEVELOPMENT_PLAN.md)
- [Agent instructions](AGENTS.md)
