# Technology Stack

These are planned choices, not installed dependencies.

| Area | Planned choice | Reason / constraint |
|---|---|---|
| Core MCP server | Python and a compatible official MCP SDK | Local-first server and MCP tool implementation |
| HTTP API | FastAPI where an HTTP app/API is needed | Explicitly preferred for HTTP application needs; not required for every MCP transport |
| WordPress integration | PHP WordPress plugin and WordPress APIs | Independently installable connector with native capability/security model |
| Dashboard | Next.js, React, TypeScript | Planned optional web interface; never required for MCP |
| Skills | Version-controlled documentation/workflows | Portable, modular agent guidance |
| CLI | Optional command-line interface (implementation choice deferred) | Operator convenience only |
| Development | Windows supported without Docker/containers | Local-first requirement |
| Repository | Initially one Git repository, plugin boundary kept extractable | Easier initial development and later independent plugin publication |

No packages were installed in Phase 0. Prefer free/open-source components and avoid mandatory external services or paid dependencies. Final versions and exact libraries should be selected when implementation begins and recorded with rationale.
