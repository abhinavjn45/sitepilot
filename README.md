# SitePilot

SitePilot is a planned personal, self-hosted platform for managing one or more WordPress websites through AI assistants using the Model Context Protocol (MCP). It aims to offer independent, open-source functionality comparable in broad purpose to WordPress management assistants while keeping the owner in control of code, data, and hosting.

**Project stage:** Phase 0 — foundation and documentation. No application functionality has been implemented yet.

## Planned components

- **SitePilot Core** (`sitepilot-core/`): Python MCP server, with FastAPI for HTTP APIs when needed.
- **SitePilot Connect** (`wordpress-plugin/`): independently installable WordPress plugin and authenticated integration layer.
- **Dashboard** (`dashboard/`): optional Next.js, React, and TypeScript web interface. MCP use must not depend on it.
- **Skills** (`skills/`): reusable, versioned agent instructions and workflows.
- **CLI** (`cli/`): optional command-line tools; never a prerequisite for using the platform.

See [PRODUCT_VISION](project-docs/PRODUCT_VISION.md), [ARCHITECTURE](project-docs/ARCHITECTURE.md), and [DEVELOPMENT_PLAN](project-docs/DEVELOPMENT_PLAN.md) for details.

## Development status

This repository currently contains project documentation and component placeholders only. The planned features are requirements, not implemented or tested functionality. No packages are installed by this initialization.

## Principles

- Local-first operation, including Windows without Docker.
- Secure, least-privilege access and explicit approval for destructive actions.
- WordPress APIs for basic remote operations; no requirement for remote SSH or WP-CLI.
- Modular architecture, auditable operations, and safe backups/rollback.
- No paid or mandatory external service dependencies.
- Independent implementation; do not copy proprietary source, branding, or protected assets.

## Current setup

There is no runnable application yet. For now, review the project documentation. Git was not initialized in the inspected workspace. When ready, initialize this directory as the single project repository and begin Phase 1 only after explicitly deciding to proceed.

## Documentation

- [Requirements](project-docs/REQUIREMENTS.md)
- [Architecture](project-docs/ARCHITECTURE.md)
- [Technology choices](project-docs/TECH_STACK.md)
- [Security](project-docs/SECURITY.md)
- [Decisions](project-docs/DECISIONS.md)
- [Feature status](project-docs/FEATURE_STATUS.md)
- [Development plan](project-docs/DEVELOPMENT_PLAN.md)
- [Agent instructions](AGENTS.md)
