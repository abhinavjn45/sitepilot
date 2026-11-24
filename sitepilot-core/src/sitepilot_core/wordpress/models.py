"""Validated response model for the SitePilot status endpoint."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import urlsplit

from sitepilot_core.errors import SiteConnectionError

_VERSION_PATTERN = re.compile(
    r"[0-9]+(?:\.[0-9]+){1,3}(?:-?(?:alpha|beta|rc|dev|a|b|pre|preview)[0-9]*(?:\.[0-9]+)?)?",
    re.IGNORECASE,
)
_EMAIL_PATTERN = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
_ABSOLUTE_PATH_PATTERN = re.compile(
    r"(?:(?<![A-Za-z0-9])[A-Za-z]:[\\/]|\\\\|(?:^|[\s('\"=:])/(?!/))"
)

DEFAULT_POST_PAGE = 1
DEFAULT_POSTS_PER_PAGE = 10
MAX_POSTS_PER_PAGE = 50
MAX_POST_PAGE = 10_000
SUPPORTED_POST_STATUSES = frozenset({"publish", "future", "draft", "pending", "private"})
DEFAULT_USERS_PER_PAGE = 10
MAX_USERS_PER_PAGE = 50
MAX_USER_PAGE = 10_000
DEFAULT_MEDIA_PER_PAGE = 10
MAX_MEDIA_PER_PAGE = 50
MAX_MEDIA_PAGE = 10_000
DEFAULT_COMMENTS_PER_PAGE = 10
MAX_COMMENTS_PER_PAGE = 50
MAX_COMMENT_PAGE = 10_000
SUPPORTED_COMMENT_STATUSES = frozenset({"approved", "pending", "spam", "trash"})
DEFAULT_CATEGORIES_PER_PAGE = 10
MAX_CATEGORIES_PER_PAGE = 50
MAX_CATEGORY_PAGE = 10_000
DEFAULT_TAGS_PER_PAGE = 10
MAX_TAGS_PER_PAGE = 50
MAX_TAG_PAGE = 10_000


def validate_post_query(page: Any, per_page: Any, status: Any) -> str | None:
    """Return a safe validation error, or None when a post query is in bounds."""
    if type(page) is not int or not 1 <= page <= MAX_POST_PAGE:
        return f"Page must be an integer from 1 to {MAX_POST_PAGE}."
    if type(per_page) is not int or not 1 <= per_page <= MAX_POSTS_PER_PAGE:
        return f"per_page must be an integer from 1 to {MAX_POSTS_PER_PAGE}."
    if not isinstance(status, str) or status not in SUPPORTED_POST_STATUSES:
        return "Status must be one of the supported WordPress post statuses."
    return None


def validate_page_query(page: Any, per_page: Any, status: Any) -> str | None:
    """Return a safe validation error, or None when a page query is in bounds."""
    if type(page) is not int or not 1 <= page <= MAX_POST_PAGE:
        return f"Page must be an integer from 1 to {MAX_POST_PAGE}."
    if type(per_page) is not int or not 1 <= per_page <= MAX_POSTS_PER_PAGE:
        return f"per_page must be an integer from 1 to {MAX_POSTS_PER_PAGE}."
    if not isinstance(status, str) or status not in SUPPORTED_POST_STATUSES:
        return "Status must be one of the supported WordPress page statuses."
    return None


def validate_user_query(page: Any, per_page: Any) -> str | None:
    """Return a safe validation error, or None for a bounded user query."""
    if type(page) is not int or not 1 <= page <= MAX_USER_PAGE:
        return f"Page must be an integer from 1 to {MAX_USER_PAGE}."
    if type(per_page) is not int or not 1 <= per_page <= MAX_USERS_PER_PAGE:
        return f"per_page must be an integer from 1 to {MAX_USERS_PER_PAGE}."
    return None


def validate_media_query(page: Any, per_page: Any) -> str | None:
    """Return a safe validation error, or None for a bounded media query."""
    if type(page) is not int or not 1 <= page <= MAX_MEDIA_PAGE:
        return f"Page must be an integer from 1 to {MAX_MEDIA_PAGE}."
    if type(per_page) is not int or not 1 <= per_page <= MAX_MEDIA_PER_PAGE:
        return f"per_page must be an integer from 1 to {MAX_MEDIA_PER_PAGE}."
    return None


def validate_comment_query(page: Any, per_page: Any, status: Any) -> str | None:
    """Return a safe validation error, or None for a bounded comment query."""
    if type(page) is not int or not 1 <= page <= MAX_COMMENT_PAGE:
        return f"Page must be an integer from 1 to {MAX_COMMENT_PAGE}."
    if type(per_page) is not int or not 1 <= per_page <= MAX_COMMENTS_PER_PAGE:
        return f"per_page must be an integer from 1 to {MAX_COMMENTS_PER_PAGE}."
    if not isinstance(status, str) or status not in SUPPORTED_COMMENT_STATUSES:
        return "Status must be one of approved, pending, spam, or trash."
    return None


def validate_category_query(page: Any, per_page: Any) -> str | None:
    """Return a safe validation error, or None for a bounded category query."""
    if type(page) is not int or not 1 <= page <= MAX_CATEGORY_PAGE:
        return f"Page must be an integer from 1 to {MAX_CATEGORY_PAGE}."
    if type(per_page) is not int or not 1 <= per_page <= MAX_CATEGORIES_PER_PAGE:
        return f"per_page must be an integer from 1 to {MAX_CATEGORIES_PER_PAGE}."
    return None


def validate_tag_query(page: Any, per_page: Any) -> str | None:
    """Return a safe validation error, or None for a bounded tag query."""
    if type(page) is not int or not 1 <= page <= MAX_TAG_PAGE:
        return f"Page must be an integer from 1 to {MAX_TAG_PAGE}."
    if type(per_page) is not int or not 1 <= per_page <= MAX_TAGS_PER_PAGE:
        return f"per_page must be an integer from 1 to {MAX_TAGS_PER_PAGE}."
    return None


@dataclass(frozen=True, slots=True)
class SiteStatus:
    """Non-sensitive version information returned by the connector."""

    plugin_name: str
    plugin_version: str
    wordpress_version: str
    php_version: str
    status: str

    @classmethod
    def from_payload(cls, payload: Any) -> SiteStatus:
        """Validate the endpoint's JSON shape and allowlisted fields."""
        required = {
            "plugin_name",
            "plugin_version",
            "wordpress_version",
            "php_version",
            "status",
        }
        if not isinstance(payload, dict) or set(payload) != required:
            raise SiteConnectionError("The WordPress status response has an unexpected format.")
        if any(not isinstance(payload[key], str) for key in required):
            raise SiteConnectionError("The WordPress status response has an unexpected format.")
        if any(not payload[key] or len(payload[key]) > 64 for key in required):
            raise SiteConnectionError("The WordPress status response has invalid values.")
        if payload["status"] != "ok" or payload["plugin_name"] != "SitePilot":
            raise SiteConnectionError("The WordPress status response did not pass validation.")
        for field in ("plugin_version", "wordpress_version", "php_version"):
            if _VERSION_PATTERN.fullmatch(payload[field]) is None:
                raise SiteConnectionError("The WordPress status response contains an invalid version value.")
        return cls(
            plugin_name=payload["plugin_name"],
            plugin_version=payload["plugin_version"],
            wordpress_version=payload["wordpress_version"],
            php_version=payload["php_version"],
            status=payload["status"],
        )


