"""Read-only MCP tool for retrieving the configured site's status."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient


class SiteStatusTool:
    """Adapt the WordPress client to a safe MCP tool response."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self) -> dict[str, str | None]:
        """Return an allowlisted status object without raising raw errors."""
        try:
            status = await self._client.fetch_status()
        except SitePilotError as exc:
            raw_message = str(exc)
            if isinstance(exc, CredentialNotFoundError):
                connection_status = "credentials_missing"
                message = "No credential is stored for the configured WordPress account."
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            elif "authentication" in raw_message.lower() or "permission" in raw_message.lower():
                connection_status = "authentication_required"
                message = raw_message
            elif "timed out" in raw_message.lower():
                connection_status = "timeout"
                message = raw_message
            else:
                connection_status = "unavailable"
                message = raw_message
            return {
                "connection_status": connection_status,
                "plugin_version": None,
                "wordpress_version": None,
                "php_version": None,
                "message": message,
            }

        return {
            "connection_status": "connected",
            "plugin_version": status.plugin_version,
            "wordpress_version": status.wordpress_version,
            "php_version": status.php_version,
            "message": "SitePilot status retrieved successfully.",
        }
