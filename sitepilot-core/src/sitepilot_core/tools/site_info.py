"""Read-only MCP tool for retrieving general information about the configured site."""

from __future__ import annotations

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SitePilotError
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import SiteInfo


class SiteInfoTool:
    """Adapt the WordPress client to an allowlisted site-information response."""

    def __init__(self, client: WordPressClient) -> None:
        self._client = client

    async def run(self) -> dict[str, str | float | None]:
        """Return safe site information or a structured, sanitized error."""
        try:
            info = await self._client.fetch_site_info()
        except SitePilotError as exc:
            return self._error_result(exc)

        return {
            "connection_status": "connected",
            **_info_fields(info),
            "message": "WordPress site information retrieved successfully.",
        }

    @staticmethod
    def _error_result(exc: SitePilotError) -> dict[str, str | float | None]:
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
            message = "The WordPress site information request timed out."
        elif "tls certificate verification" in str(exc).lower():
            connection_status = "unavailable"
            message = "TLS certificate verification failed for the WordPress connection."
        elif "refused the connection" in str(exc).lower():
            connection_status = "unavailable"
            message = "The WordPress server refused the connection."
        elif "could not be resolved" in str(exc).lower():
            connection_status = "unavailable"
            message = "The WordPress server address could not be resolved."
        else:
            connection_status = "unavailable"
            message = "The WordPress site information could not be retrieved safely."

        return {
            "connection_status": connection_status,
            **_empty_info_fields(),
            "message": message,
        }


def _info_fields(info: SiteInfo) -> dict[str, str | float | None]:
    return {
        "site_name": info.site_name,
        "site_description": info.site_description,
        "home_url": info.home_url,
        "site_url": info.site_url,
        "wordpress_version": info.wordpress_version,
        "php_version": info.php_version,
        "timezone": info.timezone,
        "gmt_offset": info.gmt_offset,
        "locale": info.locale,
        "plugin_version": info.plugin_version,
    }


def _empty_info_fields() -> dict[str, str | float | None]:
    return {
        "site_name": None,
        "site_description": None,
        "home_url": None,
        "site_url": None,
        "wordpress_version": None,
        "php_version": None,
        "timezone": None,
        "gmt_offset": None,
        "locale": None,
        "plugin_version": None,
    }
