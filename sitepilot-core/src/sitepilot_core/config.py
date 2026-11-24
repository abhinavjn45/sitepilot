"""Typed configuration for the single configured local WordPress site."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from sitepilot_core.errors import ConfigurationError
from sitepilot_core.security.tls import validate_ca_certificate_path
from sitepilot_core.security.urls import validate_site_url


@dataclass(frozen=True, slots=True)
class SiteConfig:
    """Non-secret connection settings for one WordPress site."""

    base_url: str
    username: str | None = None
    credential_ref: str | None = None
    ca_cert_path: str | None = None

    def __post_init__(self) -> None:
        """Validate even settings assembled directly by another caller."""
        object.__setattr__(self, "base_url", validate_site_url(self.base_url))
        object.__setattr__(self, "ca_cert_path", validate_ca_certificate_path(self.ca_cert_path))
        if bool(self.username) != bool(self.credential_ref):
            raise ConfigurationError(
                "Set both a WordPress username and credential reference, or leave both unset."
            )

    @classmethod
    def from_environment(cls, environ: Mapping[str, str] | None = None) -> SiteConfig:
        """Load and validate the site's settings from process environment."""
        values = os.environ if environ is None else environ
        raw_url = values.get("SITEPILOT_WORDPRESS_URL", "").strip()
        if not raw_url:
            raise ConfigurationError("Set SITEPILOT_WORDPRESS_URL to configure the local WordPress site.")

        username = values.get("SITEPILOT_WP_USERNAME", "").strip() or None
        credential_ref = values.get("SITEPILOT_CREDENTIAL_REF", "").strip() or None
        ca_cert_path = values.get("SITEPILOT_CA_CERT", "").strip() or None
        if bool(username) != bool(credential_ref):
            raise ConfigurationError(
                "Set both SITEPILOT_WP_USERNAME and SITEPILOT_CREDENTIAL_REF, or leave both unset."
            )

        return cls(
            base_url=raw_url,
            username=username,
            credential_ref=credential_ref,
            ca_cert_path=ca_cert_path,
        )
