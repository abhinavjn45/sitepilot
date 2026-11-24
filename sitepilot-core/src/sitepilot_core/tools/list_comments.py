"""Read-only MCP tool for listing WordPress comments."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import (
    DEFAULT_COMMENTS_PER_PAGE,
    CommentList,
    CommentMetadata,
    validate_comment_query,
)

CommentOutput = dict[str, int | str | None]
CommentPaginationOutput = dict[str, int | str]
ListCommentsResult = dict[str, str | list[CommentOutput] | CommentPaginationOutput | None]


class ListCommentsTool:
    """Adapt the fixed WordPress comments endpoint to a safe MCP result."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(
        self,
        page: int = 1,
        per_page: int = DEFAULT_COMMENTS_PER_PAGE,
        status: str = "approved",
    ) -> ListCommentsResult:
        """Return one bounded comment page or a sanitized structured error."""
        validation_error = validate_comment_query(page, per_page, status)
        if validation_error is not None:
            return {
                "connection_status": "invalid_request",
                "comments": None,
                "pagination": None,
                "message": validation_error,
            }

        try:
            comment_list = await self._client.fetch_comments(page, per_page, status)
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "comments": [_comment_fields(item) for item in comment_list.comments],
            "pagination": _pagination_fields(comment_list),
            "message": "WordPress comments retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ListCommentsResult:
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
            message = "The WordPress comment listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress comments could not be retrieved safely."

        return {
            "connection_status": connection_status,
            "comments": None,
            "pagination": None,
            "message": message,
        }


def _comment_fields(comment: CommentMetadata) -> CommentOutput:
    return {
        "id": comment.id,
        "post_id": comment.post_id,
        "author_name": comment.author_name,
        "date": comment.date,
        "content": comment.content,
        "status": comment.status,
        "type": comment.type,
    }


def _pagination_fields(comment_list: CommentList) -> CommentPaginationOutput:
    pagination = comment_list.pagination
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": pagination.total_items,
        "total_pages": pagination.total_pages,
        "status": pagination.status,
    }
