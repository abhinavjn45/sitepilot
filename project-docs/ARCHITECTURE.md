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

## Theme and builder isolation

Theme changes should operate on a draft or separate working copy, validate and preview, then wait for approval before publishing. Preserve a backup and provide rollback. Builder-specific adapters own detection, version compatibility, data parsing, and safe supported mutations. No adapter may assume another builder's data model.

## Deployment shape

Initial target is local Windows use without Docker. The Dashboard and CLI are optional. Remote sites need secure communication and authenticated plugin endpoints. Hosting limitations must be surfaced rather than worked around by disabling controls. No live connection or deployment is part of Phase 0.

## Future extraction

The connector directory is a clear product boundary so it can become its own public repository without large restructuring. The project uses one Git repository, initialized by the owner. The repository currently has no commits; its current branch is `master` while the owner changes the default branch to `main`. The component boundaries keep the connector extractable later.

