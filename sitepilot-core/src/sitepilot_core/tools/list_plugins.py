"""Read-only MCP tool for listing installed WordPress plugins."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import PluginList, PluginMetadata

PluginToolResult = dict[str, str | list[dict[str, str | None]] | None]


class ListPluginsTool:
    """Adapt the WordPress client to a safe, allowlisted plugin list."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self) -> PluginToolResult:
        """Return installed plugin metadata or a structured safe error."""
        try:
            plugin_list = await self._client.fetch_plugins()
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            "plugins": [_plugin_fields(plugin) for plugin in plugin_list.plugins],
            "message": "Installed WordPress plugins retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> PluginToolResult:
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
            message = "The WordPress plugin listing request timed out."
        else:
            connection_status = "unavailable"
            message = "The WordPress plugin list could not be retrieved safely."

        return {"connection_status": connection_status, "plugins": None, "message": message}


def _plugin_fields(plugin: PluginMetadata) -> dict[str, str | None]:
    return {
        "plugin_file": plugin.plugin_file,
        "name": plugin.name,
        "version": plugin.version,
        "status": plugin.status,
        "description": plugin.description,
        "author": plugin.author,
    }
