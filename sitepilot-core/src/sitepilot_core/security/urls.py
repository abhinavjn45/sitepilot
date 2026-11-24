"""Restrict the initial connector to explicit loopback destinations."""

from __future__ import annotations

import ipaddress
from urllib.parse import quote, unquote, urlsplit, urlunsplit

from sitepilot_core.errors import ConfigurationError

_LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_MAX_URL_LENGTH = 2048
_MAX_PATH_DECODE_LAYERS = 8


def validate_site_url(value: str) -> str:
    """Validate and normalize a base URL for the first, local-only milestone."""
    if len(value) > _MAX_URL_LENGTH:
        raise ConfigurationError("The configured WordPress URL is too long.")
    try:
        parts = urlsplit(value.strip())
        port = parts.port
    except (ValueError, UnicodeError) as exc:
        raise ConfigurationError("The configured WordPress URL is invalid.") from exc

    if parts.scheme not in {"http", "https"}:
        raise ConfigurationError("The WordPress URL must use HTTP or HTTPS.")
    if not parts.hostname or parts.username is not None or parts.password is not None:
        raise ConfigurationError("The WordPress URL must contain a host and no embedded credentials.")
    host = parts.hostname.casefold().rstrip(".")
    if host not in _LOCAL_HOSTS:
        raise ConfigurationError("Only localhost and loopback IP addresses are allowed in this milestone.")
    approved_port = 80 if parts.scheme == "http" else 443
    if port is not None and port != approved_port:
        raise ConfigurationError("Only the standard local web port is allowed in this milestone.")
    if parts.query or parts.fragment:
        raise ConfigurationError("The WordPress base URL cannot contain a query or fragment.")

    decoded_path = parts.path
    for _ in range(_MAX_PATH_DECODE_LAYERS):
        if "%" not in decoded_path:
            break
        next_path = unquote(decoded_path)
        if next_path == decoded_path:
            raise ConfigurationError("The WordPress base URL path contains invalid encoding.")
        decoded_path = next_path
    else:
        if "%" in decoded_path:
            raise ConfigurationError("The WordPress base URL path has too many encoding layers.")

    if "%" in decoded_path:
        raise ConfigurationError("The WordPress base URL path contains invalid or nested encoding.")
    if any(char in decoded_path for char in ("\\", "\x00", "?", "#")):
        raise ConfigurationError("The WordPress base URL path is invalid.")
    if any(segment in {".", ".."} for segment in decoded_path.split("/")):
        raise ConfigurationError("The WordPress base URL cannot contain traversal segments.")
    if "://" in decoded_path or decoded_path.startswith("//"):
        raise ConfigurationError("The WordPress base URL path is invalid.")

    # Normalize localhost to a literal loopback address so HTTPX does not
    # resolve a user-controlled hostname when the request is made.
    normalized_host = "127.0.0.1" if host == "localhost" else host
    try:
        ip = ipaddress.ip_address(normalized_host)
    except ValueError as exc:
        raise ConfigurationError("The configured WordPress host is not a loopback address.") from exc
    if not ip.is_loopback:
        raise ConfigurationError("Only loopback WordPress destinations are allowed in this milestone.")

    netloc = f"[{normalized_host}]" if ip.version == 6 else normalized_host
    if port is not None:
        netloc = f"{netloc}:{port}"
    path = quote(decoded_path.rstrip("/"), safe="/-._~!$&'()*+,;=:@")
    return urlunsplit((parts.scheme, netloc, path, "", ""))
