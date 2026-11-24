"""HTTPX client for the fixed, read-only SitePilot REST routes."""

from __future__ import annotations

import errno
import json
import socket
import ssl
from typing import Any

import httpx

from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SiteConnectionError
from sitepilot_core.security.credentials import CredentialProvider
from sitepilot_core.security.tls import create_tls_verification
from sitepilot_core.wordpress.models import (
    PageList,
    MediaList,
    CommentList,
    CategoryList,
    TagList,
    PluginList,
    PostList,
    SiteInfo,
    SiteStatus,
    ThemeList,
    UserList,
    validate_page_query,
    validate_media_query,
    validate_post_query,
    validate_user_query,
    validate_comment_query,
    validate_category_query,
    validate_tag_query,
)

_STATUS_ROUTE = "/wp-json/sitepilot/v1/status"
_SITE_INFO_ROUTE = "/wp-json/sitepilot/v1/site-info"
_PLUGINS_ROUTE = "/wp-json/sitepilot/v1/plugins"
_THEMES_ROUTE = "/wp-json/sitepilot/v1/themes"
_POSTS_ROUTE = "/wp-json/sitepilot/v1/posts"
_PAGES_ROUTE = "/wp-json/sitepilot/v1/pages"
_USERS_ROUTE = "/wp-json/sitepilot/v1/users"
_MEDIA_ROUTE = "/wp-json/sitepilot/v1/media"
_COMMENTS_ROUTE = "/wp-json/sitepilot/v1/comments"
_CATEGORIES_ROUTE = "/wp-json/sitepilot/v1/categories"
_TAGS_ROUTE = "/wp-json/sitepilot/v1/tags"
_MAX_RESPONSE_BYTES = 16 * 1024
_RESPONSE_CHUNK_BYTES = 4 * 1024
_TIMEOUT_SECONDS = 5.0
_MAX_EXCEPTION_CHAIN_NODES = 16


def _collect_exception_chain(exc: BaseException) -> list[BaseException]:
    """Collect a bounded cause/context/group chain without reading exception text."""
    pending = [exc]
    visited: set[int] = set()
    chain: list[BaseException] = []
    examined = 0
    while pending and examined < _MAX_EXCEPTION_CHAIN_NODES:
        current = pending.pop()
        examined += 1
        if id(current) in visited:
            continue
        visited.add(id(current))
        chain.append(current)

        available_slots = _MAX_EXCEPTION_CHAIN_NODES - examined - len(pending)
        if available_slots <= 0:
            continue

        children: list[BaseException] = []
        if current.__cause__ is not None:
            children.append(current.__cause__)
        if current.__context__ is not None:
            children.append(current.__context__)
        if isinstance(current, BaseExceptionGroup):
            group_slots = max(0, available_slots - len(children))
            children.extend(current.exceptions[:group_slots])
        pending.extend(reversed(children[:available_slots]))
    return chain


def _is_connection_refused(exc: BaseException) -> bool:
    if isinstance(exc, ConnectionRefusedError):
        return True
    if isinstance(exc, OSError):
        return exc.errno == errno.ECONNREFUSED or getattr(exc, "winerror", None) == 10061
    return False


def _transport_failure_category(chain: list[BaseException], response_received: bool) -> str:
    """Classify a failure using exception types and numeric OS error codes only."""
    if any(isinstance(exc, ssl.SSLCertVerificationError) for exc in chain):
        return "tls_verification"
    if any(_is_connection_refused(exc) for exc in chain):
        return "connection_refused"
    if any(isinstance(exc, httpx.ConnectTimeout) or type(exc).__name__ == "ConnectTimeout" for exc in chain):
        return "connect_timeout"
    if any(isinstance(exc, socket.gaierror) for exc in chain):
        return "dns_resolution"
    if response_received:
        return "response_read"
    return "other_connection"


def _transport_failure_message(category: str, endpoint_name: str) -> str:
    """Return a fixed, safe message for a classified transport failure."""
    messages = {
        "tls_verification": "TLS certificate verification failed for the WordPress connection.",
        "connection_refused": "The WordPress server refused the connection.",
        "connect_timeout": "The connection to the WordPress server timed out.",
        "dns_resolution": "The WordPress server address could not be resolved.",
        "response_read": f"The WordPress {endpoint_name} response could not be fully read.",
        "other_connection": f"The WordPress {endpoint_name} endpoint could not be reached.",
    }
    return messages[category]


def _append_response_chunk(body: bytearray, chunk: bytes) -> None:
    """Append a chunk only when its complete size fits the response budget."""
    if len(body) + len(chunk) > _MAX_RESPONSE_BYTES:
        raise SiteConnectionError("The WordPress response exceeded the size limit.")
    body.extend(chunk)


