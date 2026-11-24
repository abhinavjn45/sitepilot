from __future__ import annotations

import ssl

import certifi
import httpx
import pytest

import sitepilot_core.server as server_module
import sitepilot_core.wordpress.client as wordpress_client
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_media import ListMediaTool
from sitepilot_core.wordpress.client import WordPressClient, _MAX_RESPONSE_BYTES
from sitepilot_core.wordpress.models import MediaList


def media_entry(
    media_id: int,
    *,
    filename: str = "asset.bin",
    mime_type: str = "application/octet-stream",
    media_type: str = "file",
    **overrides: object,
) -> dict[str, object]:
    return {
        "id": media_id,
        "title": f"Asset {media_id}",
        "slug": f"asset-{media_id}",
        "filename": filename,
        "mime_type": mime_type,
        "media_type": media_type,
        "date": "2026-11-23T09:30:00+00:00",
        "modified": "2026-11-23T10:00:00+00:00",
        "alt_text": None,
        "caption": None,
        "description": None,
        "source_url": f"https://127.0.0.1/sitepilot-test/wp-content/uploads/{filename.replace(' ', '%20')}",
        **overrides,
    }


def media_payload(
    media: list[dict[str, object]] | None = None,
    *,
    page: int = 1,
    per_page: int = 10,
    total_items: int | None = None,
) -> dict[str, object]:
    entries = media or []
    count = len(entries) if total_items is None else total_items
    return {
        "connection_status": "connected",
        "media": entries,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": count,
            "total_pages": (count + per_page - 1) // per_page,
        },
        "message": "Media retrieved successfully.",
    }


@pytest.mark.anyio
async def test_lists_multiple_media_types_and_extracts_bare_filenames() -> None:
    payload = media_payload(
        [
            media_entry(30, filename="cover photo.jpg", mime_type="image/jpeg", media_type="image", alt_text="Cover"),
            media_entry(29, filename="clip.mp4", mime_type="video/mp4", media_type="video"),
            media_entry(28, filename="audio.mp3", mime_type="audio/mpeg", media_type="audio"),
            media_entry(27, filename="report.pdf", mime_type="application/pdf", media_type="file"),
        ],
        page=2,
        per_page=4,
        total_items=7,
    )

    class FakeClient:
        async def fetch_media(self, page: int, per_page: int) -> MediaList:
            assert (page, per_page) == (2, 4)
            return MediaList.from_payload(payload)

    result = await ListMediaTool(FakeClient()).run(2, 4)  # type: ignore[arg-type]
    assert result["connection_status"] == "connected"
    assert [item["media_type"] for item in result["media"]] == ["image", "video", "audio", "file"]
    assert result["media"][0]["filename"] == "cover photo.jpg"
    assert all("/" not in item["filename"] and "\\" not in item["filename"] for item in result["media"])
    assert result["pagination"]["total_pages"] == 2


def test_model_accepts_empty_results_and_missing_optional_metadata() -> None:
    empty = MediaList.from_payload(media_payload())
    payload = media_payload([{"id": 8, "media_type": "file"}], total_items=1)
    item = MediaList.from_payload(payload).media[0]
    assert empty.media == ()
    assert item.title is item.slug is item.filename is item.mime_type is None
    assert item.date is item.modified is item.alt_text is item.caption is item.description is item.source_url is None


@pytest.mark.anyio
async def test_tool_returns_empty_array_for_successful_empty_library() -> None:
    class EmptyMediaClient:
        async def fetch_media(self, page: int, per_page: int) -> MediaList:
            return MediaList.from_payload(media_payload())

    result = await ListMediaTool(EmptyMediaClient()).run()  # type: ignore[arg-type]
    assert result["connection_status"] == "connected"
    assert result["media"] == []


def test_model_suppresses_absolute_paths_from_text_fields() -> None:
    payload = media_payload(
        [media_entry(7, title="stored at D:\\private\\uploads\\secret.jpg", description="Path:/srv/www/private/file")],
        total_items=1,
    )
    item = MediaList.from_payload(payload).media[0]
    assert item.title is None
    assert item.description is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update({"private_config": "SECRET"}),
        lambda payload: payload["media"][0].update({"metadata": {"private": "SECRET"}}),
        lambda payload: payload["media"][0].update({"path": "D:\\private\\secret.jpg"}),
        lambda payload: payload["media"][0].update({"password": "SECRET"}),
        lambda payload: payload["media"][0].update({"id": True}),
        lambda payload: payload["media"][0].pop("id"),
        lambda payload: payload["media"][0].pop("media_type"),
        lambda payload: payload["media"][0].update({"media_type": "directory"}),
        lambda payload: payload["media"][0].update({"mime_type": "not-a-mime"}),
        lambda payload: payload["media"][0].update({"mime_type": "image/jpeg", "media_type": "audio"}),
        lambda payload: payload["media"][0].update({"filename": "D:\\private\\file.jpg"}),
        lambda payload: payload["media"][0].update({"filename": "../file.jpg"}),
        lambda payload: payload["media"][0].update({"source_url": "https://user:pass@example.test/file"}),
        lambda payload: payload["media"][0].update({"source_url": "https://example.test/file?token=PRIVATE"}),
        lambda payload: payload["media"][0].update({"date": "not-a-date"}),
        lambda payload: payload["pagination"].update({"total_pages": 99}),
        lambda payload: payload.update({"media": "not-an-array"}),
        lambda payload: payload.update({"connection_status": "unavailable"}),
    ],
)
def test_rejects_malformed_or_sensitive_media_response(mutate) -> None:
    payload = media_payload([media_entry(3)], total_items=1)
    mutate(payload)
    with pytest.raises(SiteConnectionError):
        MediaList.from_payload(payload)


