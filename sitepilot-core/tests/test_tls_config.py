from __future__ import annotations

import ssl

import certifi
import pytest

from sitepilot_core.errors import ConfigurationError
from sitepilot_core.security import tls
from sitepilot_core.security.tls import create_tls_verification


def test_absent_ca_path_keeps_httpx_default_verification() -> None:
    assert create_tls_verification(None) is True


def test_configured_ca_is_added_to_a_normal_verifying_context(monkeypatch, tmp_path) -> None:
    ca_file = tmp_path / "local-ca.pem"
    ca_file.write_text("test certificate data", encoding="ascii")
    calls: list[tuple[ssl.Purpose, str | None, str]] = []

    class ContextSpy:
        check_hostname = True
        verify_mode = ssl.CERT_REQUIRED

        def load_verify_locations(self, *, cafile: str) -> None:
            calls.append((ssl.Purpose.SERVER_AUTH, certifi.where(), cafile))

    def default_context(purpose: ssl.Purpose, *, cafile: str) -> ContextSpy:
        assert purpose is ssl.Purpose.SERVER_AUTH
        assert cafile == certifi.where()
        return ContextSpy()

    monkeypatch.setattr(tls.ssl, "create_default_context", default_context)

    context = create_tls_verification(str(ca_file))

    assert isinstance(context, ContextSpy)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert calls == [(ssl.Purpose.SERVER_AUTH, certifi.where(), str(ca_file))]


def test_real_context_preserves_verification_and_default_public_roots() -> None:
    default_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    context = create_tls_verification(certifi.where())

    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
    assert len(context.get_ca_certs()) >= len(default_context.get_ca_certs())


@pytest.mark.parametrize("ca_contents", ["not a certificate", "-----BEGIN CERTIFICATE-----\ninvalid\n-----END CERTIFICATE-----\n"])
def test_invalid_ca_certificate_is_a_sanitized_configuration_error(tmp_path, ca_contents: str) -> None:
    ca_file = tmp_path / "invalid-ca.pem"
    ca_file.write_text(ca_contents, encoding="ascii")

    with pytest.raises(ConfigurationError, match="valid readable CA certificate") as error:
        create_tls_verification(str(ca_file))

    assert str(tmp_path) not in str(error.value)
    assert "invalid" not in str(error.value).lower()


def test_directory_is_rejected_as_ca_certificate() -> None:
    with pytest.raises(ConfigurationError, match="readable CA certificate file"):
        create_tls_verification(".")
