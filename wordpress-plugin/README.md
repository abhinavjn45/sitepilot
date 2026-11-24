# SitePilot WordPress Plugin

SitePilot is an independently installable WordPress plugin. Its read-only REST endpoints provide connector status, allowlisted site information, plugin/theme inventories, and paginated post, page, user, media, comment, category, and tag data. They do not perform WordPress management operations.

## Requirements

- WordPress 7.1 or later
- PHP 8.2 or later

The project owner reports that the status, site information, plugin, theme, post, and page routes have been tested against the local WordPress installation. The users, media, comments, categories, and tags routes are source-implemented and syntax-checked only; they have not yet been installed or runtime-tested.

## Install

1. Copy the contents of this directory into a folder named `sitepilot` inside the WordPress `wp-content/plugins/` directory.
2. In WordPress Admin, open **Plugins** and activate **SitePilot**.

Update the installed plugin through the normal local workflow before using a route that is not yet present in that installation. This implementation task does not install or activate the plugin.

## Status endpoint

The plugin registers:

```text
GET /wp-json/sitepilot/v1/status
```

For a local site at `http://localhost/sitepilot-test/`, the endpoint URL is:

```text
http://localhost/sitepilot-test/wp-json/sitepilot/v1/status
```

The route requires WordPress REST authentication for a user who has the `manage_options` capability. WordPress handles authentication and returns its standard REST authorization error when the request is not permitted. Use HTTPS for authenticated requests to remote sites.

Successful requests return JSON with these fields:

```json
{
  "plugin_name": "SitePilot",
  "plugin_version": "0.1.0",
  "wordpress_version": "<installed WordPress version>",
  "php_version": "<PHP version serving WordPress>",
  "status": "ok"
}
```

The endpoint accepts no input parameters and does not read or change site content.

## Site information endpoint

The plugin also registers:

```text
GET /wp-json/sitepilot/v1/site-info
```

This route uses the same WordPress REST authentication and `manage_options` capability check as the status route. It accepts no input parameters and reads information through WordPress APIs only. Optional text, URLs, timezone, locale, and GMT offset are returned as JSON `null` when unavailable. Successful responses contain these allowlisted fields:

```json
{
  "site_name": "Example Site",
  "site_description": "A WordPress site",
  "home_url": "https://example.test/",
  "site_url": "https://example.test/",
  "wordpress_version": "7.1.5",
  "php_version": "8.2.12",
  "timezone": "America/New_York",
  "gmt_offset": -5.0,
  "locale": "en_US",
  "plugin_version": "0.1.0"
}
```

The response excludes administrator email addresses, credentials, private configuration, and server filesystem paths. The route is implemented in the plugin source; it must be installed or updated in WordPress before it is available on a site.

## Installed plugins endpoint

The plugin provides an administrator-only read endpoint:

```text
GET /wp-json/sitepilot/v1/plugins
```

It uses WordPress plugin APIs to enumerate installed plugins and determine active state, including network-active plugins on multisite. It does not accept input parameters or change plugin state. The response contains only a safe relative plugin identifier and the plugin name, version, active/inactive status, description, and author. Unavailable metadata is `null`; malformed metadata is returned as `null` fields or an empty listing when WordPress cannot provide a valid plugin list. The plugin metadata is read through WordPress APIs; no direct SQL is used.

Example:

```json
{
  "plugins": [
    {
      "plugin_file": "hello-dolly/hello.php",
      "name": "Hello Dolly",
      "version": "1.7.2",
      "status": "inactive",
      "description": "A sample plugin.",
      "author": "WordPress contributors"
    }
  ]
}
```

The project owner reports that this route has been tested against the local WordPress installation.

## Posts endpoint

The plugin provides an administrator-only, read-only endpoint:

```text
GET /wp-json/sitepilot/v1/posts
```

It uses `WP_Query` and WordPress post/taxonomy functions. Query parameters are bounded and validated: `page` is 1–10,000 (default `1`), `per_page` is 1–50 (default `10`), and `status` must be one of `publish`, `future`, `draft`, `pending`, or `private` (default `publish`). Unsupported statuses are rejected. Pagination reports `page`, `per_page`, `total_items`, `total_pages`, and the requested status based on the same query used to retrieve posts.

