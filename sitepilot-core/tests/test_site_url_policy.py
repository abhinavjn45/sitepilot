from __future__ import annotations

import pytest

from sitepilot_core.errors import ConfigurationError
from sitepilot_core.security.urls import validate_site_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://localhost/sitepilot-test/", "http://127.0.0.1/sitepilot-test"),
        ("https://127.0.0.1:443/wp", "https://127.0.0.1:443/wp"),
        ("http://[::1]:80/", "http://[::1]:80"),
        ("http://localhost/sitepilot-test/", "http://127.0.0.1/sitepilot-test"),
        ("http://localhost/sitepilot%20test/", "http://127.0.0.1/sitepilot%20test"),
    ],
)
def test_accepts_loopback_urls(raw: str, expected: str) -> None:
    assert validate_site_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "https://example.com",
        "http://192.168.1.20",
        "http://localhost.evil.example",
        "file:///etc/passwd",
        "http://user:password@localhost",
        "http://localhost/?next=https://example.com",
        "http://localhost/a/../b",
        "http://localhost/a/%2e%2e/b",
        "http://localhost/a/%252e%252e/b",
        "http://localhost/a/%3Fadmin",
        "http://localhost/a/%23fragment",
        "http://localhost/a/%2525253Fadmin",
        "http://localhost/a/%25252523fragment",
        "http://localhost\\@example.com",
        "http://localhost:8080",
    ],
)
def test_rejects_nonlocal_or_ambiguous_urls(raw: str) -> None:
    with pytest.raises(ConfigurationError):
        validate_site_url(raw)
