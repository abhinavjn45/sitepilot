# Architecture

## System view

```text
AI client (Codex / Claude Code / other MCP client)
                    |
                    | MCP
                    v
       SitePilot Core (Python, local-first)
       - connections, policy, tool registry
       - approvals, audit, skills, job handling
                    |
                    | authenticated HTTPS/REST
                    v
       SitePilot Connect (WordPress plugin)
       - WordPress authorization and APIs
       - validated, scoped operations
                    |
                    v
              WordPress site(s)

Optional independent interfaces: Dashboard (Next.js) and CLI
Reusable agent workflows: Skills directory
```

## Component boundaries

- `sitepilot-core/`: MCP protocol boundary, connection configuration, policy/approval and audit services, tool adapters, structured responses. Python. FastAPI only where HTTP endpoints are needed; use a compatible official MCP SDK.
- `wordpress-plugin/`: WordPress-specific integration, independently installable and extractable later. REST routes must enforce capabilities and validate inputs; business actions should use WordPress APIs. Do not rely on remote shell or WP-CLI for baseline behavior.
- `dashboard/`: optional web client. It communicates with Core through a deliberately scoped API; it is not on the MCP critical path.
- `skills/`: client-reusable instructions and workflows, separated from executable server tools.
- `cli/`: optional operator interface to Core functionality.

## Trust boundaries and flow

AI clients, prompts, site content, plugin responses, and network input are untrusted. Core authenticates and authorizes each operation, applies policy/approval requirements, records auditable events, and calls a configured connector over secure transport. The plugin independently checks WordPress user capabilities and validates the requested operation before using WordPress APIs. Secrets remain in local secure configuration/storage, not prompts or logs.

The Phase 2 read-only connector exposes `GET /wp-json/sitepilot/v1/status`, `GET /wp-json/sitepilot/v1/site-info`, `GET /wp-json/sitepilot/v1/plugins`, `GET /wp-json/sitepilot/v1/themes`, `GET /wp-json/sitepilot/v1/posts`, `GET /wp-json/sitepilot/v1/pages`, `GET /wp-json/sitepilot/v1/users`, `GET /wp-json/sitepilot/v1/media`, `GET /wp-json/sitepilot/v1/comments`, `GET /wp-json/sitepilot/v1/categories`, and `GET /wp-json/sitepilot/v1/tags`. Each route requires a WordPress user with `manage_options`. Python Core exposes the corresponding read-only MCP tools; the client chooses only these fixed routes and does not accept a URL as tool input. The owner reports the original six tools are tested against the local WordPress installation. The users, media, comments, categories, and tags endpoints/tools are implemented and mock-tested in source; those plugin routes still need installation and live verification.

## Theme and builder isolation

Theme changes should operate on a draft or separate working copy, validate and preview, then wait for approval before publishing. Preserve a backup and provide rollback. Builder-specific adapters own detection, version compatibility, data parsing, and safe supported mutations. No adapter may assume another builder's data model.

## Development Environment

Windows is the primary development environment, with VS Code as the IDE and XAMPP for local WordPress testing. SitePilot Core is planned as a local-first Python MCP server. Docker and other container dependencies are not mandatory.

## Deployment shape

Initial target is local Windows use without Docker. The Dashboard and CLI are optional. Remote sites need secure communication and authenticated plugin endpoints. Hosting limitations must be surfaced rather than worked around by disabling controls. No live connection or deployment is part of Phase 0.

## Future extraction

The connector directory is a clear product boundary so it can become its own public repository without large restructuring. The project uses one Git repository. It is initialized on branch `main` with initial commit `14691ea` (`first commit`); `main` tracks `origin/main`. The component boundaries keep the connector extractable later.

