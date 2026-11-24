"""Read-only MCP tool for listing WordPress pages."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import (
    PageList,
    PageMetadata,
    validate_page_query,
)

PageItemOutput = dict[str, int | str | None]
PagePaginationOutput = dict[str, int | str]
ListPagesResult = dict[str, str | list[PageItemOutput] | PagePaginationOutput | None]


class ListPagesTool:
    """Adapt the WordPress client to a validated, safe page listing."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self, page: int = 1, per_page: int = 10, status: str = "publish") -> ListPagesResult:
        """Return one bounded page of page metadata or a safe structured error."""
        validation_error = validate_page_query(page, per_page, status)
        if validation_error is not None:
            return {
                "connection_status": "invalid_request",
                "pages": None,
                "pagination": None,
                "message": validation_error,
            }

        try:
            page_list = await self._client.fetch_pages(page, per_page, status)
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "pages": [_page_fields(item) for item in page_list.pages],
            "pagination": _pagination_fields(page_list),
            "message": "WordPress pages retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ListPagesResult:
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
            message = "The WordPress page listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress pages could not be retrieved safely."

        return {
            "connection_status": connection_status,
            "pages": None,
            "pagination": None,
            "message": message,
        }


def _page_fields(item: PageMetadata) -> PageItemOutput:
    return {
        "id": item.id,
        "title": item.title,
        "slug": item.slug,
        "status": item.status,
        "author_id": item.author_id,
        "date": item.date,
        "modified": item.modified,
        "link": item.link,
        "parent_id": item.parent_id,
        "menu_order": item.menu_order,
    }


def _pagination_fields(page_list: PageList) -> PagePaginationOutput:
    pagination = page_list.pagination
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": pagination.total_items,
        "total_pages": pagination.total_pages,
        "status": pagination.status,
    }
