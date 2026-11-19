# Architectural Decisions

## Accepted for project initialization

### One workspace with clear component boundaries

**Decision:** Keep Core, plugin, dashboard, skills, CLI, and project docs in one initially intended repository, with the WordPress plugin isolated in its own directory.

**Reason:** Simplifies initial development while allowing the plugin to be extracted for public release later.

### Python Core and native WordPress connector

**Decision:** Build Core in Python using a compatible official MCP SDK; use FastAPI when HTTP APIs are needed. Build the connector as a WordPress plugin using WordPress APIs.

**Reason:** Matches the MCP and WordPress integration requirements while avoiding remote shell dependencies.

### Optional interfaces

**Decision:** Dashboard and CLI are optional and must not be prerequisites for MCP operation.

**Reason:** Keep the central agent integration independently usable.

### Safe theme editing

**Decision:** Default theme workflow uses a draft/working copy with validation, review, approval, backup, and rollback; do not directly edit active production theme by default.

**Reason:** Reduce risk of site breakage and preserve a recovery path.

### Phase 0 scope

**Decision:** Initialize documentation and structure only; no packages, application code, deployment, or live WordPress connections.

**Reason:** The owner requested a careful foundation before implementation.

## Deferred decisions

Exact MCP transport, authentication/token lifecycle, secure credential vault, database choice (if any), plugin route/versioning scheme, approval policy details, dashboard API contract, CLI framework, supported PHP/Python/WordPress versions, and licensing verification remain open until their implementation phases. No paid or mandatory external service may be introduced without first investigating a free local/open-source alternative.