@dataclass(frozen=True, slots=True)
class SiteInfo:
    """Allowlisted, non-sensitive general site information."""

    site_name: str | None
    site_description: str | None
    home_url: str | None
    site_url: str | None
    wordpress_version: str
    php_version: str
    timezone: str | None
    gmt_offset: float | None
    locale: str | None
    plugin_version: str

    @classmethod
    def from_payload(cls, payload: Any) -> SiteInfo:
        """Validate the site-info response and discard no unexpected fields silently."""
        required = {"wordpress_version", "php_version", "plugin_version"}
        optional = {
            "site_name",
            "site_description",
            "home_url",
            "site_url",
            "timezone",
            "gmt_offset",
            "locale",
        }
        if (
            not isinstance(payload, dict)
            or not required.issubset(payload)
            or not set(payload).issubset(required | optional)
        ):
            raise SiteConnectionError("The WordPress site information response has an unexpected format.")

        versions: dict[str, str] = {}
        for field in ("wordpress_version", "php_version", "plugin_version"):
            value = payload[field]
            if not isinstance(value, str) or len(value) > 64 or _VERSION_PATTERN.fullmatch(value) is None:
                raise SiteConnectionError("The WordPress site information response contains an invalid version.")
            versions[field] = value

        text_values = {
            "site_name": _optional_text(payload.get("site_name"), 512),
            "site_description": _optional_text(payload.get("site_description"), 2048),
            "timezone": _optional_text(payload.get("timezone"), 128),
            "locale": _optional_text(payload.get("locale"), 64),
        }
        home_url = _optional_url(payload.get("home_url"))
        site_url = _optional_url(payload.get("site_url"))
        gmt_offset = payload.get("gmt_offset")
        if gmt_offset is not None:
            if isinstance(gmt_offset, bool) or not isinstance(gmt_offset, (int, float)):
                raise SiteConnectionError("The WordPress site information response contains an invalid GMT offset.")
            if not math.isfinite(gmt_offset) or not -14 <= gmt_offset <= 14:
                raise SiteConnectionError("The WordPress site information response contains an invalid GMT offset.")
            gmt_offset = float(gmt_offset)

        return cls(
            **text_values,
            home_url=home_url,
            site_url=site_url,
            wordpress_version=versions["wordpress_version"],
            php_version=versions["php_version"],
            gmt_offset=gmt_offset,
            plugin_version=versions["plugin_version"],
        )


def _optional_text(value: Any, max_length: int) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > max_length:
        raise SiteConnectionError("The WordPress site information response contains an invalid text value.")
    if any(ord(character) < 32 and character not in "\n\t" for character in value):
        raise SiteConnectionError("The WordPress site information response contains an invalid text value.")
    normalized = value.strip()
    return normalized or None


def _optional_url(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 2048:
        raise SiteConnectionError("The WordPress site information response contains an invalid URL.")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port  # Force validation of malformed ports.
    except ValueError:
        raise SiteConnectionError("The WordPress site information response contains an invalid URL.") from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
        or any(ord(character) < 32 or character.isspace() for character in value)
    ):
        raise SiteConnectionError("The WordPress site information response contains an invalid URL.")
    return value


@dataclass(frozen=True, slots=True)
class PluginMetadata:
    """Allowlisted public management metadata for one installed plugin."""

    plugin_file: str | None
    name: str | None
    version: str | None
    status: str
    description: str | None
    author: str | None


