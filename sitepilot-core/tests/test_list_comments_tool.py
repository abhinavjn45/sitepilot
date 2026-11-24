from __future__ import annotations

import ssl

import httpx
import pytest

import sitepilot_core.server as server_module
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_comments import ListCommentsTool
from sitepilot_core.wordpress.client import WordPressClient, _MAX_RESPONSE_BYTES
from sitepilot_core.wordpress.models import CommentList


def comment_entry(comment_id: int, status: str = "approved", **overrides: object) -> dict[str, object]:
    return {
        "id": comment_id,
        "post_id": comment_id + 100,
        "author_name": f"Reader {comment_id}",
        "date": "2026-11-23T09:30:00+00:00",
        "content": f"Comment {comment_id}",
        "status": status,
        "type": "comment",
        **overrides,
    }


def comments_payload(
    comments: list[dict[str, object]] | None = None,
    *,
    page: int = 1,
    per_page: int = 10,
    total_items: int | None = None,
    status: str = "approved",
) -> dict[str, object]:
    entries = comments or []
    count = len(entries) if total_items is None else total_items
    return {
        "connection_status": "connected",
        "comments": entries,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": count,
            "total_pages": (count + per_page - 1) // per_page,
            "status": status,
        },
        "message": "Comments retrieved successfully.",
    }


@pytest.mark.anyio
async def test_lists_multiple_comments_with_allowlisted_fields() -> None:
    payload = comments_payload(
        [comment_entry(9), comment_entry(8, author_name="Editor", type="pingback")],
        page=2,
        per_page=2,
        total_items=3,
    )

    class FakeClient:
        async def fetch_comments(self, page: int, per_page: int, status: str) -> CommentList:
            assert (page, per_page, status) == (2, 2, "approved")
            return CommentList.from_payload(payload)

    result = await ListCommentsTool(FakeClient()).run(2, 2)  # type: ignore[arg-type]
    assert result["connection_status"] == "connected"
    assert len(result["comments"]) == 2
    assert result["comments"][1]["type"] == "pingback"
    assert set(result["comments"][0]) == {
        "id", "post_id", "author_name", "date", "content", "status", "type"
    }
    assert result["pagination"] == {
        "page": 2, "per_page": 2, "total_items": 3, "total_pages": 2, "status": "approved"
    }


def test_model_handles_empty_and_missing_optional_fields() -> None:
    assert CommentList.from_payload(comments_payload()).comments == ()
    item = CommentList.from_payload(
        comments_payload([{"id": 2, "post_id": 1, "status": "approved", "type": "comment"}])
    ).comments[0]
    assert item.author_name is item.date is item.content is None


def test_model_redacts_emails_and_treats_markup_as_plain_text() -> None:
    item = CommentList.from_payload(
        comments_payload(
            [comment_entry(1, author_name="reader@example.test", content="<script>alert(1)</script> hello@example.test")]
        )
    ).comments[0]
    assert item.author_name == "[email removed]"
    assert item.content == "<script>alert(1)</script> [email removed]"
    # Core transports text as data; rendering/HTML execution is not performed.


@pytest.mark.parametrize("status", ["approved", "pending", "spam", "trash"])
@pytest.mark.anyio
async def test_each_allowed_status_is_sent_to_fixed_get_endpoint(status: str) -> None:
    payload = comments_payload([comment_entry(4, status)], status=status)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sitepilot-test/wp-json/sitepilot/v1/comments"
        assert dict(request.url.params) == {"page": "1", "per_page": "10", "status": status}
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"), transport=httpx.MockTransport(handler)
    )
    assert (await client.fetch_comments(status=status)).comments[0].status == status


@pytest.mark.anyio
async def test_comment_query_defaults_bounds_and_rejects_invalid_inputs_without_request() -> None:
    requests: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(dict(request.url.params))
        page = int(request.url.params["page"])
        per_page = int(request.url.params["per_page"])
        status = request.url.params["status"]
        return httpx.Response(
            200, json=comments_payload([], page=page, per_page=per_page, status=status), request=request
        )

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    await client.fetch_comments()
    await client.fetch_comments(10_000, 50, "trash")
    assert requests == [
        {"page": "1", "per_page": "10", "status": "approved"},
        {"page": "10000", "per_page": "50", "status": "trash"},
    ]
    for args in ((0, 10, "approved"), (10_001, 10, "approved"), (1, 0, "approved"),
                 (1, 51, "approved"), (1, 10, "all"), (True, 10, "approved")):
        with pytest.raises(SiteConnectionError, match="parameters are invalid"):
            await client.fetch_comments(*args)  # type: ignore[arg-type]
    assert len(requests) == 2

    class UnusedClient:
        async def fetch_comments(self, *args) -> CommentList:
            pytest.fail("invalid MCP input must not request the site")

    result = await ListCommentsTool(UnusedClient()).run(status="all")  # type: ignore[arg-type]
    assert result["connection_status"] == "invalid_request" and result["comments"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update({"secret": "PRIVATE"}),
        lambda payload: payload["comments"][0].update({"author_email": "reader@example.test"}),
        lambda payload: payload["comments"][0].update({"author_ip": "127.0.0.1"}),
        lambda payload: payload["comments"][0].update({"user_agent": "PRIVATE"}),
        lambda payload: payload["comments"][0].update({"cookies": "PRIVATE"}),
        lambda payload: payload["comments"][0].update({"meta": {"secret": "PRIVATE"}}),
        lambda payload: payload["comments"][0].update({"password": "PRIVATE"}),
        lambda payload: payload["comments"][0].update({"id": True}),
        lambda payload: payload["comments"][0].update({"status": "private"}),
        lambda payload: payload["comments"][0].update({"content": 123}),
        lambda payload: payload["pagination"].update({"total_pages": 9}),
        lambda payload: payload.update({"comments": None}),
        lambda payload: payload.update({"connection_status": "unavailable"}),
    ],
)
def test_model_rejects_malformed_and_sensitive_comment_fields(mutate) -> None:
    payload = comments_payload([comment_entry(1)])
    mutate(payload)
    with pytest.raises(SiteConnectionError):
        CommentList.from_payload(payload)


