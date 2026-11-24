# Development Plan

Roadmap is provisional and may be refined as requirements become concrete. Do not advance phases without the owner's explicit request.

| Phase | Scope | Status |
|---|---|---|
| 0 | Project initialization, modular structure, documentation | Complete: documentation, Git setup, and environment review completed; Composer is not installed and is not required for the initial plugin foundation |
| 1 | WordPress connector plugin foundation | Complete: status endpoint implemented and PHP syntax-checked; owner reports local installation, activation, administrator success, and unauthenticated 401 verification |
| 2 | Local MCP server foundation | In progress: stdio-only MCP server, typed local-site configuration, restricted status client, credential-provider interface, and mocked unit tests implemented; no live WordPress request made by Core |
| 3 | Codex and Claude Code connectivity | Not started |
| 4 | Core WordPress management tools | Not started |
| 5 | WP-CLI-style tool system via WordPress APIs where possible | Not started |
| 6 | Approval engine and audit logging | Not started |
| 7 | Safe theme builder workflow | Not started |
| 8 | Gutenberg and Elementor adapters | Not started |
| 9 | Additional page-builder adapters | Not started |
| 10 | Reusable skills system | Not started |
| 11 | WooCommerce, ACF, and advanced integrations | Not started |
| 12 | Dashboard, CLI, testing, hardening, and deployment | Not started |

## Phase 0 completion checklist

- [x] Inspect workspace and record Git status.
- [x] Establish documented component boundaries and placeholder descriptions.
- [x] Create requested project documentation and ignore rules.
- [x] Initialize Git and create the initial commit (`14691ea`, `first commit`) on `main`, tracking `origin/main`.
- [x] Verify the development environment (PHP, Composer availability, Python, Node.js, and local WordPress connectivity); Composer is not installed.
- [x] Review/adjust assumptions before authorizing Phase 1.

At the end of Phase 0, no project packages had been installed and no WordPress site had been connected through SitePilot; nothing was deployed.