@pytest.mark.anyio
async def test_media_client_uses_fixed_get_route_and_query_parameters() -> None:
    payload = media_payload([media_entry(7)], page=3, per_page=4, total_items=9)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sitepilot-test/wp-json/sitepilot/v1/media"
        assert dict(request.url.params) == {"page": "3", "per_page": "4"}
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"), transport=httpx.MockTransport(handler)
    )
    assert (await client.fetch_media(3, 4)).pagination.page == 3


@pytest.mark.anyio
async def test_media_client_reuses_configured_credential_provider() -> None:
    class FakeProvider:
        requested_reference: str | None = None

        def get_password(self, credential_ref: str) -> str:
            self.requested_reference = credential_ref
            return "test-only-secret"

    provider = FakeProvider()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("authorization") is not None
        return httpx.Response(200, json=media_payload(), request=request)

    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1", username="test-user", credential_ref="test-ref"),
        provider,
        transport=httpx.MockTransport(handler),
    )
    await client.fetch_media()
    assert provider.requested_reference == "test-ref"


@pytest.mark.anyio
async def test_media_default_and_maximum_page_size() -> None:
    requested: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(dict(request.url.params))
        page = int(request.url.params["page"])
        size = int(request.url.params["per_page"])
        return httpx.Response(200, json=media_payload([], page=page, per_page=size), request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    await client.fetch_media()
    await client.fetch_media(per_page=50)
    await client.fetch_media(page=10_000, per_page=50)
    assert requested == [
        {"page": "1", "per_page": "10"},
        {"page": "1", "per_page": "50"},
        {"page": "10000", "per_page": "50"},
    ]


@pytest.mark.anyio
async def test_invalid_media_pagination_is_rejected_without_http() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json=media_payload(), request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    for page, per_page in ((0, 10), (-1, 10), (10_001, 10), (True, 10), (1, 0), (1, 51), (1, True)):
        with pytest.raises(SiteConnectionError, match="parameters are invalid"):
            await client.fetch_media(page, per_page)  # type: ignore[arg-type]
    assert requests == 0

    class UnusedClient:
        async def fetch_media(self, *args) -> MediaList:
            pytest.fail("invalid input must not trigger an HTTP request")

    result = await ListMediaTool(UnusedClient()).run(per_page=51)  # type: ignore[arg-type]
    assert result["connection_status"] == "invalid_request"
    assert result["media"] is None


@pytest.mark.anyio
async def test_authentication_http_and_transport_failures_are_sanitized() -> None:
    for status_code in (401, 403, 500):
        def response_handler(request: httpx.Request, status_code: int = status_code) -> httpx.Response:
            return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

        result = await ListMediaTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(response_handler))
        ).run()
        expected = "authentication_required" if status_code in (401, 403) else "unavailable"
        assert result["connection_status"] == expected
        assert result["media"] is None and result["pagination"] is None
        assert "PRIVATE_RESPONSE" not in str(result)

    async def connection_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_EXCEPTION", request=request)

    async def timeout_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("PRIVATE_TIMEOUT", request=request)

    for handler, private_value in ((connection_error, "PRIVATE_EXCEPTION"), (timeout_error, "PRIVATE_TIMEOUT")):
        result = await ListMediaTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
        ).run()
        assert result["media"] is None
        assert private_value not in str(result)


@pytest.mark.anyio
async def test_media_client_rejects_malformed_json_and_oversized_response() -> None:
    responses = (
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
            await client.fetch_media()
        assert "PRIVATE_" not in str(error.value)


@pytest.mark.anyio
async def test_media_client_uses_normal_tls_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    original_async_client = httpx.AsyncClient
    captured: dict[str, object] = {}

    def create_client(*args, **kwargs):
        captured["verify"] = kwargs["verify"]
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(wordpress_client.httpx, "AsyncClient", create_client)
    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1", ca_cert_path=certifi.where()),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=media_payload(), request=request)),
    )
    await client.fetch_media()
    context = captured["verify"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.anyio
async def test_list_media_mcp_registration_and_read_only_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    monkeypatch.delenv("SITEPILOT_WP_USERNAME", raising=False)
    monkeypatch.delenv("SITEPILOT_CREDENTIAL_REF", raising=False)
    monkeypatch.delenv("SITEPILOT_CA_CERT", raising=False)

    class FakeListMediaTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self, page: int, per_page: int) -> dict[str, object]:
            return media_payload([], page=page, per_page=per_page)

    monkeypatch.setattr(server_module, "ListMediaTool", FakeListMediaTool)
    server = server_module.create_server()
    registered = await server.list_tools()
    tool = next(item for item in registered if item.name == "list_media")
    result = await server.call_tool("list_media", {})
    schema = str(tool.input_schema)
    assert "page" in schema and "per_page" in schema
    assert "url" not in schema
    assert result.structured_content["pagination"] == {
        "page": 1,
        "per_page": 10,
        "total_items": 0,
        "total_pages": 0,
    }
