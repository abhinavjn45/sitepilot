from __future__ import annotations

import httpx
import pytest

import sitepilot_core.server as server_module
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_plugins import ListPluginsTool
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import PluginList

PLUGIN_ENTRIES = [
    {
        "plugin_file": "sitepilot/sitepilot-connect.php",
        "name": "SitePilot",
        "version": "0.1.0",
        "status": "active",
        "description": "Provides safe WordPress connector routes.",
        "author": "SitePilot",
    },
    {
        "plugin_file": "hello.php",
        "name": "Hello Plugin",
        "version": None,
        "status": "inactive",
        "description": None,
        "author": None,
    },
]


@pytest.mark.anyio
async def test_lists_multiple_active_and_inactive_plugins() -> None:
    class FakeClient:
        async def fetch_plugins(self) -> PluginList:
            return PluginList.from_payload({"plugins": PLUGIN_ENTRIES})

    result = await ListPluginsTool(FakeClient()).run()  # type: ignore[arg-type]

    assert result == {
        "connection_status": "connected",
        "plugins": PLUGIN_ENTRIES,
        "message": "Installed WordPress plugins retrieved successfully.",
    }


def test_plugin_list_accepts_empty_list_and_missing_optional_metadata() -> None:
    empty = PluginList.from_payload({"plugins": []})
    missing = PluginList.from_payload(
        {"plugins": [{"status": "inactive"}]}
    )

    assert empty.plugins == ()
    assert missing.plugins[0].name is None
    assert missing.plugins[0].plugin_file is None
    assert missing.plugins[0].description is None
    assert missing.plugins[0].author is None


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"plugins": "not-a-list"},
        {"plugins": [{"name": "Missing fields"}]},
        {"plugins": [{**PLUGIN_ENTRIES[0], "status": "enabled"}]},
        {"plugins": [{**PLUGIN_ENTRIES[0], "status": []}]},
        {"plugins": [{**PLUGIN_ENTRIES[0], "plugin_file": "../private.php"}]},
        {"plugins": [{**PLUGIN_ENTRIES[0], "author": {"token": "PRIVATE"}}]},
        {"plugins": [{**PLUGIN_ENTRIES[0], "database_password": "PRIVATE"}]},
        {"plugins": PLUGIN_ENTRIES, "server_path": "PRIVATE"},
    ],
)
def test_rejects_malformed_or_sensitive_plugin_responses(payload: object) -> None:
    with pytest.raises(SiteConnectionError):
        PluginList.from_payload(payload)


@pytest.mark.anyio
async def test_plugin_client_uses_fixed_read_only_get_route() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == "http://127.0.0.1/sitepilot-test/wp-json/sitepilot/v1/plugins"
        return httpx.Response(200, json={"plugins": PLUGIN_ENTRIES}, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"),
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_plugins()

    assert len(result.plugins) == 2
    assert result.plugins[0].status == "active"


@pytest.mark.anyio
async def test_plugin_client_uses_existing_credential_provider() -> None:
    class FakeProvider:
        requested_reference: str | None = None

        def get_password(self, credential_ref: str) -> str:
            self.requested_reference = credential_ref
            return "test-only-credential"

    provider = FakeProvider()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers.get("authorization") is not None
        return httpx.Response(200, json={"plugins": PLUGIN_ENTRIES}, request=request)

    client = WordPressClient(
        SiteConfig(
            base_url="https://127.0.0.1/sitepilot-test",
            username="test-user",
            credential_ref="test-reference",
        ),
        provider,
        transport=httpx.MockTransport(handler),
    )

    await client.fetch_plugins()

    assert provider.requested_reference == "test-reference"


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_plugin_authentication_and_permission_errors_are_sanitized(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler)
    )
    result = await ListPluginsTool(client).run()

    assert result["connection_status"] == "authentication_required"
    assert result["plugins"] is None
    assert "PRIVATE_RESPONSE" not in str(result)


@pytest.mark.anyio
async def test_plugin_http_and_transport_errors_are_sanitized() -> None:
    async def http_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="PRIVATE_RESPONSE", request=request)

    result = await ListPluginsTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(http_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_RESPONSE" not in str(result)

    async def transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_EXCEPTION", request=request)

    result = await ListPluginsTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(transport_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_EXCEPTION" not in str(result)


@pytest.mark.anyio
async def test_list_plugins_mcp_tool_is_registered_without_url_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    monkeypatch.delenv("SITEPILOT_WP_USERNAME", raising=False)
    monkeypatch.delenv("SITEPILOT_CREDENTIAL_REF", raising=False)
    monkeypatch.delenv("SITEPILOT_CA_CERT", raising=False)

    class FakeListPluginsTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self) -> dict[str, object]:
            return {"connection_status": "connected", "plugins": []}

    monkeypatch.setattr(server_module, "ListPluginsTool", FakeListPluginsTool)
    server = server_module.create_server()
    tools = await server.list_tools()
    tool = next(tool for tool in tools if tool.name == "list_plugins")
    result = await server.call_tool("list_plugins", {})

    assert tool.name == "list_plugins"
    assert "url" not in str(tool.input_schema)
    assert result.structured_content["plugins"] == []
