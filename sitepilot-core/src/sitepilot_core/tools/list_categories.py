"""Read-only MCP tool for listing WordPress categories."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import (
    DEFAULT_CATEGORIES_PER_PAGE,
    CategoryList,
    CategoryMetadata,
    validate_category_query,
)

CategoryOutput = dict[str, int | str | None]
CategoryPaginationOutput = dict[str, int]
ListCategoriesResult = dict[str, str | list[CategoryOutput] | CategoryPaginationOutput | None]


class ListCategoriesTool:
    """Adapt the fixed category endpoint to a validated MCP result."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(
        self,
        page: int = 1,
        per_page: int = DEFAULT_CATEGORIES_PER_PAGE,
    ) -> ListCategoriesResult:
        """Return one bounded category page or a sanitized structured error."""
        validation_error = validate_category_query(page, per_page)
        if validation_error is not None:
            return {
                "connection_status": "invalid_request",
                "categories": None,
                "pagination": None,
                "message": validation_error,
            }

        try:
            category_list = await self._client.fetch_categories(page, per_page)
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "categories": [_category_fields(category) for category in category_list.categories],
            "pagination": _pagination_fields(category_list),
            "message": "WordPress categories retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ListCategoriesResult:
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
            message = "The WordPress category listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress categories could not be retrieved safely."

        return {
            "connection_status": connection_status,
            "categories": None,
            "pagination": None,
            "message": message,
        }


def _category_fields(category: CategoryMetadata) -> CategoryOutput:
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
        "parent_id": category.parent_id,
        "count": category.count,
    }


def _pagination_fields(category_list: CategoryList) -> CategoryPaginationOutput:
    pagination = category_list.pagination
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": pagination.total_items,
        "total_pages": pagination.total_pages,
    }
