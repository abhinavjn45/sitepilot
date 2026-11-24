"""Read-only MCP tool for listing WordPress media attachments."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import (
    DEFAULT_MEDIA_PER_PAGE,
    MediaList,
    MediaMetadata,
    validate_media_query,
)

MediaItemOutput = dict[str, int | str | None]
MediaPaginationOutput = dict[str, int]
ListMediaResult = dict[str, str | list[MediaItemOutput] | MediaPaginationOutput | None]


class ListMediaTool:
    """Adapt the WordPress client to a validated media inventory result."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self, page: int = 1, per_page: int = DEFAULT_MEDIA_PER_PAGE) -> ListMediaResult:
        """Return one bounded page of attachment metadata or a safe structured error."""
        validation_error = validate_media_query(page, per_page)
        if validation_error is not None:
            return {
                "connection_status": "invalid_request",
                "media": None,
                "pagination": None,
                "message": validation_error,
            }

        try:
            media_list = await self._client.fetch_media(page, per_page)
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "media": [_media_fields(item) for item in media_list.media],
            "pagination": _pagination_fields(media_list),
            "message": "WordPress media retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ListMediaResult:
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
            message = "The WordPress media listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress media could not be retrieved safely."

        return {
            "connection_status": connection_status,
            "media": None,
            "pagination": None,
            "message": message,
        }


def _media_fields(item: MediaMetadata) -> MediaItemOutput:
    return {
        "id": item.id,
        "title": item.title,
        "slug": item.slug,
        "filename": item.filename,
        "mime_type": item.mime_type,
        "media_type": item.media_type,
        "date": item.date,
        "modified": item.modified,
        "alt_text": item.alt_text,
        "caption": item.caption,
        "description": item.description,
        "source_url": item.source_url,
    }


def _pagination_fields(media_list: MediaList) -> MediaPaginationOutput:
    pagination = media_list.pagination
    return {
        "page": pagination.page,
        "per_page": pagination.per_page,
        "total_items": pagination.total_items,
        "total_pages": pagination.total_pages,
    }
