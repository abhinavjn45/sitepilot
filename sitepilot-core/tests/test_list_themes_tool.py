from __future__ import annotations

import httpx
import pytest

import sitepilot_core.server as server_module
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_themes import ListThemesTool
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import ThemeList

THEME_ENTRIES = [
    {
        "stylesheet": "sitepilot-child",
        "name": "SitePilot Child",
        "version": "1.0.0",
        "status": "active",
        "description": "A child theme.",
        "author": "Example Author",
        "template": "sitepilot-parent",
    },
    {
        "stylesheet": "sitepilot-parent",
        "name": "SitePilot Parent",
        "version": "2.0.0",
        "status": "inactive",
        "description": "A parent theme.",
        "author": "Example Author",
        "template": None,
    },
]


@pytest.mark.anyio
async def test_lists_multiple_themes_and_child_parent_relationship() -> None:
    class FakeClient:
        async def fetch_themes(self) -> ThemeList:
            return ThemeList.from_payload({"themes": THEME_ENTRIES})

    result = await ListThemesTool(FakeClient()).run()  # type: ignore[arg-type]

    assert result == {
        "connection_status": "connected",
        "themes": THEME_ENTRIES,
        "message": "Installed WordPress themes retrieved successfully.",
    }
    assert result["themes"][0]["template"] == "sitepilot-parent"


def test_theme_list_accepts_empty_list_and_missing_optional_metadata() -> None:
    empty = ThemeList.from_payload({"themes": []})
    missing = ThemeList.from_payload({"themes": [{"stylesheet": "theme-slug", "status": "inactive"}]})

    assert empty.themes == ()
    assert missing.themes[0].stylesheet == "theme-slug"
    assert missing.themes[0].name is None
    assert missing.themes[0].version is None
    assert missing.themes[0].description is None
    assert missing.themes[0].author is None
    assert missing.themes[0].template is None


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"themes": "not-a-list"},
        {"themes": [{"name": "Missing status"}]},
        {"themes": [{"status": "inactive"}]},
        {"themes": [{**THEME_ENTRIES[0], "status": "enabled"}]},
        {"themes": [{**THEME_ENTRIES[0], "status": []}]},
        {"themes": [{**THEME_ENTRIES[0], "stylesheet": "../private-theme"}]},
        {"themes": [{**THEME_ENTRIES[0], "template": "D:/private/theme"}]},
        {"themes": [{**THEME_ENTRIES[0], "author": {"token": "PRIVATE"}}]},
        {"themes": [{**THEME_ENTRIES[0], "database_password": "PRIVATE"}]},
        {"themes": THEME_ENTRIES, "server_path": "PRIVATE"},
    ],
)
def test_rejects_malformed_or_sensitive_theme_responses(payload: object) -> None:
    with pytest.raises(SiteConnectionError):
        ThemeList.from_payload(payload)


@pytest.mark.anyio
async def test_theme_client_uses_fixed_read_only_get_route() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == "http://127.0.0.1/sitepilot-test/wp-json/sitepilot/v1/themes"
        return httpx.Response(200, json={"themes": THEME_ENTRIES}, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"),
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_themes()

    assert len(result.themes) == 2
    assert result.themes[0].status == "active"
    assert result.themes[0].template == "sitepilot-parent"


@pytest.mark.anyio
async def test_theme_client_uses_existing_credential_provider() -> None:
    class FakeProvider:
        requested_reference: str | None = None

        def get_password(self, credential_ref: str) -> str:
            self.requested_reference = credential_ref
            return "test-only-credential"

    provider = FakeProvider()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers.get("authorization") is not None
        return httpx.Response(200, json={"themes": THEME_ENTRIES}, request=request)

    client = WordPressClient(
        SiteConfig(
            base_url="https://127.0.0.1/sitepilot-test",
            username="test-user",
            credential_ref="test-reference",
        ),
        provider,
        transport=httpx.MockTransport(handler),
    )

    await client.fetch_themes()

    assert provider.requested_reference == "test-reference"


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_theme_authentication_and_permission_errors_are_sanitized(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler)
    )
    result = await ListThemesTool(client).run()

    assert result["connection_status"] == "authentication_required"
    assert result["themes"] is None
    assert "PRIVATE_RESPONSE" not in str(result)


@pytest.mark.anyio
async def test_theme_http_and_transport_errors_are_sanitized() -> None:
    async def http_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="PRIVATE_RESPONSE", request=request)

    result = await ListThemesTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(http_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert result["themes"] is None
    assert "PRIVATE_RESPONSE" not in str(result)

    async def transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_EXCEPTION", request=request)

    result = await ListThemesTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(transport_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_EXCEPTION" not in str(result)


@pytest.mark.anyio
async def test_list_themes_mcp_tool_is_registered_without_url_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    monkeypatch.delenv("SITEPILOT_WP_USERNAME", raising=False)
    monkeypatch.delenv("SITEPILOT_CREDENTIAL_REF", raising=False)
    monkeypatch.delenv("SITEPILOT_CA_CERT", raising=False)

    class FakeListThemesTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self) -> dict[str, object]:
            return {"connection_status": "connected", "themes": []}

    monkeypatch.setattr(server_module, "ListThemesTool", FakeListThemesTool)
    server = server_module.create_server()
    tools = await server.list_tools()
    tool = next(tool for tool in tools if tool.name == "list_themes")
    result = await server.call_tool("list_themes", {})

    assert tool.name == "list_themes"
    assert "url" not in str(tool.input_schema)
    assert result.structured_content["themes"] == []
