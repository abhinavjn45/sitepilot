# Feature Status

Last updated: 2026-11-24

This status distinguishes **planned** work (documented intent), **implemented** work (present in the project), and **verified** work (checked against the stated criteria). A requirement or placeholder is not an implementation.

| Area | Status | Evidence / note |
|---|---|---|
| Phase 0 documentation | Implemented (documentation only) | Project vision, requirements, architecture, roadmap, security, stack, decisions, status, agent guidance, README, ignore rules |
| Component directory structure | Implemented (placeholders only) | Directories and purpose README files created |
| Git repository | Initialized (committed) | Branch `main` tracks `origin/main`; initial commit `14691ea` (`first commit`) |
| MCP server | Implemented (read-only tools; stdio verified) | Official MCP SDK v2 stdio server registers read-only `site_status`, `site_info`, `list_plugins`, `list_themes`, `list_posts`, `list_pages`, `list_users`, `list_media`, `list_comments`, `list_categories`, and `list_tags`; no network server is exposed |
| Python Core WordPress client | Implemented (mock tested) | HTTPX client validates fixed status, site-info, inventory, post, page, user, media, comment, category, and tag responses, limits payload size, rejects redirects, uses timeouts, and permits loopback destinations only; `list_tags` uses mocked HTTP |
| Python Core credentials | Implemented (provider interface) | Windows Credential Manager backend verified as available; no credentials created, requested, read, or sent |
| WordPress plugin | Implemented (existing routes owner-verified; users, media, comments, categories, and tags routes source implemented) | `wordpress-plugin/sitepilot-connect.php` exposes read-only `status`, `site-info`, `plugins`, `themes`, `posts`, `pages`, `users`, `media`, `comments`, `categories`, and `tags` routes guarded by `manage_options`; users, media, comments, categories, and tags routes are syntax-checked but not installed or runtime-verified |
| Dashboard | Not implemented | No application source or dependencies |
| Skills runtime/content | Not implemented | Directory purpose placeholder only |
| CLI | Not implemented | Directory purpose placeholder only |
| WordPress management tools | Not implemented | Requirements only |
| Approvals/audit | Not implemented | Requirements/design only |
| Theme builder/page-builder adapters | Not implemented | Requirements/design only |
| Page-builder integrations | Planned | Gutenberg, Elementor, Divi, Bricks Builder, Beaver Builder, and Breakdance are requirements only |
| Page-builder compatibility claims | Not verified | No integration has been tested against actual installed builder versions |
| Tests | Verified (Core unit suite) | 298 mocked Python unit tests pass; PHP syntax check passes; MCP tool registration is covered. Users, media, comments, categories, and tags routes/tools have not been tested against live WordPress. |
| Deployment | Not performed | No site connected or deployment |


