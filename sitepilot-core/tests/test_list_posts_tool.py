from __future__ import annotations

from copy import deepcopy

import httpx
import pytest

import sitepilot_core.server as server_module
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_posts import ListPostsTool
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import (
    DEFAULT_POSTS_PER_PAGE,
    MAX_POSTS_PER_PAGE,
    PostList,
)

POSTS_PAYLOAD = {
    "connection_status": "connected",
    "posts": [
        {
            "id": 42,
            "title": "A published post",
            "slug": "a-published-post",
            "status": "publish",
            "author_id": 3,
            "date": "2026-11-23T09:30:00+00:00",
            "modified": "2026-11-23T10:00:00+00:00",
            "link": "https://127.0.0.1/sitepilot-test/a-published-post/",
            "categories": [2],
            "tags": [5, 6],
        },
        {
            "id": 41,
            "title": "Another published post",
            "slug": "another-published-post",
            "status": "publish",
            "author_id": 3,
            "date": "2026-11-22T09:30:00+00:00",
            "modified": "2026-11-22T10:00:00+00:00",
            "link": "https://127.0.0.1/sitepilot-test/another-published-post/",
            "categories": [],
            "tags": [],
        },
    ],
    "pagination": {
        "page": 2,
        "per_page": 2,
        "total_items": 3,
        "total_pages": 2,
        "status": "publish",
    },
    "message": "Posts retrieved successfully.",
}


@pytest.mark.anyio
async def test_lists_multiple_posts_and_pagination() -> None:
    class FakeClient:
        async def fetch_posts(self, page: int, per_page: int, status: str) -> PostList:
            assert (page, per_page, status) == (2, 2, "publish")
            return PostList.from_payload(POSTS_PAYLOAD)

    result = await ListPostsTool(FakeClient()).run(2, 2, "publish")  # type: ignore[arg-type]

    assert result["connection_status"] == "connected"
    assert len(result["posts"]) == 2
    assert result["posts"][0]["status"] == "publish"
    assert result["posts"][0]["categories"] == [2]
    assert result["pagination"] == POSTS_PAYLOAD["pagination"]


@pytest.mark.anyio
async def test_supported_non_published_status_is_passed_explicitly() -> None:
    draft_payload = deepcopy(POSTS_PAYLOAD)
    draft_payload["posts"] = [
        {**POSTS_PAYLOAD["posts"][0], "status": "draft"},
    ]
    draft_payload["pagination"] = {
        "page": 1,
        "per_page": 10,
        "total_items": 1,
        "total_pages": 1,
        "status": "draft",
    }

    class FakeClient:
        async def fetch_posts(self, page: int, per_page: int, status: str) -> PostList:
            assert (page, per_page, status) == (1, 10, "draft")
            return PostList.from_payload(draft_payload)

    result = await ListPostsTool(FakeClient()).run(status="draft")  # type: ignore[arg-type]

    assert result["posts"][0]["status"] == "draft"


@pytest.mark.anyio
async def test_defaults_to_first_page_ten_published_posts() -> None:
    class FakeClient:
        requested: tuple[int, int, str] | None = None

        async def fetch_posts(self, page: int, per_page: int, status: str) -> PostList:
            self.requested = (page, per_page, status)
            empty_payload = {
                "connection_status": "connected",
                "posts": [],
                "pagination": {
                    "page": 1,
                    "per_page": DEFAULT_POSTS_PER_PAGE,
                    "total_items": 0,
                    "total_pages": 0,
                    "status": "publish",
                },
                "message": "Posts retrieved successfully.",
            }
            return PostList.from_payload(empty_payload)

    client = FakeClient()
    result = await ListPostsTool(client).run()  # type: ignore[arg-type]

    assert client.requested == (1, DEFAULT_POSTS_PER_PAGE, "publish")
    assert result["posts"] == []
    assert result["pagination"]["page"] == 1


def test_model_accepts_empty_results_and_missing_optional_metadata() -> None:
    empty_payload = {
        "connection_status": "connected",
        "posts": [],
        "pagination": {"page": 1, "per_page": 10, "total_items": 0, "total_pages": 0, "status": "publish"},
        "message": "Posts retrieved successfully.",
    }
    missing_optional = deepcopy(empty_payload)
    missing_optional["pagination"]["total_items"] = 1
    missing_optional["pagination"]["total_pages"] = 1
    missing_optional["posts"] = [
        {"id": 8, "status": "publish", "author_id": 0, "categories": [], "tags": []}
    ]

    assert PostList.from_payload(empty_payload).posts == ()
    post = PostList.from_payload(missing_optional).posts[0]
    assert post.title is None
    assert post.slug is None
    assert post.date is None
    assert post.modified is None
    assert post.link is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update({"private_config": "SECRET"}),
        lambda payload: payload["posts"][0].update({"content": "PRIVATE BODY"}),
        lambda payload: payload["posts"][0].update({"author_email": "private@example.test"}),
        lambda payload: payload["posts"][0].update({"password": "SECRET"}),
        lambda payload: payload["posts"][0].update({"id": True}),
        lambda payload: payload["posts"][0].update({"status": "trash"}),
        lambda payload: payload["posts"][0].update({"categories": ["not-an-id"]}),
        lambda payload: payload["posts"][0].update({"date": "not-a-date"}),
        lambda payload: payload["posts"][0].update({"link": "javascript:alert(1)"}),
        lambda payload: payload["pagination"].update({"total_pages": 99}),
        lambda payload: payload.update({"posts": "not-an-array"}),
        lambda payload: payload.update({"connection_status": "unavailable"}),
    ],
)
def test_rejects_malformed_or_sensitive_post_responses(mutate) -> None:
    payload = deepcopy(POSTS_PAYLOAD)
    mutate(payload)
    with pytest.raises(SiteConnectionError):
        PostList.from_payload(payload)


