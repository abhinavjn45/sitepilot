"""Read-only MCP tool for listing installed WordPress themes."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import ThemeList, ThemeMetadata

ThemeToolResult = dict[str, str | list[dict[str, str | None]] | None]


class ListThemesTool:
    """Adapt the WordPress client to a safe, allowlisted theme list."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self) -> ThemeToolResult:
        """Return installed theme metadata or a structured safe error."""
        try:
            theme_list = await self._client.fetch_themes()
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "themes": [_theme_fields(theme) for theme in theme_list.themes],
            "message": "Installed WordPress themes retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> ThemeToolResult:
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
            message = "The WordPress theme listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress theme list could not be retrieved safely."

        return {"connection_status": connection_status, "themes": None, "message": message}


def _theme_fields(theme: ThemeMetadata) -> dict[str, str | None]:
    return {
        "stylesheet": theme.stylesheet,
        "name": theme.name,
        "version": theme.version,
        "status": theme.status,
        "description": theme.description,
        "author": theme.author,
        "template": theme.template,
    }
