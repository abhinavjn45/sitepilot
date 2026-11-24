"""TLS verification configuration for optional local development CAs."""

from __future__ import annotations

import ssl
from pathlib import Path

import certifi

from sitepilot_core.errors import ConfigurationError


def validate_ca_certificate_path(ca_certificate_path: str | None) -> str | None:
    """Return a normalized CA path after confirming it is a readable file."""
    if ca_certificate_path is None:
        return None

    try:
        path = Path(ca_certificate_path).expanduser()
        if not path.is_file():
            raise ConfigurationError("SITEPILOT_CA_CERT must point to a readable CA certificate file.")
        with path.open("rb"):
            pass
    except (OSError, ValueError):
        raise ConfigurationError("SITEPILOT_CA_CERT must point to a readable CA certificate file.") from None
    return str(path)


def create_tls_verification(ca_certificate_path: str | None) -> ssl.SSLContext | bool:
    """Keep default verification, optionally adding a configured CA certificate."""
    normalized_path = validate_ca_certificate_path(ca_certificate_path)
    if normalized_path is None:
        return True

    try:
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=certifi.where())
        context.load_verify_locations(cafile=normalized_path)
    except (OSError, ssl.SSLError, ValueError):
        raise ConfigurationError("SITEPILOT_CA_CERT is not a valid readable CA certificate file.") from None
    return context
