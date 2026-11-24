from __future__ import annotations

import httpx
import pytest

import sitepilot_core.server as server_module
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_pages import ListPagesTool
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import PageList


def page_entry(
    page_id: int,
    *,
    status: str = "publish",
    title: str | None = "Example page",
    parent_id: int = 0,
    menu_order: int = 0,
) -> dict[str, object]:
    return {
        "id": page_id,
        "title": title,
        "slug": f"example-page-{page_id}",
        "status": status,
        "author_id": 3,
        "date": "2026-11-23T09:30:00+00:00",
        "modified": "2026-11-23T10:00:00+00:00",
        "link": f"https://127.0.0.1/sitepilot-test/page-{page_id}/",
        "parent_id": parent_id,
        "menu_order": menu_order,
    }


def pages_payload(
    pages: list[dict[str, object]] | None = None,
    *,
    page: int = 1,
    per_page: int = 10,
    total_items: int | None = None,
    status: str = "publish",
) -> dict[str, object]:
    entries = pages or []
    count = len(entries) if total_items is None else total_items
    return {
        "connection_status": "connected",
        "pages": entries,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": count,
            "total_pages": (count + per_page - 1) // per_page,
            "status": status,
        },
        "message": "Pages retrieved successfully.",
    }


@pytest.mark.anyio
async def test_lists_multiple_pages_and_pagination() -> None:
    payload = pages_payload(
        [page_entry(20, parent_id=4, menu_order=2), page_entry(19, menu_order=1)],
        page=2,
        per_page=2,
        total_items=3,
    )

    class FakeClient:
        async def fetch_pages(self, page: int, per_page: int, status: str) -> PageList:
            assert (page, per_page, status) == (2, 2, "publish")
            return PageList.from_payload(payload)

    result = await ListPagesTool(FakeClient()).run(2, 2)  # type: ignore[arg-type]
    assert result["connection_status"] == "connected"
    assert [item["id"] for item in result["pages"]] == [20, 19]
    assert result["pages"][0]["parent_id"] == 4
    assert result["pages"][0]["menu_order"] == 2
    assert result["pagination"]["total_pages"] == 2


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["draft", "future", "pending", "private"])
async def test_supported_nonpublished_statuses_are_explicit(status: str) -> None:
    payload = pages_payload([page_entry(5, status=status)], total_items=1, status=status)

    class FakeClient:
        async def fetch_pages(self, page: int, per_page: int, requested_status: str) -> PageList:
            assert requested_status == status
            return PageList.from_payload(payload)

    result = await ListPagesTool(FakeClient()).run(status=status)  # type: ignore[arg-type]
    assert result["pages"][0]["status"] == status


def test_model_accepts_empty_pages_and_missing_optional_fields() -> None:
    empty = PageList.from_payload(pages_payload())
    missing = pages_payload(
        [{"id": 8, "status": "publish", "author_id": 0, "parent_id": 0, "menu_order": 0}],
        total_items=1,
    )
    result = PageList.from_payload(missing).pages[0]
    assert empty.pages == ()
    assert result.title is result.slug is result.date is result.modified is result.link is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update({"secret": "PRIVATE"}),
        lambda payload: payload["pages"][0].update({"content": "PRIVATE BODY"}),
        lambda payload: payload["pages"][0].update({"author_email": "private@example.test"}),
        lambda payload: payload["pages"][0].update({"password": "PRIVATE"}),
        lambda payload: payload["pages"][0].update({"id": True}),
        lambda payload: payload["pages"][0].update({"status": "trash"}),
        lambda payload: payload["pages"][0].update({"parent_id": -1}),
        lambda payload: payload["pages"][0].update({"menu_order": "one"}),
        lambda payload: payload["pages"][0].update({"date": "not-a-date"}),
        lambda payload: payload["pages"][0].update({"link": "javascript:alert(1)"}),
        lambda payload: payload["pagination"].update({"total_pages": 99}),
        lambda payload: payload.update({"pages": "not-an-array"}),
    ],
)
def test_rejects_malformed_or_sensitive_page_responses(mutate) -> None:
    payload = pages_payload([page_entry(3)], total_items=1)
    mutate(payload)
    with pytest.raises(SiteConnectionError):
        PageList.from_payload(payload)