@pytest.mark.anyio
async def test_posts_client_uses_fixed_get_endpoint_and_pagination_parameters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sitepilot-test/wp-json/sitepilot/v1/posts"
        assert dict(request.url.params) == {"page": "2", "per_page": "2", "status": "publish"}
        return httpx.Response(200, json=POSTS_PAYLOAD, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"),
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_posts(2, 2, "publish")

    assert len(result.posts) == 2
    assert result.pagination.page == 2


@pytest.mark.anyio
async def test_posts_client_uses_existing_credential_provider() -> None:
    class FakeProvider:
        requested_reference: str | None = None

        def get_password(self, credential_ref: str) -> str:
            self.requested_reference = credential_ref
            return "test-only-credential"

    provider = FakeProvider()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers.get("authorization") is not None
        payload = deepcopy(POSTS_PAYLOAD)
        payload["pagination"].update({"page": 1, "per_page": 10, "total_items": 0, "total_pages": 0})
        payload["posts"] = []
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1/sitepilot-test", username="test-user", credential_ref="test-ref"),
        provider,
        transport=httpx.MockTransport(handler),
    )

    await client.fetch_posts()

    assert provider.requested_reference == "test-ref"


@pytest.mark.anyio
async def test_posts_client_rejects_entries_outside_requested_status_filter() -> None:
    payload = deepcopy(POSTS_PAYLOAD)
    payload["posts"][0]["status"] = "draft"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler)
    )

    with pytest.raises(SiteConnectionError, match="requested status"):
        await client.fetch_posts(2, 2, "publish")


@pytest.mark.anyio
async def test_posts_client_allows_maximum_page_size_and_rejects_invalid_parameters() -> None:
    payload = deepcopy(POSTS_PAYLOAD)
    payload["posts"] = []
    payload["pagination"] = {
        "page": 1,
        "per_page": MAX_POSTS_PER_PAGE,
        "total_items": 0,
        "total_pages": 0,
        "status": "publish",
    }
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler)
    )
    result = await client.fetch_posts(per_page=MAX_POSTS_PER_PAGE)
    assert result.pagination.per_page == 50

    for page, per_page, status in (
        (0, 10, "publish"),
        (-1, 10, "publish"),
        (10_001, 10, "publish"),
        (True, 10, "publish"),
        (1, 0, "publish"),
        (1, 51, "publish"),
        (1, True, "publish"),
        (1, 10, "trash"),
        (1, 10, "any"),
    ):
        with pytest.raises(SiteConnectionError, match="parameters are invalid"):
            await client.fetch_posts(page, per_page, status)  # type: ignore[arg-type]
    assert len(requests) == 1


@pytest.mark.anyio
async def test_invalid_tool_query_returns_structured_error_without_request() -> None:
    class UnusedClient:
        async def fetch_posts(self, *args) -> PostList:
            pytest.fail("invalid query must not make an HTTP request")

    result = await ListPostsTool(UnusedClient()).run(per_page=100)  # type: ignore[arg-type]

    assert result["connection_status"] == "invalid_request"
    assert result["posts"] is None
    assert result["pagination"] is None


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_posts_authentication_and_permission_errors_are_sanitized(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

    result = await ListPostsTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    ).run()

    assert result["connection_status"] == "authentication_required"
    assert result["posts"] is None
    assert result["pagination"] is None
    assert "PRIVATE_RESPONSE" not in str(result)


@pytest.mark.anyio
async def test_posts_http_and_transport_errors_are_sanitized() -> None:
    async def http_error(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="PRIVATE_RESPONSE", request=request)

    result = await ListPostsTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(http_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_RESPONSE" not in str(result)

    async def transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_EXCEPTION", request=request)

    result = await ListPostsTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(transport_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_EXCEPTION" not in str(result)


@pytest.mark.anyio
async def test_list_posts_mcp_tool_is_registered_with_only_bounded_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    monkeypatch.delenv("SITEPILOT_WP_USERNAME", raising=False)
    monkeypatch.delenv("SITEPILOT_CREDENTIAL_REF", raising=False)
    monkeypatch.delenv("SITEPILOT_CA_CERT", raising=False)

    class FakeListPostsTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self, page: int, per_page: int, status: str) -> dict[str, object]:
            return {
                "connection_status": "connected",
                "posts": [],
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total_items": 0,
                    "total_pages": 0,
                    "status": status,
                },
                "message": "WordPress posts retrieved successfully.",
            }

    monkeypatch.setattr(server_module, "ListPostsTool", FakeListPostsTool)
    server = server_module.create_server()
    tools = await server.list_tools()
    tool = next(tool for tool in tools if tool.name == "list_posts")
    result = await server.call_tool("list_posts", {})

    assert tool.name == "list_posts"
    schema = str(tool.input_schema)
    assert "page" in schema and "per_page" in schema and "status" in schema
    assert "url" not in schema
    assert result.structured_content["pagination"]["page"] == 1
    assert result.structured_content["pagination"]["per_page"] == DEFAULT_POSTS_PER_PAGE
    assert result.structured_content["pagination"]["status"] == "publish"
