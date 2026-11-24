from __future__ import annotations

import sitepilot_core.server as server_module
import pytest

from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SiteConnectionError
from sitepilot_core.tools.site_status import SiteStatusTool
from sitepilot_core.wordpress.models import SiteStatus


@pytest.mark.anyio
async def test_tool_returns_allowlisted_versions() -> None:
    class FakeClient:
        async def fetch_status(self) -> SiteStatus:
            return SiteStatus("SitePilot", "0.1.0", "7.1.5", "8.2.12", "ok")

    result = await SiteStatusTool(FakeClient()).run()  # type: ignore[arg-type]
    assert result == {
        "connection_status": "connected",
        "plugin_version": "0.1.0",
        "wordpress_version": "7.1.5",
        "php_version": "8.2.12",
        "message": "SitePilot status retrieved successfully.",
    }


@pytest.mark.anyio
async def test_tool_maps_authentication_failure_to_safe_status() -> None:
    class FakeClient:
        async def fetch_status(self) -> SiteStatus:
            raise SiteConnectionError("WordPress requires authentication or additional permission.")

    result = await SiteStatusTool(FakeClient()).run()  # type: ignore[arg-type]
    assert result["connection_status"] == "authentication_required"
    assert result["plugin_version"] is None


@pytest.mark.anyio
async def test_tool_maps_missing_credential_to_structured_status() -> None:
    class FakeClient:
        async def fetch_status(self) -> SiteStatus:
            raise CredentialNotFoundError("The configured WordPress credential was not found in secure storage.")

    result = await SiteStatusTool(FakeClient()).run()  # type: ignore[arg-type]
    assert result["connection_status"] == "credentials_missing"
    assert result["plugin_version"] is None


@pytest.mark.anyio
async def test_tool_maps_credential_lookup_failure_to_structured_status() -> None:
    class FakeClient:
        async def fetch_status(self) -> SiteStatus:
            raise CredentialStoreError("PRIVATE_LOOKUP_DETAIL")

    result = await SiteStatusTool(FakeClient()).run()  # type: ignore[arg-type]
    assert result["connection_status"] == "credentials_unavailable"
    assert "PRIVATE_LOOKUP_DETAIL" not in str(result)


@pytest.mark.anyio
async def test_mcp_callback_returns_safe_result_on_credential_init_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "https://127.0.0.1")
    monkeypatch.setenv("SITEPILOT_WP_USERNAME", "dummy-user")
    monkeypatch.setenv("SITEPILOT_CREDENTIAL_REF", "dummy-reference")

    def fail_initialization() -> None:
        raise CredentialStoreError("PRIVATE_BACKEND_DETAIL")

    monkeypatch.setattr(server_module, "WindowsCredentialProvider", fail_initialization)
    result = await server_module.create_server().call_tool("site_status", {})

    structured = result.structured_content
    assert structured["connection_status"] == "credentials_unavailable"
    assert structured["plugin_version"] is None
    assert structured["message"] == "Windows Credential Manager is unavailable or could not read the configured credential."
    assert "PRIVATE_BACKEND_DETAIL" not in str(structured)