class WordPressClient:
    """Call only fixed, read-only endpoints on the configured site."""

    def __init__(
        self,
        config: SiteConfig,
        credential_provider: CredentialProvider | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._config = config
        self._credential_provider = credential_provider
        self._transport = transport
        self._tls_verification = create_tls_verification(config.ca_cert_path)

    async def fetch_status(self) -> SiteStatus:
        """Fetch and validate the site's non-sensitive status information."""
        payload = await self._fetch_json(_STATUS_ROUTE, "status")
        return SiteStatus.from_payload(payload)

    async def fetch_site_info(self) -> SiteInfo:
        """Fetch and validate the site's non-sensitive general information."""
        payload = await self._fetch_json(_SITE_INFO_ROUTE, "site information")
        return SiteInfo.from_payload(payload)

    async def fetch_plugins(self) -> PluginList:
        """Fetch and validate the configured site's installed plugin metadata."""
        payload = await self._fetch_json(_PLUGINS_ROUTE, "plugin list")
        return PluginList.from_payload(payload)

    async def fetch_themes(self) -> ThemeList:
        """Fetch and validate the configured site's installed theme metadata."""
        payload = await self._fetch_json(_THEMES_ROUTE, "theme list")
        return ThemeList.from_payload(payload)

    async def fetch_posts(self, page: int = 1, per_page: int = 10, status: str = "publish") -> PostList:
        """Fetch one bounded page of posts with an explicitly supported status."""
        query_error = validate_post_query(page, per_page, status)
        if query_error is not None:
            raise SiteConnectionError("The requested post list parameters are invalid.")
        payload = await self._fetch_json(
            _POSTS_ROUTE,
            "post list",
            params={"page": page, "per_page": per_page, "status": status},
        )
        post_list = PostList.from_payload(payload)
        pagination = post_list.pagination
        if pagination.page != page or pagination.per_page != per_page or pagination.status != status:
            raise SiteConnectionError("The WordPress post list response does not match the requested pagination.")
        if any(post.status != status for post in post_list.posts):
            raise SiteConnectionError("The WordPress post list response does not match the requested status.")
        return post_list

    async def fetch_pages(self, page: int = 1, per_page: int = 10, status: str = "publish") -> PageList:
        """Fetch one bounded page of WordPress pages with an allowed status."""
        if validate_page_query(page, per_page, status) is not None:
            raise SiteConnectionError("The requested page list parameters are invalid.")
        payload = await self._fetch_json(
            _PAGES_ROUTE,
            "page list",
            params={"page": page, "per_page": per_page, "status": status},
        )
        page_list = PageList.from_payload(payload)
        pagination = page_list.pagination
        if pagination.page != page or pagination.per_page != per_page or pagination.status != status:
            raise SiteConnectionError("The WordPress page list response does not match the requested pagination.")
        if any(item.status != status for item in page_list.pages):
            raise SiteConnectionError("The WordPress page list response does not match the requested status.")
        return page_list

    async def fetch_users(self, page: int = 1, per_page: int = 10) -> UserList:
        """Fetch one bounded page of allowlisted WordPress user metadata."""
        if validate_user_query(page, per_page) is not None:
            raise SiteConnectionError("The requested user list parameters are invalid.")
        payload = await self._fetch_json(
            _USERS_ROUTE,
            "user list",
            params={"page": page, "per_page": per_page},
        )
        user_list = UserList.from_payload(payload)
        pagination = user_list.pagination
        if pagination.page != page or pagination.per_page != per_page:
            raise SiteConnectionError("The WordPress user list response does not match the requested pagination.")
        return user_list

    async def fetch_media(self, page: int = 1, per_page: int = 10) -> MediaList:
        """Fetch one bounded page of allowlisted WordPress attachment metadata."""
        if validate_media_query(page, per_page) is not None:
            raise SiteConnectionError("The requested media list parameters are invalid.")
        payload = await self._fetch_json(
            _MEDIA_ROUTE,
            "media list",
            params={"page": page, "per_page": per_page},
        )
        media_list = MediaList.from_payload(payload)
        pagination = media_list.pagination
        if pagination.page != page or pagination.per_page != per_page:
            raise SiteConnectionError("The WordPress media list response does not match the requested pagination.")
        return media_list

    async def fetch_comments(
        self, page: int = 1, per_page: int = 10, status: str = "approved"
    ) -> CommentList:
        """Fetch one bounded page of allowlisted comments for an approved status."""
        if validate_comment_query(page, per_page, status) is not None:
            raise SiteConnectionError("The requested comment list parameters are invalid.")
        payload = await self._fetch_json(
            _COMMENTS_ROUTE,
            "comment list",
            params={"page": page, "per_page": per_page, "status": status},
        )
        comment_list = CommentList.from_payload(payload)
        pagination = comment_list.pagination
        if pagination.page != page or pagination.per_page != per_page or pagination.status != status:
            raise SiteConnectionError("The WordPress comment list response does not match the requested query.")
        return comment_list

    async def fetch_categories(self, page: int = 1, per_page: int = 10) -> CategoryList:
        """Fetch one bounded page of the built-in WordPress category taxonomy."""
        if validate_category_query(page, per_page) is not None:
            raise SiteConnectionError("The requested category list parameters are invalid.")
        payload = await self._fetch_json(
            _CATEGORIES_ROUTE,
            "category list",
            params={"page": page, "per_page": per_page},
        )
        category_list = CategoryList.from_payload(payload)
        pagination = category_list.pagination
        if pagination.page != page or pagination.per_page != per_page:
            raise SiteConnectionError("The WordPress category list response does not match the requested pagination.")
        return category_list

    async def fetch_tags(self, page: int = 1, per_page: int = 10) -> TagList:
        """Fetch one bounded page of the built-in WordPress post_tag taxonomy."""
        if validate_tag_query(page, per_page) is not None:
            raise SiteConnectionError("The requested tag list parameters are invalid.")
        payload = await self._fetch_json(
            _TAGS_ROUTE,
            "tag list",
            params={"page": page, "per_page": per_page},
        )
        tag_list = TagList.from_payload(payload)
        pagination = tag_list.pagination
        if pagination.page != page or pagination.per_page != per_page:
            raise SiteConnectionError("The WordPress tag list response does not match the requested pagination.")
        return tag_list

    async def _fetch_json(
        self,
        route: str,
        endpoint_name: str,
        *,
        params: dict[str, int | str] | None = None,
    ) -> Any:
        """Request a fixed connector route using the client's shared protections."""
        if self._config.credential_ref is not None and not self._config.base_url.startswith("https://"):
            raise SiteConnectionError("Credentials are disabled for plain HTTP connections.")
        auth = self._get_auth()

        url = f"{self._config.base_url}{route}"
        response_received = False
        try:
            async with httpx.AsyncClient(
                transport=self._transport,
                timeout=httpx.Timeout(_TIMEOUT_SECONDS),
                follow_redirects=False,
                trust_env=False,
                verify=self._tls_verification,
            ) as client:
                async with client.stream(
                    "GET",
                    url,
                    params=params,
                    auth=auth,
                    headers={"Accept": "application/json"},
                ) as response:
                    response_received = True
                    if response.status_code in {401, 403}:
                        raise SiteConnectionError("WordPress requires authentication or additional permission.")
                    if 300 <= response.status_code < 400:
                        raise SiteConnectionError("WordPress returned an unexpected redirect.")
                    if response.status_code != 200:
                        raise SiteConnectionError(f"The WordPress {endpoint_name} endpoint returned an error.")
                    content_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
                    if content_type != "application/json":
                        raise SiteConnectionError(
                            f"The WordPress {endpoint_name} endpoint returned an unexpected content type."
                        )
                    body = bytearray()
                    async for chunk in response.aiter_bytes(chunk_size=_RESPONSE_CHUNK_BYTES):
                        _append_response_chunk(body, chunk)
        except SiteConnectionError:
            raise
        except httpx.TimeoutException as exc:
            category = _transport_failure_category(_collect_exception_chain(exc), response_received)
            if category == "other_connection":
                raise SiteConnectionError(f"The WordPress {endpoint_name} request timed out.") from None
            raise SiteConnectionError(_transport_failure_message(category, endpoint_name)) from None
        except httpx.RequestError as exc:
            category = _transport_failure_category(_collect_exception_chain(exc), response_received)
            raise SiteConnectionError(_transport_failure_message(category, endpoint_name)) from None

        try:
            return json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise SiteConnectionError(f"The WordPress {endpoint_name} response was not valid JSON.") from None

    def _get_auth(self) -> httpx.BasicAuth | None:
        if self._config.credential_ref is None:
            return None
        if self._config.username is None or self._credential_provider is None:
            raise CredentialStoreError("WordPress credentials are not configured in secure storage.")
        try:
            password = self._credential_provider.get_password(self._config.credential_ref)
        except CredentialStoreError:
            raise
        except Exception:
            raise CredentialStoreError("Windows Credential Manager could not read the requested credential.") from None
        if not password:
            raise CredentialNotFoundError("The configured WordPress credential was not found in secure storage.")
        return httpx.BasicAuth(self._config.username, password)
