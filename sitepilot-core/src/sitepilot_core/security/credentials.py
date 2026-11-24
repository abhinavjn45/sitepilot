"""Credential-provider abstraction backed by Windows Credential Manager."""

from __future__ import annotations

from typing import Protocol

from sitepilot_core.errors import CredentialStoreError


class CredentialProvider(Protocol):
    """Retrieve a password by reference without exposing storage details."""

    def get_password(self, credential_ref: str) -> str | None:
        """Return a password, if one is stored under this reference."""


class WindowsCredentialProvider:
    """Read an existing secret from the verified Windows Vault keyring backend."""

    def __init__(self, service_name: str = "SitePilot") -> None:
        if not service_name or len(service_name) > 128:
            raise CredentialStoreError("The Windows credential service name is invalid.")
        try:
            from keyring.backends.Windows import WinVaultKeyring

            backend = WinVaultKeyring()
            if backend.priority <= 0:
                raise CredentialStoreError("Windows Credential Manager is not available.")
            self._backend = backend
            self._service_name = service_name
        except CredentialStoreError:
            raise
        except Exception:
            raise CredentialStoreError("Windows Credential Manager is not available.") from None

    def get_password(self, credential_ref: str) -> str | None:
        """Look up a credential without ever including it in an error message."""
        if not credential_ref or len(credential_ref) > 256:
            raise CredentialStoreError("The credential reference is invalid.")
        try:
            return self._backend.get_password(self._service_name, credential_ref)
        except Exception:
            raise CredentialStoreError("Windows Credential Manager could not read the requested credential.") from None
