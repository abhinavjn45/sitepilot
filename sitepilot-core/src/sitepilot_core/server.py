"""Official MCP SDK v2 server using stdio transport only."""

from __future__ import annotations

import logging
import sys

from mcp.server import MCPServer

from sitepilot_core import __version__
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import ConfigurationError, CredentialStoreError, SitePilotError
from sitepilot_core.security.credentials import WindowsCredentialProvider
from sitepilot_core.tools.list_plugins import ListPluginsTool, PluginToolResult
from sitepilot_core.tools.list_pages import ListPagesResult, ListPagesTool
from sitepilot_core.tools.list_media import ListMediaResult, ListMediaTool
from sitepilot_core.tools.list_comments import ListCommentsResult, ListCommentsTool
from sitepilot_core.tools.list_categories import ListCategoriesResult, ListCategoriesTool
from sitepilot_core.tools.list_tags import ListTagsResult, ListTagsTool
from sitepilot_core.tools.list_posts import ListPostsResult, ListPostsTool
from sitepilot_core.tools.list_themes import ListThemesTool, ThemeToolResult
from sitepilot_core.tools.list_users import ListUsersResult, ListUsersTool
from sitepilot_core.tools.site_info import SiteInfoTool
from sitepilot_core.tools.site_status import SiteStatusTool
from sitepilot_core.wordpress.client import WordPressClient


def create_server() -> MCPServer:
    """Create the MCP server without making a network request."""
    server = MCPServer(name="SitePilot", version=__version__)

    @server.tool(name="site_status", description="Read version and connection status for the configured local WordPress site.")
    async def site_status() -> dict[str, str | None]:
        """Read the configured site's SitePilot connector status."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = SiteStatusTool(WordPressClient(config, credential_provider))
            return await tool.run()
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured site status check could not be completed safely."
            if isinstance(exc, ConfigurationError):
                message = str(exc)
            return {
                "connection_status": connection_status,
                "plugin_version": None,
                "wordpress_version": None,
                "php_version": None,
                "message": message,
            }

    @server.tool(name="site_info", description="Read general information for the configured WordPress site.")
    async def site_info() -> dict[str, str | float | None]:
        """Read allowlisted, non-sensitive information from the configured site."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = SiteInfoTool(WordPressClient(config, credential_provider))
            return await tool.run()
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured site information request could not be completed safely."
            return {
                "connection_status": connection_status,
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
                "message": message,
            }

    @server.tool(name="list_plugins", description="List installed WordPress plugins and their active status.")
    async def list_plugins() -> PluginToolResult:
        """List allowlisted plugin metadata for the configured WordPress site."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListPluginsTool(WordPressClient(config, credential_provider))
            return await tool.run()
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured plugin list request could not be completed safely."
            return {"connection_status": connection_status, "plugins": None, "message": message}

    @server.tool(name="list_themes", description="List installed WordPress themes and identify the active theme.")
    async def list_themes() -> ThemeToolResult:
        """List allowlisted theme metadata for the configured WordPress site."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListThemesTool(WordPressClient(config, credential_provider))
            return await tool.run()
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured theme list request could not be completed safely."
            return {"connection_status": connection_status, "themes": None, "message": message}

    @server.tool(name="list_posts", description="List WordPress posts with bounded pagination and status filtering.")
    async def list_posts(
        page: int = 1,
        per_page: int = 10,
        status: str = "publish",
    ) -> ListPostsResult:
        """List metadata for one bounded page of the configured site's posts."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListPostsTool(WordPressClient(config, credential_provider))
            return await tool.run(page, per_page, status)
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured post list request could not be completed safely."
            return {
                "connection_status": connection_status,
                "posts": None,
                "pagination": None,
                "message": message,
            }

    @server.tool(name="list_pages", description="List WordPress pages with bounded pagination and status filtering.")
    async def list_pages(
        page: int = 1,
        per_page: int = 10,
        status: str = "publish",
    ) -> ListPagesResult:
        """List metadata for one bounded page of the configured site's pages."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListPagesTool(WordPressClient(config, credential_provider))
            return await tool.run(page, per_page, status)
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured page list request could not be completed safely."
            return {
                "connection_status": connection_status,
                "pages": None,
                "pagination": None,
                "message": message,
            }

    @server.tool(name="list_users", description="List WordPress user metadata with bounded pagination.")
    async def list_users(page: int = 1, per_page: int = 10) -> ListUsersResult:
        """List privacy-limited metadata for one page of configured-site users."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListUsersTool(WordPressClient(config, credential_provider))
            return await tool.run(page, per_page)
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured user list request could not be completed safely."
            return {
                "connection_status": connection_status,
                "users": None,
                "pagination": None,
                "message": message,
            }

    @server.tool(name="list_media", description="List WordPress media attachments with bounded pagination.")
    async def list_media(page: int = 1, per_page: int = 10) -> ListMediaResult:
        """List allowlisted metadata for one page of the configured site's media library."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListMediaTool(WordPressClient(config, credential_provider))
            return await tool.run(page, per_page)
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured media list request could not be completed safely."
            return {
                "connection_status": connection_status,
                "media": None,
                "pagination": None,
                "message": message,
            }

    @server.tool(name="list_comments", description="List WordPress comments with bounded pagination and status filtering.")
    async def list_comments(page: int = 1, per_page: int = 10, status: str = "approved") -> ListCommentsResult:
        """List allowlisted comment text and metadata from the configured site."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListCommentsTool(WordPressClient(config, credential_provider))
            return await tool.run(page, per_page, status)
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured comment list request could not be completed safely."
            return {
                "connection_status": connection_status,
                "comments": None,
                "pagination": None,
                "message": message,
            }

    @server.tool(name="list_categories", description="List built-in WordPress categories with bounded pagination.")
    async def list_categories(page: int = 1, per_page: int = 10) -> ListCategoriesResult:
        """List allowlisted category data from the configured WordPress site."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListCategoriesTool(WordPressClient(config, credential_provider))
            return await tool.run(page, per_page)
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured category list request could not be completed safely."
            return {
                "connection_status": connection_status,
                "categories": None,
                "pagination": None,
                "message": message,
            }

    @server.tool(name="list_tags", description="List built-in WordPress tags with bounded pagination.")
    async def list_tags(page: int = 1, per_page: int = 10) -> ListTagsResult:
        """List allowlisted tag data from the configured WordPress site."""
        try:
            config = SiteConfig.from_environment()
            credential_provider = WindowsCredentialProvider() if config.credential_ref else None
            tool = ListTagsTool(WordPressClient(config, credential_provider))
            return await tool.run(page, per_page)
        except SitePilotError as exc:
            if isinstance(exc, ConfigurationError):
                connection_status = "not_configured"
                message = str(exc)
            elif isinstance(exc, CredentialStoreError):
                connection_status = "credentials_unavailable"
                message = "Windows Credential Manager is unavailable or could not read the configured credential."
            else:
                connection_status = "unavailable"
                message = "The configured tag list request could not be completed safely."
            return {
                "connection_status": connection_status,
                "tags": None,
                "pagination": None,
                "message": message,
            }

    return server


def main() -> None:
    """Run stdio MCP; keep all application diagnostics on stderr."""
    logging.basicConfig(stream=sys.stderr, level=logging.INFO)
    create_server().run(transport="stdio")