@dataclass(frozen=True, slots=True)
class PluginList:
    """Validated metadata for the installed plugins returned by SitePilot Connect."""

    plugins: tuple[PluginMetadata, ...]

    @classmethod
    def from_payload(cls, payload: Any) -> PluginList:
        """Validate the exact response shape and reject unexpected fields."""
        if not isinstance(payload, dict) or set(payload) != {"plugins"}:
            raise SiteConnectionError("The WordPress plugin list response has an unexpected format.")
        entries = payload["plugins"]
        if not isinstance(entries, list) or len(entries) > 500:
            raise SiteConnectionError("The WordPress plugin list response has an invalid plugin list.")

        required_fields = {"status"}
        expected_fields = {
            "plugin_file",
            "name",
            "version",
            "status",
            "description",
            "author",
        }
        plugins: list[PluginMetadata] = []
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not required_fields.issubset(entry)
                or not set(entry).issubset(expected_fields)
            ):
                raise SiteConnectionError("The WordPress plugin list response has an invalid plugin entry.")
            status = entry["status"]
            if not isinstance(status, str) or status not in {"active", "inactive"}:
                raise SiteConnectionError("The WordPress plugin list response contains an invalid plugin status.")
            plugins.append(
                PluginMetadata(
                    plugin_file=_optional_plugin_file(entry.get("plugin_file")),
                    name=_optional_text(entry.get("name"), 512),
                    version=_optional_text(entry.get("version"), 128),
                    status=status,
                    description=_optional_text(entry.get("description"), 4096),
                    author=_optional_text(entry.get("author"), 512),
                )
            )

        return cls(plugins=tuple(plugins))


