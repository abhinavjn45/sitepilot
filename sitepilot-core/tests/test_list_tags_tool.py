from __future__ import annotations

import ssl

import certifi
import httpx
import pytest

import sitepilot_core.server as server_module
import sitepilot_core.wordpress.client as wordpress_client
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_tags import ListTagsTool
from sitepilot_core.wordpress.client import WordPressClient, _MAX_RESPONSE_BYTES
from sitepilot_core.wordpress.models import TagList


def tag_entry(tag_id: int, **overrides: object) -> dict[str, object]:
    return {
        "id": tag_id,
        "name": f"Tag {tag_id}",
        "slug": f"tag-{tag_id}",
        "description": f"Description {tag_id}",
        "count": tag_id * 3,
        **overrides,
    }


def tags_payload(
    tags: list[dict[str, object]] | None = None,
    *,
    page: int = 1,
    per_page: int = 10,
    total_items: int | None = None,
) -> dict[str, object]:
    entries = tags or []
    count = len(entries) if total_items is None else total_items
    return {
        "connection_status": "connected",
        "tags": entries,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": count,
            "total_pages": (count + per_page - 1) // per_page,
        },
        "message": "Tags retrieved successfully.",
    }


@pytest.mark.anyio
async def test_lists_multiple_tags_with_allowlisted_fields() -> None:
    payload = tags_payload([tag_entry(8), tag_entry(9, description=None)], page=2, per_page=2, total_items=3)

    class FakeClient:
        async def fetch_tags(self, page: int, per_page: int) -> TagList:
            assert (page, per_page) == (2, 2)
            return TagList.from_payload(payload)

    result = await ListTagsTool(FakeClient()).run(2, 2)  # type: ignore[arg-type]
    assert result["connection_status"] == "connected"
    assert len(result["tags"]) == 2
    assert result["tags"][0]["count"] == 24
    assert result["tags"][1]["description"] is None
    assert set(result["tags"][0]) == {"id", "name", "slug", "description", "count"}
    assert result["pagination"] == {"page": 2, "per_page": 2, "total_items": 3, "total_pages": 2}


def test_model_accepts_empty_tags_and_missing_optional_description() -> None:
    assert TagList.from_payload(tags_payload()).tags == ()
    tag = TagList.from_payload(tags_payload([{"id": 4, "count": 0}])).tags[0]
    assert tag.name is tag.slug is tag.description is None


def test_model_rejects_markup_in_untrusted_tag_descriptions() -> None:
    with pytest.raises(SiteConnectionError, match="untrusted markup"):
        TagList.from_payload(tags_payload([tag_entry(1, description="<script>alert(1)</script>")]))


@pytest.mark.anyio
async def test_tag_client_uses_fixed_get_endpoint_and_query_parameters() -> None:
    payload = tags_payload([tag_entry(7)], page=3, per_page=5, total_items=11)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sitepilot-test/wp-json/sitepilot/v1/tags"
        assert dict(request.url.params) == {"page": "3", "per_page": "5"}
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"), transport=httpx.MockTransport(handler)
    )
    assert (await client.fetch_tags(3, 5)).pagination.total_items == 11


@pytest.mark.anyio
async def test_tag_client_defaults_and_maximum_page_size() -> None:
    requested: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(dict(request.url.params))
        page = int(request.url.params["page"])
        size = int(request.url.params["per_page"])
        return httpx.Response(200, json=tags_payload([], page=page, per_page=size), request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    await client.fetch_tags()
    await client.fetch_tags(10_000, 50)
    assert requested == [{"page": "1", "per_page": "10"}, {"page": "10000", "per_page": "50"}]


@pytest.mark.anyio
async def test_invalid_tag_pagination_is_rejected_without_http() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=tags_payload(), request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    for page, per_page in ((0, 10), (-1, 10), (10_001, 10), (True, 10), (1, 0), (1, 51), (1, True)):
        with pytest.raises(SiteConnectionError, match="parameters are invalid"):
            await client.fetch_tags(page, per_page)  # type: ignore[arg-type]
    assert calls == 0

    class UnusedClient:
        async def fetch_tags(self, *args) -> TagList:
            pytest.fail("invalid MCP parameters must not make an HTTP request")

    result = await ListTagsTool(UnusedClient()).run(per_page=51)  # type: ignore[arg-type]
    assert result["connection_status"] == "invalid_request" and result["tags"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update({"taxonomy": "category"}),
        lambda payload: payload.update({"private_config": "PRIVATE"}),
        lambda payload: payload["tags"][0].update({"meta": {"private": "PRIVATE"}}),
        lambda payload: payload["tags"][0].update({"path": "D:\\private\\site"}),
        lambda payload: payload["tags"][0].update({"credentials": "PRIVATE"}),
        lambda payload: payload["tags"][0].update({"id": True}),
        lambda payload: payload["tags"][0].update({"count": "many"}),
        lambda payload: payload["tags"][0].update({"slug": "bad/tag"}),
        lambda payload: payload["tags"][0].update({"name": "<b>tag</b>"}),
        lambda payload: payload["tags"][0].pop("id"),
        lambda payload: payload["pagination"].update({"total_pages": 99}),
        lambda payload: payload.update({"tags": "not-a-list"}),
        lambda payload: payload.update({"connection_status": "unavailable"}),
    ],
)
def test_model_rejects_unexpected_or_malformed_tag_fields(mutate) -> None:
    payload = tags_payload([tag_entry(1)])
    mutate(payload)
    with pytest.raises(SiteConnectionError):
        TagList.from_payload(payload)


