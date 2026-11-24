"""Read-only MCP tool for listing WordPress posts."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import (
    DEFAULT_POST_PAGE,
    DEFAULT_POSTS_PER_PAGE,
    PostList,
    PostMetadata,
    validate_post_query,
)

PostItemOutput = dict[str, int | str | list[int] | None]
PaginationOutput = dict[str, int | str]
ListPostsResult = dict[str, str | list[PostItemOutput] | PaginationOutput | None]


class ListPostsTool:
    """Adapt the WordPress client to a validated, safe post listing."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(
        self,
        page: int = DEFAULT_POST_PAGE,
        per_page: int = DEFAULT_POSTS_PER_PAGE,
        status: str = "publish",
    ) -> ListPostsResult:
        """Return one bounded page of post metadata or a safe structured error."""
        validation_error = validate_post_query(page, per_page, status)
        if validation_error is not None:
            return {
                "connection_status": "invalid_request",
                "posts": None,
                "pagination": None,
                "message": validation_error,
            }

        try:
            post_list = await self._client.fetch_posts(page, per_page, status)
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "posts": [_post_fields(post) for post in post_list.posts],
            "pagination": _pagination_fields(post_list),
            "message": "WordPress posts retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ListPostsResult:
        if isinstance(exc, CredentialNotFoundError):
            connection_status = "credentials_missing"
            message = "No credential is stored for the configured WordPress account."
        elif isinstance(exc, CredentialStoreError):
            connection_status = "credentials_unavailable"
            message = "Windows Credential Manager is unavailable or could not read the configured credential."
        elif "authentication" in str(exc).lower() or "permission" in str(exc).lower():
            connection_status = "authentication_required"
            message = "WordPress requires authentication or additional permission."
        elif "timed out" in str(exc).lower():
            connection_status = "timeout"
            message = "The WordPress post listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress posts could not be retrieved safely."

        return {
            "connection_status": connection_status,
            "posts": None,
            "pagination": None,
            "message": message,
        }


def _post_fields(post: PostMetadata) -> PostItemOutput:
    return {
        "id": post.id,
        "title": post.title,
        "slug": post.slug,
        "status": post.status,
        "author_id": post.author_id,
        "date": post.date,
        "modified": post.modified,
        "link": post.link,
        "categories": list(post.categories),
        "tags": list(post.tags),
    }


def _pagination_fields(post_list: PostList) -> PaginationOutput:
    pagination = post_list.pagination
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": pagination.total_items,
        "total_pages": pagination.total_pages,
        "status": pagination.status,
    }