def _optional_plugin_file(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 512 or re.fullmatch(r"[A-Za-z0-9 _./-]+", value) is None:
        raise SiteConnectionError("The WordPress plugin list response contains an invalid plugin identifier.")
    if value.startswith("/") or any(segment in {"", ".", ".."} for segment in value.split("/")):
        raise SiteConnectionError("The WordPress plugin list response contains an invalid plugin identifier.")
    return value


@dataclass(frozen=True, slots=True)
class ThemeMetadata:
    """Allowlisted public management metadata for one installed theme."""

    stylesheet: str | None
    name: str | None
    version: str | None
    status: str
    description: str | None
    author: str | None
    template: str | None


@dataclass(frozen=True, slots=True)
class ThemeList:
    """Validated metadata for the installed themes returned by SitePilot Connect."""

    themes: tuple[ThemeMetadata, ...]

    @classmethod
    def from_payload(cls, payload: Any) -> ThemeList:
        """Validate the exact response shape and reject unexpected fields."""
        if not isinstance(payload, dict) or set(payload) != {"themes"}:
            raise SiteConnectionError("The WordPress theme list response has an unexpected format.")
        entries = payload["themes"]
        if not isinstance(entries, list) or len(entries) > 500:
            raise SiteConnectionError("The WordPress theme list response has an invalid theme list.")

        required_fields = {"stylesheet", "status"}
        expected_fields = required_fields | {"name", "version", "description", "author", "template"}
        themes: list[ThemeMetadata] = []
        for entry in entries:
            if (
                not isinstance(entry, dict)
                or not required_fields.issubset(entry)
                or not set(entry).issubset(expected_fields)
            ):
                raise SiteConnectionError("The WordPress theme list response has an invalid theme entry.")
            status = entry["status"]
            if not isinstance(status, str) or status not in {"active", "inactive"}:
                raise SiteConnectionError("The WordPress theme list response contains an invalid theme status.")
            themes.append(
                ThemeMetadata(
                    stylesheet=_optional_theme_identifier(entry.get("stylesheet")),
                    name=_optional_text(entry.get("name"), 512),
                    version=_optional_text(entry.get("version"), 128),
                    status=status,
                    description=_optional_text(entry.get("description"), 4096),
                    author=_optional_text(entry.get("author"), 512),
                    template=_optional_theme_identifier(entry.get("template")),
                )
            )

        return cls(themes=tuple(themes))


def _optional_theme_identifier(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 255:
        raise SiteConnectionError("The WordPress theme list response contains an invalid theme identifier.")
    if re.fullmatch(r"[A-Za-z0-9 _.-]+", value) is None or value in {".", ".."}:
        raise SiteConnectionError("The WordPress theme list response contains an invalid theme identifier.")
    return value


@dataclass(frozen=True, slots=True)
class PostMetadata:
    """Allowlisted metadata for one WordPress post."""

    id: int
    title: str | None
    slug: str | None
    status: str
    author_id: int
    date: str | None
    modified: str | None
    link: str | None
    categories: tuple[int, ...]
    tags: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class PostPagination:
    """Pagination data for the matching post query."""

    page: int
    per_page: int
    total_items: int
    total_pages: int
    status: str


@dataclass(frozen=True, slots=True)
class PostList:
    """Validated posts and pagination returned by the connector."""

    posts: tuple[PostMetadata, ...]
    pagination: PostPagination

    @classmethod
    def from_payload(cls, payload: Any) -> PostList:
        """Validate the complete allowlisted response and post metadata."""
        expected_root = {"connection_status", "posts", "pagination", "message"}
        if not isinstance(payload, dict) or set(payload) != expected_root:
            raise SiteConnectionError("The WordPress post list response has an unexpected format.")
        if payload["connection_status"] != "connected":
            raise SiteConnectionError("The WordPress post list response did not pass validation.")
        message = payload["message"]
        if not isinstance(message, str) or len(message) > 256:
            raise SiteConnectionError("The WordPress post list response has an invalid message.")

        pagination = _parse_post_pagination(payload["pagination"])
        raw_posts = payload["posts"]
        if not isinstance(raw_posts, list) or len(raw_posts) > pagination.per_page:
            raise SiteConnectionError("The WordPress post list response has an invalid posts collection.")
        posts = tuple(_parse_post(item) for item in raw_posts)
        return cls(posts=posts, pagination=pagination)


@dataclass(frozen=True, slots=True)
class PageMetadata:
    """Allowlisted metadata for one WordPress page."""

    id: int
    title: str | None
    slug: str | None
    status: str
    author_id: int
    date: str | None
    modified: str | None
    link: str | None
    parent_id: int
    menu_order: int


@dataclass(frozen=True, slots=True)
class PagePagination:
    """Pagination data for the matching WordPress page query."""

    page: int
    per_page: int
    total_items: int
    total_pages: int
    status: str


@dataclass(frozen=True, slots=True)
class PageList:
    """Validated pages and pagination returned by SitePilot Connect."""

    pages: tuple[PageMetadata, ...]
    pagination: PagePagination

    @classmethod
    def from_payload(cls, payload: Any) -> PageList:
        """Validate the exact response shape and allowlisted page metadata."""
        expected_root = {"connection_status", "pages", "pagination", "message"}
        if not isinstance(payload, dict) or set(payload) != expected_root:
            raise SiteConnectionError("The WordPress page list response has an unexpected format.")
        if payload["connection_status"] != "connected":
            raise SiteConnectionError("The WordPress page list response did not pass validation.")
        message = payload["message"]
        if not isinstance(message, str) or len(message) > 256:
            raise SiteConnectionError("The WordPress page list response has an invalid message.")

        pagination = _parse_page_pagination(payload["pagination"])
        raw_pages = payload["pages"]
        if not isinstance(raw_pages, list) or len(raw_pages) > pagination.per_page:
            raise SiteConnectionError("The WordPress page list response has an invalid pages collection.")
        pages = tuple(_parse_page(item) for item in raw_pages)
        return cls(pages=pages, pagination=pagination)


@dataclass(frozen=True, slots=True)
class UserMetadata:
    """Allowlisted public-facing metadata for one WordPress user."""

    id: int
    username: str | None
    display_name: str | None
    roles: tuple[str, ...]
    registered: str | None
    description: str | None


@dataclass(frozen=True, slots=True)
class UserPagination:
    """Pagination metadata for a WordPress user query."""

    page: int
    per_page: int
    total_items: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class UserList:
    """Validated user metadata and pagination from SitePilot Connect."""

    users: tuple[UserMetadata, ...]
    pagination: UserPagination

    @classmethod
    def from_payload(cls, payload: Any) -> UserList:
        """Validate the complete, privacy-limited user listing response."""
        expected_root = {"connection_status", "users", "pagination", "message"}
        if not isinstance(payload, dict) or set(payload) != expected_root:
            raise SiteConnectionError("The WordPress user list response has an unexpected format.")
        if payload["connection_status"] != "connected":
            raise SiteConnectionError("The WordPress user list response did not pass validation.")
        if not isinstance(payload["message"], str) or len(payload["message"]) > 256:
            raise SiteConnectionError("The WordPress user list response has an invalid message.")

        pagination = _parse_user_pagination(payload["pagination"])
        raw_users = payload["users"]
        if not isinstance(raw_users, list) or len(raw_users) > pagination.per_page:
            raise SiteConnectionError("The WordPress user list response has an invalid users collection.")
        users = tuple(_parse_user(item) for item in raw_users)
        return cls(users=users, pagination=pagination)


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    """Allowlisted metadata for one WordPress media attachment."""

    id: int
    title: str | None
    slug: str | None
    filename: str | None
    mime_type: str | None
    media_type: str
    date: str | None
    modified: str | None
    alt_text: str | None
    caption: str | None
    description: str | None
    source_url: str | None


@dataclass(frozen=True, slots=True)
class MediaPagination:
    """Pagination metadata for a WordPress attachment query."""

    page: int
    per_page: int
    total_items: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class MediaList:
    """Validated media attachment metadata and pagination."""

    media: tuple[MediaMetadata, ...]
    pagination: MediaPagination

    @classmethod
    def from_payload(cls, payload: Any) -> MediaList:
        """Validate exact response shape and the allowlisted attachment fields."""
        expected_root = {"connection_status", "media", "pagination", "message"}
        if not isinstance(payload, dict) or set(payload) != expected_root:
            raise SiteConnectionError("The WordPress media list response has an unexpected format.")
        if payload["connection_status"] != "connected":
            raise SiteConnectionError("The WordPress media list response did not pass validation.")
        if not isinstance(payload["message"], str) or len(payload["message"]) > 256:
            raise SiteConnectionError("The WordPress media list response has an invalid message.")
        pagination = _parse_media_pagination(payload["pagination"])
        raw_media = payload["media"]
        if not isinstance(raw_media, list) or len(raw_media) > pagination.per_page:
            raise SiteConnectionError("The WordPress media list response has an invalid media collection.")
        return cls(media=tuple(_parse_media(item) for item in raw_media), pagination=pagination)


@dataclass(frozen=True, slots=True)
class CommentMetadata:
    """Allowlisted text and identifiers for one WordPress comment."""

    id: int
    post_id: int
    author_name: str | None
    date: str | None
    content: str | None
    status: str
    type: str


@dataclass(frozen=True, slots=True)
class CommentPagination:
    """Pagination metadata for a filtered WordPress comment query."""

    page: int
    per_page: int
    total_items: int
    total_pages: int
    status: str


@dataclass(frozen=True, slots=True)
class CommentList:
    """Validated comments and pagination from SitePilot Connect."""

    comments: tuple[CommentMetadata, ...]
    pagination: CommentPagination

    @classmethod
    def from_payload(cls, payload: Any) -> CommentList:
        """Validate exact response shape and safe comment metadata."""
        expected_root = {"connection_status", "comments", "pagination", "message"}
        if not isinstance(payload, dict) or set(payload) != expected_root:
            raise SiteConnectionError("The WordPress comment list response has an unexpected format.")
        if payload["connection_status"] != "connected":
            raise SiteConnectionError("The WordPress comment list response did not pass validation.")
        if not isinstance(payload["message"], str) or len(payload["message"]) > 256:
            raise SiteConnectionError("The WordPress comment list response has an invalid message.")
        pagination = _parse_comment_pagination(payload["pagination"])
        raw_comments = payload["comments"]
        if not isinstance(raw_comments, list) or len(raw_comments) > pagination.per_page:
            raise SiteConnectionError("The WordPress comment list response has an invalid comments collection.")
        comments = tuple(_parse_comment(item) for item in raw_comments)
        if any(comment.status != pagination.status for comment in comments):
            raise SiteConnectionError("The WordPress comment list response does not match its status filter.")
        return cls(comments=comments, pagination=pagination)


@dataclass(frozen=True, slots=True)
class CategoryMetadata:
    """Allowlisted fields for one built-in WordPress category term."""

    id: int
    name: str | None
    slug: str | None
    description: str | None
    parent_id: int
    count: int


@dataclass(frozen=True, slots=True)
class CategoryPagination:
    """Pagination metadata for the built-in category taxonomy."""

    page: int
    per_page: int
    total_items: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class CategoryList:
    """Validated category terms and pagination returned by SitePilot Connect."""

    categories: tuple[CategoryMetadata, ...]
    pagination: CategoryPagination

    @classmethod
    def from_payload(cls, payload: Any) -> CategoryList:
        """Validate exact response shape and category fields."""
        expected = {"connection_status", "categories", "pagination", "message"}
        if not isinstance(payload, dict) or set(payload) != expected:
            raise SiteConnectionError("The WordPress category list response has an unexpected format.")
        if payload["connection_status"] != "connected":
            raise SiteConnectionError("The WordPress category list response did not pass validation.")
        if not isinstance(payload["message"], str) or len(payload["message"]) > 256:
            raise SiteConnectionError("The WordPress category list response has an invalid message.")
        pagination = _parse_category_pagination(payload["pagination"])
        entries = payload["categories"]
        if not isinstance(entries, list) or len(entries) > pagination.per_page:
            raise SiteConnectionError("The WordPress category list response has an invalid categories collection.")
        return cls(categories=tuple(_parse_category(entry) for entry in entries), pagination=pagination)


def _parse_category_pagination(value: Any) -> CategoryPagination:
    expected = {"page", "per_page", "total_items", "total_pages"}
    if not isinstance(value, dict) or set(value) != expected:
        raise SiteConnectionError("The WordPress category list response has invalid pagination metadata.")
    page = value["page"]
    per_page = value["per_page"]
    total_items = value["total_items"]
    total_pages = value["total_pages"]
    if (
        validate_category_query(page, per_page) is not None
        or not _is_nonnegative_int(total_items)
        or total_items > 2**63 - 1
        or not _is_nonnegative_int(total_pages)
    ):
        raise SiteConnectionError("The WordPress category list response has invalid pagination metadata.")
    expected_pages = math.ceil(total_items / per_page) if total_items else 0
    if total_pages != expected_pages:
        raise SiteConnectionError("The WordPress category list response has inconsistent pagination metadata.")
    return CategoryPagination(page, per_page, total_items, total_pages)


def _parse_category(value: Any) -> CategoryMetadata:
    required = {"id", "parent_id", "count"}
    optional = {"name", "slug", "description"}
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(required | optional):
        raise SiteConnectionError("The WordPress category list response contains an invalid category entry.")
    term_id = value["id"]
    parent_id = value["parent_id"]
    count = value["count"]
    if (
        not _is_positive_int(term_id)
        or term_id > 2**63 - 1
        or not _is_nonnegative_int(parent_id)
        or parent_id > 2**63 - 1
        or not _is_nonnegative_int(count)
        or count > 2**63 - 1
    ):
        raise SiteConnectionError("The WordPress category list response contains invalid category metadata.")
    name = _optional_text(value.get("name"), 512)
    slug = _optional_text(value.get("slug"), 200)
    description = _optional_text(value.get("description"), 4096)
    if any(_contains_markup(text) for text in (name, slug, description) if text is not None):
        raise SiteConnectionError("The WordPress category list response contains untrusted markup.")
    if slug is not None and any(character in slug for character in ("/", "\\", "?", "#")):
        raise SiteConnectionError("The WordPress category list response contains an invalid category slug.")
    return CategoryMetadata(term_id, name, slug, description, parent_id, count)


def _contains_markup(value: str) -> bool:
    """Identify tag-shaped markup so it cannot be passed along for rendering."""
    return re.search(r"</?[A-Za-z][^>]*>", value) is not None


@dataclass(frozen=True, slots=True)
class TagMetadata:
    """Allowlisted fields for one built-in WordPress post tag."""

    id: int
    name: str | None
    slug: str | None
    description: str | None
    count: int


@dataclass(frozen=True, slots=True)
class TagPagination:
    """Pagination metadata for the built-in post_tag taxonomy."""

    page: int
    per_page: int
    total_items: int
    total_pages: int


@dataclass(frozen=True, slots=True)
class TagList:
    """Validated tag terms and pagination returned by SitePilot Connect."""

    tags: tuple[TagMetadata, ...]
    pagination: TagPagination

    @classmethod
    def from_payload(cls, payload: Any) -> TagList:
        """Validate exact response shape and allowlisted tag fields."""
        expected = {"connection_status", "tags", "pagination", "message"}
        if not isinstance(payload, dict) or set(payload) != expected:
            raise SiteConnectionError("The WordPress tag list response has an unexpected format.")
        if payload["connection_status"] != "connected":
            raise SiteConnectionError("The WordPress tag list response did not pass validation.")
        if not isinstance(payload["message"], str) or len(payload["message"]) > 256:
            raise SiteConnectionError("The WordPress tag list response has an invalid message.")
        pagination = _parse_tag_pagination(payload["pagination"])
        entries = payload["tags"]
        if not isinstance(entries, list) or len(entries) > pagination.per_page:
            raise SiteConnectionError("The WordPress tag list response has an invalid tags collection.")
        return cls(tags=tuple(_parse_tag(entry) for entry in entries), pagination=pagination)


def _parse_tag_pagination(value: Any) -> TagPagination:
    expected = {"page", "per_page", "total_items", "total_pages"}
    if not isinstance(value, dict) or set(value) != expected:
        raise SiteConnectionError("The WordPress tag list response has invalid pagination metadata.")
    page = value["page"]
    per_page = value["per_page"]
    total_items = value["total_items"]
    total_pages = value["total_pages"]
    if (
        validate_tag_query(page, per_page) is not None
        or not _is_nonnegative_int(total_items)
        or total_items > 2**63 - 1
        or not _is_nonnegative_int(total_pages)
    ):
        raise SiteConnectionError("The WordPress tag list response has invalid pagination metadata.")
    expected_pages = math.ceil(total_items / per_page) if total_items else 0
    if total_pages != expected_pages:
        raise SiteConnectionError("The WordPress tag list response has inconsistent pagination metadata.")
    return TagPagination(page, per_page, total_items, total_pages)


def _parse_tag(value: Any) -> TagMetadata:
    required = {"id", "count"}
    optional = {"name", "slug", "description"}
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(required | optional):
        raise SiteConnectionError("The WordPress tag list response contains an invalid tag entry.")
    tag_id = value["id"]
    count = value["count"]
    if (
        not _is_positive_int(tag_id)
        or tag_id > 2**63 - 1
        or not _is_nonnegative_int(count)
        or count > 2**63 - 1
    ):
        raise SiteConnectionError("The WordPress tag list response contains invalid tag metadata.")
    name = _optional_text(value.get("name"), 512)
    slug = _optional_text(value.get("slug"), 200)
    description = _optional_text(value.get("description"), 4096)
    if any(_contains_markup(text) for text in (name, slug, description) if text is not None):
        raise SiteConnectionError("The WordPress tag list response contains untrusted markup.")
    if slug is not None and any(character in slug for character in ("/", "\\", "?", "#")):
        raise SiteConnectionError("The WordPress tag list response contains an invalid tag slug.")
    return TagMetadata(tag_id, name, slug, description, count)


def _parse_comment_pagination(value: Any) -> CommentPagination:
    expected = {"page", "per_page", "total_items", "total_pages", "status"}
    if not isinstance(value, dict) or set(value) != expected:
        raise SiteConnectionError("The WordPress comment list response has invalid pagination metadata.")
    page = value["page"]
    per_page = value["per_page"]
    total_items = value["total_items"]
    total_pages = value["total_pages"]
    status = value["status"]
    if (
        validate_comment_query(page, per_page, status) is not None
        or not _is_nonnegative_int(total_items)
        or total_items > 2**63 - 1
        or not _is_nonnegative_int(total_pages)
    ):
        raise SiteConnectionError("The WordPress comment list response has invalid pagination metadata.")
    expected_pages = math.ceil(total_items / per_page) if total_items else 0
    if total_pages != expected_pages:
        raise SiteConnectionError("The WordPress comment list response has inconsistent pagination metadata.")
    return CommentPagination(page, per_page, total_items, total_pages, status)


def _parse_comment(value: Any) -> CommentMetadata:
    required = {"id", "post_id", "status", "type"}
    allowed = required | {"author_name", "date", "content"}
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(allowed):
        raise SiteConnectionError("The WordPress comment list response contains an invalid comment entry.")
    comment_id = value["id"]
    post_id = value["post_id"]
    status = value["status"]
    comment_type = value["type"]
    if (
        not _is_positive_int(comment_id)
        or comment_id > 2**63 - 1
        or not _is_positive_int(post_id)
        or post_id > 2**63 - 1
        or not isinstance(status, str)
        or status not in SUPPORTED_COMMENT_STATUSES
        or not isinstance(comment_type, str)
        or len(comment_type) > 64
        or re.fullmatch(r"[A-Za-z0-9_-]+", comment_type) is None
    ):
        raise SiteConnectionError("The WordPress comment list response contains invalid comment metadata.")
    return CommentMetadata(
        id=comment_id,
        post_id=post_id,
        author_name=_optional_comment_text(value.get("author_name"), 512),
        date=_optional_iso_datetime(value.get("date")),
        content=_optional_comment_text(value.get("content"), 4096),
        status=status,
        type=comment_type,
    )


def _optional_comment_text(value: Any, maximum: int) -> str | None:
    text = _optional_text(value, maximum)
    if text is not None and _EMAIL_PATTERN.search(text):
        return _EMAIL_PATTERN.sub("[email removed]", text)
    return text


def _parse_media_pagination(value: Any) -> MediaPagination:
    expected = {"page", "per_page", "total_items", "total_pages"}
    if not isinstance(value, dict) or set(value) != expected:
        raise SiteConnectionError("The WordPress media list response has invalid pagination metadata.")
    page = value["page"]
    per_page = value["per_page"]
    total_items = value["total_items"]
    total_pages = value["total_pages"]
    if (
        validate_media_query(page, per_page) is not None
        or not _is_nonnegative_int(total_items)
        or total_items > 2**63 - 1
        or not _is_nonnegative_int(total_pages)
    ):
        raise SiteConnectionError("The WordPress media list response has invalid pagination metadata.")
    expected_pages = math.ceil(total_items / per_page) if total_items else 0
    if total_pages != expected_pages:
        raise SiteConnectionError("The WordPress media list response has inconsistent pagination metadata.")
    return MediaPagination(page, per_page, total_items, total_pages)


def _parse_media(value: Any) -> MediaMetadata:
    expected = {
        "id", "title", "slug", "filename", "mime_type", "media_type", "date", "modified",
        "alt_text", "caption", "description", "source_url",
    }
    required = {"id", "media_type"}
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(expected):
        raise SiteConnectionError("The WordPress media list response contains an invalid attachment entry.")
    attachment_id = value["id"]
    media_type = value["media_type"]
    if (
        not _is_positive_int(attachment_id)
        or attachment_id > 2**63 - 1
        or not isinstance(media_type, str)
        or media_type not in {"image", "video", "audio", "file"}
    ):
        raise SiteConnectionError("The WordPress media list response contains invalid attachment metadata.")

    mime_type = _optional_mime_type(value.get("mime_type"))
    if mime_type is not None:
        expected_type = "image" if mime_type.startswith("image/") else (
            "video" if mime_type.startswith("video/") else "audio" if mime_type.startswith("audio/") else "file"
        )
        if media_type != expected_type:
            raise SiteConnectionError("The WordPress media list response has inconsistent media types.")

    return MediaMetadata(
        id=attachment_id,
        title=_optional_media_text(value.get("title"), 1024),
        slug=_optional_media_text(value.get("slug"), 512),
        filename=_optional_filename(value.get("filename")),
        mime_type=mime_type,
        media_type=media_type,
        date=_optional_iso_datetime(value.get("date")),
        modified=_optional_iso_datetime(value.get("modified")),
        alt_text=_optional_media_text(value.get("alt_text"), 2048),
        caption=_optional_media_text(value.get("caption"), 4096),
        description=_optional_media_text(value.get("description"), 4096),
        source_url=_optional_media_url(value.get("source_url")),
    )


def _optional_media_text(value: Any, maximum: int) -> str | None:
    text = _optional_text(value, maximum)
    if text is not None and _ABSOLUTE_PATH_PATTERN.search(text):
        return None
    return text


def _optional_filename(value: Any) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or not value
        or len(value) > 255
        or any(char in value for char in ("/", "\\", ":", "<", ">", '"', "|", "?", "*"))
        or any(ord(char) < 32 for char in value)
        or not value.strip()
        or value in {".", ".."}
    ):
        raise SiteConnectionError("The WordPress media list response contains an invalid filename.")
    return value


def _optional_media_url(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise SiteConnectionError("The WordPress media list response contains an invalid source URL.")
    try:
        parsed = urlsplit(value)
    except ValueError:
        raise SiteConnectionError("The WordPress media list response contains an invalid source URL.") from None
    if parsed.query or parsed.fragment:
        raise SiteConnectionError("The WordPress media list response contains an unsafe source URL.")
    return _optional_post_url(value)


def _optional_mime_type(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 127 or re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9.+-]{0,62}/[A-Za-z0-9][A-Za-z0-9.+-]{0,62}", value
    ) is None:
        raise SiteConnectionError("The WordPress media list response contains an invalid MIME type.")
    return value.lower()


def _parse_user_pagination(value: Any) -> UserPagination:
    expected = {"page", "per_page", "total_items", "total_pages"}
    if not isinstance(value, dict) or set(value) != expected:
        raise SiteConnectionError("The WordPress user list response has invalid pagination metadata.")
    page = value["page"]
    per_page = value["per_page"]
    total_items = value["total_items"]
    total_pages = value["total_pages"]
    if (
        validate_user_query(page, per_page) is not None
        or not _is_nonnegative_int(total_items)
        or not _is_nonnegative_int(total_pages)
        or total_items > 2**63 - 1
    ):
        raise SiteConnectionError("The WordPress user list response has invalid pagination metadata.")
    expected_pages = math.ceil(total_items / per_page) if total_items else 0
    if total_pages != expected_pages:
        raise SiteConnectionError("The WordPress user list response has inconsistent pagination metadata.")
    return UserPagination(page, per_page, total_items, total_pages)


def _parse_user(value: Any) -> UserMetadata:
    required = {"id", "roles"}
    allowed = required | {"username", "display_name", "registered", "description"}
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(allowed):
        raise SiteConnectionError("The WordPress user list response contains an invalid user entry.")
    user_id = value["id"]
    if not _is_positive_int(user_id) or user_id > 2**63 - 1:
        raise SiteConnectionError("The WordPress user list response contains an invalid user identifier.")

    raw_roles = value["roles"]
    if not isinstance(raw_roles, list) or len(raw_roles) > 100:
        raise SiteConnectionError("The WordPress user list response contains invalid role metadata.")
    roles: list[str] = []
    for role in raw_roles:
        if not isinstance(role, str) or len(role) > 64 or re.fullmatch(r"[a-zA-Z0-9_-]+", role) is None:
            raise SiteConnectionError("The WordPress user list response contains invalid role metadata.")
        roles.append(role)

    return UserMetadata(
        id=user_id,
        username=_optional_user_text(value.get("username"), 60),
        display_name=_optional_user_text(value.get("display_name"), 512),
        roles=tuple(roles),
        registered=_optional_iso_datetime(value.get("registered")),
        description=_optional_user_text(value.get("description"), 4096),
    )


def _optional_user_text(value: Any, maximum: int) -> str | None:
    """Validate optional user text and suppress any value containing an email address."""
    result = _optional_text(value, maximum)
    if result is not None and _EMAIL_PATTERN.search(result):
        return None
    return result


def _parse_page_pagination(value: Any) -> PagePagination:
    expected = {"page", "per_page", "total_items", "total_pages", "status"}
    if not isinstance(value, dict) or set(value) != expected:
        raise SiteConnectionError("The WordPress page list response has invalid pagination metadata.")

    page = value["page"]
    per_page = value["per_page"]
    status = value["status"]
    total_items = value["total_items"]
    total_pages = value["total_pages"]
    if (
        validate_page_query(page, per_page, status) is not None
        or not _is_nonnegative_int(total_items)
        or not _is_nonnegative_int(total_pages)
    ):
        raise SiteConnectionError("The WordPress page list response has invalid pagination metadata.")
    expected_pages = math.ceil(total_items / per_page) if total_items else 0
    if total_pages != expected_pages or total_items > 2**63 - 1:
        raise SiteConnectionError("The WordPress page list response has inconsistent pagination metadata.")
    return PagePagination(page, per_page, total_items, total_pages, status)


def _parse_page(value: Any) -> PageMetadata:
    required = {"id", "status", "author_id", "parent_id", "menu_order"}
    optional = {"title", "slug", "date", "modified", "link"}
    allowed = required | optional
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(allowed):
        raise SiteConnectionError("The WordPress page list response contains an invalid page entry.")

    page_id = value["id"]
    author_id = value["author_id"]
    parent_id = value["parent_id"]
    menu_order = value["menu_order"]
    status = value["status"]
    if (
        not _is_positive_int(page_id)
        or page_id > 2**63 - 1
        or not _is_nonnegative_int(author_id)
        or author_id > 2**63 - 1
        or not _is_nonnegative_int(parent_id)
        or parent_id > 2**63 - 1
        or type(menu_order) is not int
        or not -(2**31) <= menu_order <= 2**31 - 1
        or not isinstance(status, str)
        or status not in SUPPORTED_POST_STATUSES
    ):
        raise SiteConnectionError("The WordPress page list response contains invalid page metadata.")

    return PageMetadata(
        id=page_id,
        title=_optional_text(value.get("title"), 1024),
        slug=_optional_text(value.get("slug"), 512),
        status=status,
        author_id=author_id,
        date=_optional_iso_datetime(value.get("date")),
        modified=_optional_iso_datetime(value.get("modified")),
        link=_optional_post_url(value.get("link")),
        parent_id=parent_id,
        menu_order=menu_order,
    )


def _parse_post_pagination(value: Any) -> PostPagination:
    expected = {"page", "per_page", "total_items", "total_pages", "status"}
    if not isinstance(value, dict) or set(value) != expected:
        raise SiteConnectionError("The WordPress post list response has invalid pagination metadata.")

    page = value["page"]
    per_page = value["per_page"]
    status = value["status"]
    query_error = validate_post_query(page, per_page, status)
    total_items = value["total_items"]
    total_pages = value["total_pages"]
    if query_error is not None or not _is_nonnegative_int(total_items) or not _is_nonnegative_int(total_pages):
        raise SiteConnectionError("The WordPress post list response has invalid pagination metadata.")
    expected_pages = math.ceil(total_items / per_page) if total_items else 0
    if total_pages != expected_pages or total_items > 2**63 - 1:
        raise SiteConnectionError("The WordPress post list response has inconsistent pagination metadata.")
    return PostPagination(page, per_page, total_items, total_pages, status)


def _parse_post(value: Any) -> PostMetadata:
    required = {"id", "status", "author_id", "categories", "tags"}
    optional = {"title", "slug", "date", "modified", "link"}
    allowed = required | optional
    if not isinstance(value, dict) or not required.issubset(value) or not set(value).issubset(allowed):
        raise SiteConnectionError("The WordPress post list response contains an invalid post entry.")

    post_id = value["id"]
    author_id = value["author_id"]
    status = value["status"]
    if (
        not _is_positive_int(post_id)
        or post_id > 2**63 - 1
        or not _is_nonnegative_int(author_id)
        or author_id > 2**63 - 1
        or not isinstance(status, str)
        or status not in SUPPORTED_POST_STATUSES
    ):
        raise SiteConnectionError("The WordPress post list response contains invalid post metadata.")

    categories = _parse_term_ids(value["categories"])
    tags = _parse_term_ids(value["tags"])
    return PostMetadata(
        id=post_id,
        title=_optional_text(value.get("title"), 1024),
        slug=_optional_text(value.get("slug"), 512),
        status=status,
        author_id=author_id,
        date=_optional_iso_datetime(value.get("date")),
        modified=_optional_iso_datetime(value.get("modified")),
        link=_optional_post_url(value.get("link")),
        categories=categories,
        tags=tags,
    )


def _parse_term_ids(value: Any) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) > 500:
        raise SiteConnectionError("The WordPress post list response contains invalid taxonomy metadata.")
    if any(not _is_positive_int(term_id) or term_id > 2**63 - 1 for term_id in value):
        raise SiteConnectionError("The WordPress post list response contains invalid taxonomy metadata.")
    return tuple(value)


def _optional_iso_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 64 or re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]+)?(?:Z|[+-][0-9]{2}:[0-9]{2})",
        value,
    ) is None:
        raise SiteConnectionError("The WordPress post list response contains an invalid date.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise SiteConnectionError("The WordPress post list response contains an invalid date.") from None
    if parsed.tzinfo is None:
        raise SiteConnectionError("The WordPress post list response contains an invalid date.")
    return value


def _optional_post_url(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 2048:
        raise SiteConnectionError("The WordPress post list response contains an invalid link.")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        parsed.port
    except ValueError:
        raise SiteConnectionError("The WordPress post list response contains an invalid link.") from None
    if (
        parsed.scheme.lower() not in {"http", "https"}
        or not parsed.netloc
        or not hostname
        or parsed.username is not None
        or parsed.password is not None
        or any(ord(character) < 32 or character.isspace() for character in value)
    ):
        raise SiteConnectionError("The WordPress post list response contains an invalid link.")
    return value


def _is_positive_int(value: Any) -> bool:
    return type(value) is int and value > 0


def _is_nonnegative_int(value: Any) -> bool:
    return type(value) is int and value >= 0
