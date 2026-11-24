from __future__ import annotations

import pytest

from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import ConfigurationError


def test_loads_one_configured_site_from_environment() -> None:
    config = SiteConfig.from_environment({"SITEPILOT_WORDPRESS_URL": "http://localhost/sitepilot-test/"})
    assert config.base_url == "http://127.0.0.1/sitepilot-test"
    assert config.username is None
    assert config.credential_ref is None
    assert config.ca_cert_path is None


def test_loads_optional_ca_certificate_path_from_environment(tmp_path) -> None:
    ca_file = tmp_path / "local-ca.pem"
    ca_file.write_text("certificate placeholder", encoding="ascii")

    config = SiteConfig.from_environment(
        {
            "SITEPILOT_WORDPRESS_URL": "https://127.0.0.1/sitepilot-test",
            "SITEPILOT_CA_CERT": str(ca_file),
        }
    )

    assert config.ca_cert_path == str(ca_file)


def test_rejects_missing_ca_certificate_path_safely(tmp_path) -> None:
    with pytest.raises(ConfigurationError, match="SITEPILOT_CA_CERT") as error:
        SiteConfig.from_environment(
            {
                "SITEPILOT_WORDPRESS_URL": "https://127.0.0.1/sitepilot-test",
                "SITEPILOT_CA_CERT": str(tmp_path / "missing.pem"),
            }
        )

    assert str(tmp_path) not in str(error.value)


def test_requires_site_url() -> None:
    with pytest.raises(ConfigurationError, match="SITEPILOT_WORDPRESS_URL"):
        SiteConfig.from_environment({})


def test_requires_username_and_credential_reference_together() -> None:
    with pytest.raises(ConfigurationError, match="both"):
        SiteConfig.from_environment(
            {"SITEPILOT_WORDPRESS_URL": "http://localhost", "SITEPILOT_WP_USERNAME": "admin"}
        )