The response includes `connection_status`, `posts`, `pagination`, and `message`. Post entries include ID, sanitized title and slug, status, author ID, date, modified date, permalink, and category/tag IDs. It excludes post content, author email addresses, credentials, and filesystem paths. A successful empty query returns `posts: []`; a failure returns `posts: null`. This endpoint never creates, changes, publishes, trashes, or deletes posts and does not use direct SQL.

Example:

```json
{
  "connection_status": "connected",
  "posts": [],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total_items": 0,
    "total_pages": 0,
    "status": "publish"
  },
  "message": "Posts retrieved successfully."
}
```

The project owner reports that this route has been tested against the local WordPress installation.

## Pages endpoint

The plugin provides an administrator-only, read-only endpoint:

```text
GET /wp-json/sitepilot/v1/pages
```

It uses `WP_Query` with `post_type` fixed to `page`, so it cannot list posts or custom post types. `page` is bounded from 1 to 10,000 (default `1`), `per_page` from 1 to 50 (default `10`), and `status` must be one of `publish`, `future`, `draft`, `pending`, or `private` (default `publish`). Pagination reports the selected page and size, total matching pages, total page count, and status.

Each returned item contains only the page ID, sanitized title and slug, status, author ID, date, modified date, permalink, parent ID, and menu order. Missing text or URL metadata is `null`. A successful empty query returns `pages: []`; invalid parameters or other errors return a safe message with `pages: null`. The route only reads through WordPress APIs and cannot create, update, publish, trash, or delete pages. It uses no direct SQL. The project owner reports that this route has been tested against the local WordPress installation.

## Installed themes endpoint

The plugin provides an administrator-only read endpoint:

```text
GET /wp-json/sitepilot/v1/themes
```

It uses WordPress theme APIs to enumerate installed themes and identify the active stylesheet. Child themes include their parent theme's stylesheet identifier in `template`; themes without a parent return `null` there. Each theme contains only a relative `stylesheet` identifier when safe, its name, version, active/inactive status, description, author, and optional `template`. Missing optional metadata is `null`. A successful site with no installed themes returns `{"themes": []}`. The endpoint changes no theme state and does not use direct SQL.

Example:

```json
{
  "themes": [
    {
      "stylesheet": "sitepilot-child",
      "name": "SitePilot Child",
      "version": "1.0.0",
      "status": "active",
      "description": "A child theme.",
      "author": "Example Author",
      "template": "sitepilot-parent"
    }
  ]
}
```

The project owner reports that this route has been tested against the local WordPress installation.

## Users endpoint

The plugin provides an administrator-only, read-only endpoint:

```text
GET /wp-json/sitepilot/v1/users
```

It uses `WP_User_Query` with `page` from 1 to 10,000 (default `1`) and `per_page` from 1 to 50 (default `10`). Pagination reports the current page, page size, total matching users, and total pages. The response allowlist contains only user ID, username, display name, role identifiers, registration date, and description. Email-shaped usernames/display names are returned as `null`; email addresses in descriptions are replaced with `[email removed]`. Missing optional values use `null`; successful empty results use `users: []`; invalid pagination returns a structured safe error. WordPress handles authentication failures with its standard REST error response, which the Python tool converts to `users: null` and a safe message.

The route requires an authenticated user with `manage_options`. It performs no user changes and uses the WordPress API rather than direct SQL. It is implemented and syntax-checked in the plugin source, but has not yet been installed or runtime-tested in WordPress.

## Media endpoint

The plugin provides an administrator-only, read-only endpoint:

```text
GET /wp-json/sitepilot/v1/media
```

It uses `WP_Query` restricted to attachment records, with `page` from 1 to 10,000 (default `1`) and `per_page` from 1 to 50 (default `10`). Pagination totals come from the same query. The response allowlist contains attachment ID, title, slug, filename, MIME type, media type, dates, alt text, caption, description, and public source URL. The filename is extracted as a basename only; absolute paths and path-like text are suppressed. Source URLs with query strings or fragments are omitted to avoid exposing signed or token-bearing URLs. Only the designated alt-text metadata key is read, and arbitrary attachment metadata and file contents are never returned.

