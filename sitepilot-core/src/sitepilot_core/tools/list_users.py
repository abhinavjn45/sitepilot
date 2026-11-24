"""Read-only MCP tool for listing privacy-limited WordPress user metadata."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import UserList, UserMetadata, validate_user_query

UserItemOutput = dict[str, int | str | list[str] | None]
UserPaginationOutput = dict[str, int]
ListUsersResult = dict[str, str | list[UserItemOutput] | UserPaginationOutput | None]


class ListUsersTool:
    """Adapt the WordPress client to a validated, privacy-limited user listing."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self, page: int = 1, per_page: int = 10) -> ListUsersResult:
        """Return one bounded page of user metadata or a safe structured error."""
        validation_error = validate_user_query(page, per_page)
        if validation_error is not None:
            return {
                "connection_status": "invalid_request",
                "users": None,
                "pagination": None,
                "message": validation_error,
            }

        try:
            user_list = await self._client.fetch_users(page, per_page)
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "users": [_user_fields(user) for user in user_list.users],
            "pagination": _pagination_fields(user_list),
            "message": "WordPress users retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ListUsersResult:
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
            message = "The WordPress user listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress users could not be retrieved safely."

        return {
            "connection_status": connection_status,
            "users": None,
            "pagination": None,
            "message": message,
        }


def _user_fields(user: UserMetadata) -> UserItemOutput:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "roles": list(user.roles),
        "registered": user.registered,
        "description": user.description,
    }


def _pagination_fields(user_list: UserList) -> UserPaginationOutput:
    pagination = user_list.pagination
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": pagination.total_items,
        "total_pages": pagination.total_pages,
    }
