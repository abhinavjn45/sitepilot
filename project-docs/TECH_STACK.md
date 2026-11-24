# Technology Stack

The table separates implemented choices from later planned components. Exact Python Core dependency pins are recorded in `sitepilot-core/pyproject.toml` and `sitepilot-core/requirements.lock`.

| Area | Planned choice | Reason / constraint |
|---|---|---|
| Core MCP server | Python 3.13, official MCP SDK v2 (`mcp` 2.3.0), stdio | Implemented in the initial local-first server; no HTTP listener |
| Core WordPress client | HTTPX 0.28.1 | Implemented for the fixed, read-only status route; mocked tests only |
| Core credential storage | `keyring` 25.7.0 with Windows Vault backend | Provider implemented and backend availability verified; no secret stored or retrieved |
| Core tests | `pytest` 9.2.0 and AnyIO 4.16.0 | Implemented for mocked async unit tests |
| HTTP API | FastAPI where an HTTP app/API is needed | Explicitly preferred for HTTP application needs; not required for every MCP transport |
| WordPress integration | PHP WordPress plugin and WordPress APIs | Independently installable connector with native capability/security model |
| Dashboard | Next.js, React, TypeScript | Planned optional web interface; never required for MCP |
| Skills | Version-controlled documentation/workflows | Portable, modular agent guidance |
| CLI | Optional command-line interface (implementation choice deferred) | Operator convenience only |
| Development | Windows supported without Docker/containers | Local-first requirement |
| Repository | Initially one Git repository, plugin boundary kept extractable | Easier initial development and later independent plugin publication |

The pinned Core packages are installed in the project `.venv`; no global Python installation was changed. FastAPI remains deferred because the initial MCP server uses stdio and has no HTTP API. Prefer free/open-source components and avoid mandatory external services or paid dependencies.