Image, video, audio, and generic files are classified without assuming all attachments are images. Missing optional fields use `null`; an empty library returns `media: []`; invalid pagination returns a structured safe error. The route requires an authenticated user with `manage_options` and does not alter attachments or files. It is implemented and syntax-checked in source, but has not yet been installed or runtime-tested in WordPress.

## Tags endpoint

The plugin provides an administrator-only, read-only endpoint:

```text
GET /wp-json/sitepilot/v1/tags
```

It uses WordPress term APIs with the taxonomy fixed to `post_tag`; callers cannot select another taxonomy or pass arbitrary query arguments. Empty tags are included. `page` is bounded from 1 to 10,000 (default `1`) and `per_page` from 1 to 50 (default `10`). Pagination totals count the complete built-in tag taxonomy, and items use a stable term-ID ordering.

Each item contains only term ID, sanitized name, slug, plain-text description, and post count. No arbitrary term metadata is read or returned. Missing descriptions are `null`; a successful empty query returns `tags: []`. Invalid input or a safe retrieval failure returns `tags: null` with a structured message. The route requires `manage_options`, is GET-only, and uses WordPress APIs without changing terms or using direct SQL. It is source-implemented and syntax-checked but has not been installed or runtime-tested in WordPress.

## Categories endpoint

The plugin provides an administrator-only, read-only endpoint:

```text
GET /wp-json/sitepilot/v1/categories
```

It uses WordPress term APIs with the taxonomy fixed to `category`; callers cannot select another taxonomy or pass arbitrary query arguments. Empty categories are included. `page` is bounded from 1 to 10,000 (default `1`) and `per_page` from 1 to 50 (default `10`). The endpoint returns pagination totals for the complete built-in category taxonomy and uses a stable term-ID ordering.

Each item contains only term ID, sanitized name, slug, plain-text description, parent ID, and post count. No arbitrary term metadata is read or returned. A top-level category has `parent_id: 0`; an empty result returns `categories: []`. Invalid input or a safe retrieval failure returns `categories: null` with a structured message. The route requires `manage_options` and uses WordPress APIs; it does not change terms or use direct SQL. The route is source-implemented and syntax-checked but has not been installed or runtime-tested in WordPress.

## Comments endpoint

The plugin provides an administrator-only read endpoint:

```text
GET /wp-json/sitepilot/v1/comments
```

It uses `WP_Comment_Query` with `page` from 1 to 10,000 (default `1`), `per_page` from 1 to 50 (default `10`), and `status` restricted to `approved`, `pending`, `spam`, or `trash` (default `approved`). For WordPress-native query values, `approved` maps to `approve` and `pending` maps to `hold`; `spam` and `trash` map directly. Pagination is computed from that filtered query.

Each comment contains only ID, post ID, author name, date, plain-text content, normalized status, and type. The endpoint does not read or return author email, author IP, user agent, cookies, or comment metadata. HTML is stripped from content, email-shaped text is redacted, and optional text fields may be `null`. A successful empty query returns `comments: []`; invalid input returns a safe structured error with `comments: null`. It is GET-only, requires `manage_options`, uses WordPress APIs, and performs no content changes or direct SQL. This route is source-implemented and syntax-checked, but has not been installed or runtime-tested in WordPress.

## Security and limitations

- Access is restricted by a REST permission callback using `current_user_can( 'manage_options' )`.
- Responses contain only the documented status, site-information, plugin, theme, post, page, user, media, or comment fields. They do not return credentials, private metadata, absolute filesystem paths, or secret configuration values.
- This foundation does not provide arbitrary PHP or shell execution, file access, database operations, audit logging, approvals, or site-management tools.
- No external APIs or package dependencies are used.
- The project owner reports runtime testing of the existing status, site-info, plugins, themes, posts, and pages routes. The users, media, comments, categories, and tags routes are source-implemented and syntax-checked but have not yet been runtime-tested. Builder and other integration compatibility is not claimed.

See [`../project-docs/SECURITY.md`](../project-docs/SECURITY.md) for the project's broader security requirements.
