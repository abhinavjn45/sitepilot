from __future__ import annotations

import pytest
import keyring.backends.Windows as windows_keyring

from sitepilot_core.errors import CredentialStoreError
from sitepilot_core.security.credentials import WindowsCredentialProvider


def test_backend_initialization_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenBackend:
        def __init__(self) -> None:
            raise RuntimeError("PRIVATE_BACKEND_DETAIL")

    monkeypatch.setattr(windows_keyring, "WinVaultKeyring", BrokenBackend)

    with pytest.raises(CredentialStoreError) as error:
        WindowsCredentialProvider()

    assert str(error.value) == "Windows Credential Manager is not available."
    assert "PRIVATE_BACKEND_DETAIL" not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


def test_backend_lookup_failure_is_sanitized(monkeypatch: pytest.MonkeyPatch) -> None:
    class BrokenBackend:
        priority = 5

        def get_password(self, service_name: str, credential_ref: str) -> str:
            raise RuntimeError("PRIVATE_LOOKUP_DETAIL")

    monkeypatch.setattr(windows_keyring, "WinVaultKeyring", BrokenBackend)
    provider = WindowsCredentialProvider()

    with pytest.raises(CredentialStoreError) as error:
        provider.get_password("dummy-reference")

    assert str(error.value) == "Windows Credential Manager could not read the requested credential."
    assert "PRIVATE_LOOKUP_DETAIL" not in str(error.value)
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__