@pytest.mark.anyio
async def test_authentication_http_and_transport_failures_are_sanitized() -> None:
    for status_code in (401, 403, 500):
        def response_handler(request: httpx.Request, status_code: int = status_code) -> httpx.Response:
            return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

        result = await ListCommentsTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(response_handler))
        ).run()
        assert result["comments"] is None and "PRIVATE_RESPONSE" not in str(result)
        assert result["connection_status"] == ("authentication_required" if status_code in (401, 403) else "unavailable")

    async def connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_CONNECT", request=request)

    async def read_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("PRIVATE_TIMEOUT", request=request)

    async def connect_timeout(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("PRIVATE_CONNECT_TIMEOUT", request=request)

    async def tls_failure(request: httpx.Request) -> httpx.Response:
        error = httpx.ConnectError("PRIVATE_TLS", request=request)
        error.__cause__ = ssl.SSLCertVerificationError("PRIVATE_CERT_DETAIL")
        raise error

    for handler, secret in (
        (connect_error, "PRIVATE_CONNECT"),
        (read_timeout, "PRIVATE_TIMEOUT"),
        (connect_timeout, "PRIVATE_CONNECT_TIMEOUT"),
        (tls_failure, "PRIVATE_TLS"),
    ):
        result = await ListCommentsTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
        ).run()
        assert result["comments"] is None and secret not in str(result)


@pytest.mark.anyio
async def test_comment_http_client_rejects_redirect_content_type_json_and_oversize() -> None:
    responses = (
        httpx.Response(302, headers={"Location": "https://example.test", "Content-Type": "application/json"}),
        httpx.Response(200, text="PRIVATE_HTML", headers={"Content-Type": "text/html"}),
        httpx.Response(200, content=b"not-json", headers={"Content-Type": "application/json"}),
        httpx.Response(200, content=b" " * (_MAX_RESPONSE_BYTES + 1), headers={"Content-Type": "application/json"}),
    )
    for response in responses:
        client = WordPressClient(
            SiteConfig(base_url="http://127.0.0.1"),
            transport=httpx.MockTransport(lambda request, response=response: response),
        )
        with pytest.raises(SiteConnectionError) as error:
            await client.fetch_comments()
        assert "PRIVATE" not in str(error.value)


@pytest.mark.anyio
async def test_comment_client_preserves_tls_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    import certifi
    import sitepilot_core.wordpress.client as wordpress_client

    original = httpx.AsyncClient
    captured: dict[str, object] = {}

    def create_client(*args, **kwargs):
        captured["verify"] = kwargs["verify"]
        return original(*args, **kwargs)

    monkeypatch.setattr(wordpress_client.httpx, "AsyncClient", create_client)
    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1", ca_cert_path=certifi.where()),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=comments_payload(), request=request)),
    )
    await client.fetch_comments()
    context = captured["verify"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True


@pytest.mark.anyio
async def test_list_comments_mcp_registration_and_read_only_invocation(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    for key in ("SITEPILOT_WP_USERNAME", "SITEPILOT_CREDENTIAL_REF", "SITEPILOT_CA_CERT"):
        monkeypatch.delenv(key, raising=False)

    class FakeListCommentsTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self, page: int, per_page: int, status: str) -> dict[str, object]:
            assert (page, per_page, status) == (1, 10, "approved")
            return comments_payload([], page=page, per_page=per_page, status=status)

    monkeypatch.setattr(server_module, "ListCommentsTool", FakeListCommentsTool)
    server = server_module.create_server()
    registered = await server.list_tools()
    tool = next(item for item in registered if item.name == "list_comments")
    result = await server.call_tool("list_comments", {})
    schema = str(tool.input_schema)
    assert all(field in schema for field in ("page", "per_page", "status"))
    assert "url" not in schema
    assert result.structured_content["comments"] == []
    assert result.structured_content["pagination"]["status"] == "approved"
