# SitePilot Core

SitePilot Core is the local Python MCP server that connects an MCP client to the separately installed SitePilot WordPress plugin.

## Current status

The foundation is implemented: an official MCP SDK v2 stdio server exposes read-only WordPress information and inventory tools, with typed one-site configuration, local URL restrictions, an HTTPX client, and a credential-provider interface. Unit tests use mocked HTTP responses. The comments endpoint and tool in this change are source-implemented and mock-tested; update the plugin in WordPress before using that route. No live request is part of this change.

## Requirements

- Python 3.13 and the project `.venv`
- Install pinned dependencies from `requirements.lock`, then install the local package in editable mode:

  ```powershell
  .\.venv\Scripts\python.exe -m pip install -r .\sitepilot-core\requirements.lock
  .\.venv\Scripts\python.exe -m pip install -e .\sitepilot-core --no-deps --no-build-isolation
  ```
- Set `SITEPILOT_WORDPRESS_URL` to the local WordPress site URL before launching
- Optional `SITEPILOT_WP_USERNAME` and `SITEPILOT_CREDENTIAL_REF` configure credential lookup. The reference points to Windows Credential Manager; the password itself is never stored in project files.
- Optional `SITEPILOT_CA_CERT` adds a local development CA certificate while retaining normal TLS certificate and hostname verification.

### Local HTTPS certificate trust on Windows

When using mkcert's default Windows CA location, set the public CA certificate for the current PowerShell session before launching SitePilot Core:

```powershell
$env:SITEPILOT_CA_CERT = "$env:LOCALAPPDATA\mkcert\rootCA.pem"
```

This adds that CA alongside the normal public certificate authorities; it does not disable TLS checks. Use the public `rootCA.pem` file only. Never set this variable to `rootCA-key.pem`, which is the private CA key. The setting applies only to processes started from that PowerShell session. To clear it from the current session:

```powershell
Remove-Item Env:SITEPILOT_CA_CERT
```

If mkcert was configured with a custom `CAROOT`, set the variable to that location's `rootCA.pem` instead.

The client refuses to retrieve or send a stored credential over plain HTTP. Local HTTP can be used for unauthenticated development checks; the protected status endpoint will report that authentication is required until a secure authenticated transport is configured.

### Connection errors

Transport failures are classified into safe categories such as TLS certificate verification, refused connections, connection timeouts, DNS lookup failures, response-read failures, and other connection failures. SitePilot returns a fixed, category-specific message without including exception details. Transport exceptions and credentials are not written to application logs.

### Read-only MCP tools

- `site_status` reads connector and runtime version status from `GET /wp-json/sitepilot/v1/status`.
- `site_info` reads general WordPress site information from `GET /wp-json/sitepilot/v1/site-info`. It returns `site_name`, `site_description`, `home_url`, `site_url` (the WordPress installation URL), `wordpress_version`, `php_version`, `timezone`, `gmt_offset`, `locale`, and `plugin_version`. Optional values use JSON `null` when unavailable.
- `list_plugins` reads installed plugin metadata from `GET /wp-json/sitepilot/v1/plugins`. Each entry contains a safe relative `plugin_file` identifier when available, `name`, `version`, `status` (`active` or `inactive`), `description`, and `author`. Missing optional values use JSON `null`; an unavailable listing returns `plugins: null`, while a successful empty site returns `plugins: []`.
- `list_themes` reads installed theme metadata from `GET /wp-json/sitepilot/v1/themes`. Each entry contains `stylesheet`, `name`, `version`, `status` (`active` or `inactive`), `description`, `author`, and optional parent-theme `template`. Missing optional values use JSON `null`; an unavailable listing returns `themes: null`, while a successful empty site returns `themes: []`.
- `list_posts` reads post metadata from `GET /wp-json/sitepilot/v1/posts`. Its optional inputs are `page` (1–10,000; default `1`), `per_page` (1–50; default `10`), and one `status` (default `publish`; supported values are `publish`, `future`, `draft`, `pending`, and `private`). Its result includes posts, page counts, totals, the selected status, and a safe message.
- `list_pages` reads page metadata from `GET /wp-json/sitepilot/v1/pages`. It accepts the same bounded `page`, `per_page`, and explicitly supported `status` inputs as `list_posts`, and returns page ID, title, slug, status, author ID, dates, permalink, parent ID, menu order, and pagination.
- `list_users` reads privacy-limited user metadata from `GET /wp-json/sitepilot/v1/users`. It accepts `page` (1–10,000; default `1`) and `per_page` (1–50; default `10`), returning user ID, username, display name, role identifiers, registration date, description, and pagination. Email-shaped user text is suppressed and sensitive/unexpected fields are rejected by validation.
- `list_media` reads attachment metadata from `GET /wp-json/sitepilot/v1/media`. It accepts `page` (1–10,000; default `1`) and `per_page` (1–50; default `10`), returning only the documented attachment fields. Filenames are basenames, path-like text is suppressed, unsafe query-bearing source URLs are omitted, and unexpected metadata or sensitive fields are rejected.
- `list_comments` reads a bounded page from `GET /wp-json/sitepilot/v1/comments`. It accepts `page` (1–10,000; default `1`), `per_page` (1–50; default `10`), and `status` (`approved`, `pending`, `spam`, or `trash`; default `approved`). It returns only comment ID, post ID, author name, date, plain-text content, status, and type. Email addresses in text are redacted and unexpected fields are rejected. WordPress-native `approve` and `hold` query statuses are mapped to the public `approved` and `pending` values.
- `list_categories` reads the built-in category taxonomy from `GET /wp-json/sitepilot/v1/categories`. It accepts `page` (1–10,000; default `1`) and `per_page` (1–50; default `10`), and returns only category ID, name, slug, plain-text description, parent ID, post count, and pagination. It does not accept a taxonomy or arbitrary query arguments.
- `list_tags` reads the built-in `post_tag` taxonomy from `GET /wp-json/sitepilot/v1/tags`. It accepts `page` (1–10,000; default `1`) and `per_page` (1–50; default `10`), and returns only tag ID, name, slug, plain-text description, post count, and pagination. Empty tags are included; no taxonomy or arbitrary query arguments can be supplied.

All tools use the configured site and existing credential provider. None accepts a URL or performs writes. The plugin checks that the authenticated WordPress user has `manage_options`. Responses are allowlisted and exclude credentials, email addresses, secret configuration, and absolute filesystem paths. The owner reports the original six tools have been tested against the local WordPress site. `list_users`, `list_media`, `list_comments`, `list_categories`, and `list_tags` are source-implemented and mock-tested but have not been live-verified.

## Run

Install the Core package into the project virtual environment once:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .\sitepilot-core --no-deps --no-build-isolation
```

Then run it from the repository root:

```powershell
.\.venv\Scripts\python.exe -m sitepilot_core
```

Configure your MCP host to launch this command with `sitepilot-core` as its working directory. The server uses stdio and does not open a network port. It writes no diagnostic messages to stdout.

## Test

```powershell
.\.venv\Scripts\python.exe -m pytest sitepilot-core\tests
```

The tests do not contact WordPress or a database. See `../project-docs/ARCHITECTURE.md` and `../project-docs/SECURITY.md` for product boundaries and security principles.
