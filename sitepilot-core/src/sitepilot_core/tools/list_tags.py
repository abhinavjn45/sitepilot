"""Read-only MCP tool for listing WordPress tags."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import (
    DEFAULT_TAGS_PER_PAGE,
    TagList,
    TagMetadata,
    validate_tag_query,
)

TagOutput = dict[str, int | str | None]
TagPaginationOutput = dict[str, int]
ListTagsResult = dict[str, str | list[TagOutput] | TagPaginationOutput | None]


class ListTagsTool:
    """Adapt the fixed tag endpoint to a validated MCP result."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self, page: int = 1, per_page: int = DEFAULT_TAGS_PER_PAGE) -> ListTagsResult:
        """Return one bounded tag page or a sanitized structured error."""
        validation_error = validate_tag_query(page, per_page)
        if validation_error is not None:
            return {
                "connection_status": "invalid_request",
                "tags": None,
                "pagination": None,
                "message": validation_error,
            }

        try:
            tag_list = await self._client.fetch_tags(page, per_page)
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "tags": [_tag_fields(tag) for tag in tag_list.tags],
            "pagination": _pagination_fields(tag_list),
            "message": "WordPress tags retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ListTagsResult:
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
            message = "The WordPress tag listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress tags could not be retrieved safely."

        return {
            "connection_status": connection_status,
            "tags": None,
            "pagination": None,
            "message": message,
        }


def _tag_fields(tag: TagMetadata) -> TagOutput:
    return {
        "id": tag.id,
        "name": tag.name,
        "slug": tag.slug,
        "description": tag.description,
        "count": tag.count,
    }


def _pagination_fields(tag_list: TagList) -> TagPaginationOutput:
    pagination = tag_list.pagination
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": pagination.total_items,
        "total_pages": pagination.total_pages,
    }