@pytest.mark.anyio
async def test_pages_client_uses_fixed_get_route_and_query_parameters() -> None:
    payload = pages_payload([page_entry(4)], page=3, per_page=7, total_items=15)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sitepilot-test/wp-json/sitepilot/v1/pages"
        assert dict(request.url.params) == {"page": "3", "per_page": "7", "status": "publish"}
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"), transport=httpx.MockTransport(handler)
    )
    result = await client.fetch_pages(3, 7)
    assert result.pagination.page == 3


@pytest.mark.anyio
async def test_default_and_maximum_page_size() -> None:
    seen: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(dict(request.url.params))
        requested_page_size = int(request.url.params["per_page"])
        return httpx.Response(
            200,
            json=pages_payload([], per_page=requested_page_size, status="publish"),
            request=request,
        )

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler)
    )
    await client.fetch_pages()
    await client.fetch_pages(per_page=50)
    assert seen == [
        {"page": "1", "per_page": "10", "status": "publish"},
        {"page": "1", "per_page": "50", "status": "publish"},
    ]


@pytest.mark.anyio
async def test_invalid_query_is_rejected_before_request() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json=pages_payload(), request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler)
    )
    for page, per_page, status in (
        (0, 10, "publish"), (-1, 10, "publish"), (10_001, 10, "publish"),
        (True, 10, "publish"), (1, 0, "publish"), (1, 51, "publish"),
        (1, True, "publish"), (1, 10, "trash"), (1, 10, "any"),
    ):
        with pytest.raises(SiteConnectionError, match="parameters are invalid"):
            await client.fetch_pages(page, per_page, status)  # type: ignore[arg-type]
    assert requests == 0

    class UnusedClient:
        async def fetch_pages(self, *args) -> PageList:
            pytest.fail("invalid input must not reach the HTTP client")

    invalid_result = await ListPagesTool(UnusedClient()).run(page=0)  # type: ignore[arg-type]
    assert invalid_result["connection_status"] == "invalid_request"
    assert invalid_result["pages"] is None


@pytest.mark.anyio
async def test_auth_http_and_transport_errors_are_sanitized() -> None:
    for status_code in (401, 403, 500):
        def response_handler(request: httpx.Request, status_code: int = status_code) -> httpx.Response:
            return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

        result = await ListPagesTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(response_handler))
        ).run()
        expected = "authentication_required" if status_code in (401, 403) else "unavailable"
        assert result["connection_status"] == expected
        assert result["pages"] is None and result["pagination"] is None
        assert "PRIVATE_RESPONSE" not in str(result)

    async def transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_EXCEPTION", request=request)

    result = await ListPagesTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(transport_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_EXCEPTION" not in str(result)


@pytest.mark.anyio
async def test_list_pages_mcp_tool_is_registered_with_bounded_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    monkeypatch.delenv("SITEPILOT_WP_USERNAME", raising=False)
    monkeypatch.delenv("SITEPILOT_CREDENTIAL_REF", raising=False)
    monkeypatch.delenv("SITEPILOT_CA_CERT", raising=False)

    class FakeListPagesTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self, page: int, per_page: int, status: str) -> dict[str, object]:
            return pages_payload([], page=page, per_page=per_page, status=status)

    monkeypatch.setattr(server_module, "ListPagesTool", FakeListPagesTool)
    server = server_module.create_server()
    registered = await server.list_tools()
    tool = next(item for item in registered if item.name == "list_pages")
    result = await server.call_tool("list_pages", {})
    schema = str(tool.input_schema)
    assert "page" in schema and "per_page" in schema and "status" in schema
    assert "url" not in schema
    assert result.structured_content["pagination"]["per_page"] == 10
    assert result.structured_content["pagination"]["status"] == "publish"
