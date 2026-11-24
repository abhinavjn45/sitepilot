"""Safe, user-facing error types for SitePilot Core."""


class SitePilotError(Exception):
    """An expected failure with a safe message for an MCP caller."""


class ConfigurationError(SitePilotError):
    """The local SitePilot configuration is missing or invalid."""


class SiteConnectionError(SitePilotError):
    """The configured WordPress status endpoint could not be used safely."""


class CredentialStoreError(SitePilotError):
    """The configured secure credential store is unavailable."""


class CredentialNotFoundError(CredentialStoreError):
    """No password is stored under the configured credential reference."""