@pytest.mark.anyio
async def test_authentication_permission_and_http_errors_are_sanitized() -> None:
    for status_code in (401, 403, 500):
        def handler(request: httpx.Request, status_code: int = status_code) -> httpx.Response:
            return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

        result = await ListTagsTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
        ).run()
        assert result["tags"] is None and result["pagination"] is None
        assert "PRIVATE_RESPONSE" not in str(result)
        assert result["connection_status"] == ("authentication_required" if status_code in (401, 403) else "unavailable")


@pytest.mark.anyio
async def test_connection_timeout_and_tls_failures_are_sanitized() -> None:
    async def connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_CONNECTION", request=request)

    async def timeout_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("PRIVATE_TIMEOUT", request=request)

    async def tls_error(request: httpx.Request) -> httpx.Response:
        error = httpx.ConnectError("PRIVATE_TLS", request=request)
        error.__cause__ = ssl.SSLCertVerificationError("PRIVATE_CERT")
        raise error

    for handler, secret in (
        (connect_error, "PRIVATE_CONNECTION"), (timeout_error, "PRIVATE_TIMEOUT"), (tls_error, "PRIVATE_TLS")
    ):
        result = await ListTagsTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
        ).run()
        assert result["tags"] is None and secret not in str(result)


@pytest.mark.anyio
async def test_tag_client_rejects_redirect_bad_content_json_and_oversized_body() -> None:
    responses = (
        httpx.Response(302, headers={"Location": "https://example.test", "Content-Type": "application/json"}),
        httpx.Response(200, text="PRIVATE_HTML", headers={"Content-Type": "text/html"}),
        httpx.Response(200, content=b"not-json", headers={"Content-Type": "application/json"}),
        httpx.Response(
            200,
            content=b" " * (_MAX_RESPONSE_BYTES + 1),
            headers={"Content-Type": "application/json"},
        ),
    )
    for response in responses:
        client = WordPressClient(
            SiteConfig(base_url="http://127.0.0.1"),
            transport=httpx.MockTransport(lambda request, response=response: response),
        )
        with pytest.raises(SiteConnectionError) as error:
            await client.fetch_tags()
        assert "PRIVATE" not in str(error.value)


@pytest.mark.anyio
async def test_tag_client_keeps_tls_certificate_verification_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    original = httpx.AsyncClient
    captured: dict[str, object] = {}

    def create_client(*args, **kwargs):
        captured["verify"] = kwargs["verify"]
        return original(*args, **kwargs)

    monkeypatch.setattr(wordpress_client.httpx, "AsyncClient", create_client)
    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1", ca_cert_path=certifi.where()),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=tags_payload(), request=request)),
    )
    await client.fetch_tags()
    context = captured["verify"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True


@pytest.mark.anyio
async def test_list_tags_mcp_registration_and_read_only_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    for key in ("SITEPILOT_WP_USERNAME", "SITEPILOT_CREDENTIAL_REF", "SITEPILOT_CA_CERT"):
        monkeypatch.delenv(key, raising=False)

    class FakeListTagsTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self, page: int, per_page: int) -> dict[str, object]:
            assert (page, per_page) == (1, 10)
            return tags_payload()

    monkeypatch.setattr(server_module, "ListTagsTool", FakeListTagsTool)
    server = server_module.create_server()
    registered = await server.list_tools()
    tool = next(item for item in registered if item.name == "list_tags")
    result = await server.call_tool("list_tags", {})
    schema = str(tool.input_schema)
    assert "page" in schema and "per_page" in schema and "url" not in schema
    assert result.structured_content["tags"] == []
    assert result.structured_content["pagination"] == {
        "page": 1, "per_page": 10, "total_items": 0, "total_pages": 0
    }
