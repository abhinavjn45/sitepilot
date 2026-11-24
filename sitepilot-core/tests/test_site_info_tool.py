from __future__ import annotations

import httpx
import pytest

import sitepilot_core.server as server_module
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.site_info import SiteInfoTool
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import SiteInfo

SITE_INFO_PAYLOAD = {
    "site_name": "Example Site",
    "site_description": "A local WordPress test site",
    "home_url": "https://127.0.0.1/sitepilot-test/",
    "site_url": "https://127.0.0.1/sitepilot-test/",
    "wordpress_version": "7.1.5",
    "php_version": "8.2.12",
    "timezone": "America/New_York",
    "gmt_offset": -5.0,
    "locale": "en_US",
    "plugin_version": "0.1.0",
}


@pytest.mark.anyio
async def test_site_info_tool_returns_allowlisted_fields() -> None:
    class FakeClient:
        async def fetch_site_info(self) -> SiteInfo:
            return SiteInfo.from_payload(SITE_INFO_PAYLOAD)

    result = await SiteInfoTool(FakeClient()).run()  # type: ignore[arg-type]

    assert result == {
        "connection_status": "connected",
        **SITE_INFO_PAYLOAD,
        "message": "WordPress site information retrieved successfully.",
    }


def test_site_info_model_normalizes_missing_optional_fields_to_none() -> None:
    info = SiteInfo.from_payload(
        {"wordpress_version": "7.1.5", "php_version": "8.2.12", "plugin_version": "0.1.0"}
    )

    assert info.site_name is None
    assert info.site_description is None
    assert info.home_url is None
    assert info.site_url is None
    assert info.timezone is None
    assert info.gmt_offset is None
    assert info.locale is None


@pytest.mark.parametrize(
    "payload",
    [
        {**SITE_INFO_PAYLOAD, "wordpress_version": "not a version"},
        {**SITE_INFO_PAYLOAD, "site_name": ["unexpected"]},
        {**SITE_INFO_PAYLOAD, "home_url": "javascript:alert(1)"},
        {**SITE_INFO_PAYLOAD, "site_url": "https://user:secret@example.test/"},
        {**SITE_INFO_PAYLOAD, "gmt_offset": True},
        {**SITE_INFO_PAYLOAD, "admin_email": "private@example.test"},
        {**SITE_INFO_PAYLOAD, "database_password": "private-value"},
        {**SITE_INFO_PAYLOAD, "private_key": "private-value"},
    ],
)
def test_site_info_model_rejects_malformed_or_sensitive_fields(payload: dict[str, object]) -> None:
    with pytest.raises(SiteConnectionError):
        SiteInfo.from_payload(payload)


@pytest.mark.anyio
async def test_site_info_client_uses_fixed_read_only_get_route() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == "http://127.0.0.1/sitepilot-test/wp-json/sitepilot/v1/site-info"
        return httpx.Response(200, json=SITE_INFO_PAYLOAD, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"),
        transport=httpx.MockTransport(handler),
    )

    info = await client.fetch_site_info()

    assert info.site_name == "Example Site"
    assert info.plugin_version == "0.1.0"


@pytest.mark.anyio
async def test_site_info_client_uses_existing_credential_provider() -> None:
    class FakeProvider:
        requested_reference: str | None = None

        def get_password(self, credential_ref: str) -> str:
            self.requested_reference = credential_ref
            return "test-only-credential"

    provider = FakeProvider()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers.get("authorization") is not None
        return httpx.Response(200, json=SITE_INFO_PAYLOAD, request=request)

    client = WordPressClient(
        SiteConfig(
            base_url="https://127.0.0.1/sitepilot-test",
            username="test-user",
            credential_ref="test-reference",
        ),
        provider,
        transport=httpx.MockTransport(handler),
    )

    await client.fetch_site_info()

    assert provider.requested_reference == "test-reference"


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_site_info_authentication_and_permission_failures_are_sanitized(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="PRIVATE_RESPONSE_BODY", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"),
        transport=httpx.MockTransport(handler),
    )
    result = await SiteInfoTool(client).run()

    assert result["connection_status"] == "authentication_required"
    assert result["site_name"] is None
    assert "PRIVATE_RESPONSE_BODY" not in str(result)


@pytest.mark.anyio
async def test_site_info_http_and_transport_errors_are_safe() -> None:
    async def http_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="PRIVATE_RESPONSE_BODY", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(http_error)
    )
    result = await SiteInfoTool(client).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_RESPONSE_BODY" not in str(result)

    async def network_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_EXCEPTION_DETAIL", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(network_error)
    )
    result = await SiteInfoTool(client).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_EXCEPTION_DETAIL" not in str(result)


@pytest.mark.anyio
async def test_site_info_mcp_tool_is_registered_and_has_no_url_argument(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    monkeypatch.delenv("SITEPILOT_WP_USERNAME", raising=False)
    monkeypatch.delenv("SITEPILOT_CREDENTIAL_REF", raising=False)
    monkeypatch.delenv("SITEPILOT_CA_CERT", raising=False)

    class FakeInfoTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self) -> dict[str, str | float | None]:
            return {"connection_status": "connected", "site_name": "Example Site"}

    monkeypatch.setattr(server_module, "SiteInfoTool", FakeInfoTool)
    server = server_module.create_server()
    tools = await server.list_tools()
    tool = next(tool for tool in tools if tool.name == "site_info")
    result = await server.call_tool("site_info", {})

    assert tool.name == "site_info"
    assert "url" not in str(tool.input_schema)
    assert result.structured_content["site_name"] == "Example Site"
