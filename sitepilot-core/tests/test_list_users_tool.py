from __future__ import annotations

import httpx
import pytest

import sitepilot_core.server as server_module
from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import SiteConnectionError
from sitepilot_core.tools.list_users import ListUsersTool
from sitepilot_core.wordpress.client import WordPressClient
from sitepilot_core.wordpress.models import UserList


def user_entry(user_id: int, **overrides: object) -> dict[str, object]:
    return {
        "id": user_id,
        "username": f"user{user_id}",
        "display_name": f"User {user_id}",
        "roles": ["subscriber"],
        "registered": "2026-11-23T09:30:00+00:00",
        "description": "A sample profile.",
        **overrides,
    }


def users_payload(
    users: list[dict[str, object]] | None = None,
    *,
    page: int = 1,
    per_page: int = 10,
    total_items: int | None = None,
) -> dict[str, object]:
    entries = users or []
    count = len(entries) if total_items is None else total_items
    return {
        "connection_status": "connected",
        "users": entries,
        "pagination": {
            "page": page,
            "per_page": per_page,
            "total_items": count,
            "total_pages": (count + per_page - 1) // per_page,
        },
        "message": "Users retrieved successfully.",
    }


@pytest.mark.anyio
async def test_lists_multiple_users_and_multiple_roles() -> None:
    payload = users_payload(
        [
            user_entry(14, roles=["administrator", "editor"]),
            user_entry(15, roles=["author"]),
        ],
        page=2,
        per_page=2,
        total_items=3,
    )

    class FakeClient:
        async def fetch_users(self, page: int, per_page: int) -> UserList:
            assert (page, per_page) == (2, 2)
            return UserList.from_payload(payload)

    result = await ListUsersTool(FakeClient()).run(2, 2)  # type: ignore[arg-type]
    assert result["connection_status"] == "connected"
    assert len(result["users"]) == 2
    assert result["users"][0]["roles"] == ["administrator", "editor"]
    assert result["pagination"] == {
        "page": 2,
        "per_page": 2,
        "total_items": 3,
        "total_pages": 2,
    }


def test_model_accepts_empty_and_missing_optional_metadata() -> None:
    empty = UserList.from_payload(users_payload())
    payload = users_payload([{"id": 20, "roles": []}], total_items=1)
    user = UserList.from_payload(payload).users[0]
    assert empty.users == ()
    assert user.username is user.display_name is user.registered is user.description is None


def test_model_suppresses_email_addresses_from_user_text() -> None:
    payload = users_payload(
        [
            user_entry(
                22,
                username="person@example.test",
                display_name="Contact person@example.test",
                description="About person@example.test and other details.",
            )
        ],
        total_items=1,
    )
    result = UserList.from_payload(payload).users[0]
    assert result.username is None
    assert result.display_name is None
    assert result.description is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda payload: payload.update({"secret": "PRIVATE"}),
        lambda payload: payload["users"][0].update({"email": "person@example.test"}),
        lambda payload: payload["users"][0].update({"password": "PRIVATE_HASH"}),
        lambda payload: payload["users"][0].update({"application_passwords": ["PRIVATE"]}),
        lambda payload: payload["users"][0].update({"meta": {"private": "PRIVATE"}}),
        lambda payload: payload["users"][0].update({"id": True}),
        lambda payload: payload["users"][0].update({"roles": ["administrator", "bad role"]}),
        lambda payload: payload["users"][0].update({"registered": "not-a-date"}),
        lambda payload: payload["pagination"].update({"total_pages": 77}),
        lambda payload: payload.update({"users": "not-an-array"}),
        lambda payload: payload.update({"connection_status": "unavailable"}),
    ],
)
def test_rejects_malformed_or_sensitive_user_responses(mutate) -> None:
    payload = users_payload([user_entry(5)], total_items=1)
    mutate(payload)
    with pytest.raises(SiteConnectionError):
        UserList.from_payload(payload)


@pytest.mark.anyio
async def test_users_client_uses_fixed_get_route_and_pagination() -> None:
    payload = users_payload([user_entry(5)], page=3, per_page=7, total_items=15)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/sitepilot-test/wp-json/sitepilot/v1/users"
        assert dict(request.url.params) == {"page": "3", "per_page": "7"}
        return httpx.Response(200, json=payload, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"), transport=httpx.MockTransport(handler)
    )
    result = await client.fetch_users(3, 7)
    assert result.pagination.page == 3


@pytest.mark.anyio
async def test_user_client_reuses_configured_credential_provider() -> None:
    class FakeProvider:
        requested_reference: str | None = None

        def get_password(self, credential_ref: str) -> str:
            self.requested_reference = credential_ref
            return "test-only-credential"

    provider = FakeProvider()

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.headers.get("authorization") is not None
        assert "test-only-credential" not in str(request.headers)
        return httpx.Response(200, json=users_payload(), request=request)

    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1/sitepilot-test", username="test-user", credential_ref="test-ref"),
        provider,
        transport=httpx.MockTransport(handler),
    )
    await client.fetch_users()
    assert provider.requested_reference == "test-ref"


@pytest.mark.anyio
async def test_default_and_maximum_user_page_sizes() -> None:
    requested: list[dict[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requested.append(dict(request.url.params))
        size = int(request.url.params["per_page"])
        return httpx.Response(200, json=users_payload([], per_page=size), request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    await client.fetch_users()
    await client.fetch_users(per_page=50)
    assert requested == [
        {"page": "1", "per_page": "10"},
        {"page": "1", "per_page": "50"},
    ]


@pytest.mark.anyio
async def test_invalid_user_pagination_is_rejected_before_request() -> None:
    requests = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal requests
        requests += 1
        return httpx.Response(200, json=users_payload(), request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    for page, per_page in ((0, 10), (-1, 10), (10_001, 10), (True, 10), (1, 0), (1, 51), (1, True)):
        with pytest.raises(SiteConnectionError, match="parameters are invalid"):
            await client.fetch_users(page, per_page)  # type: ignore[arg-type]
    assert requests == 0

    class UnusedClient:
        async def fetch_users(self, *args) -> UserList:
            pytest.fail("invalid pagination must not reach the HTTP client")

    result = await ListUsersTool(UnusedClient()).run(per_page=51)  # type: ignore[arg-type]
    assert result["connection_status"] == "invalid_request"
    assert result["users"] is None


@pytest.mark.anyio
async def test_authentication_permission_http_and_transport_errors_are_safe() -> None:
    for status_code in (401, 403, 500):
        def response_handler(request: httpx.Request, status_code: int = status_code) -> httpx.Response:
            return httpx.Response(status_code, text="PRIVATE_RESPONSE", request=request)

        result = await ListUsersTool(
            WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(response_handler))
        ).run()
        expected = "authentication_required" if status_code in (401, 403) else "unavailable"
        assert result["connection_status"] == expected
        assert result["users"] is None and result["pagination"] is None
        assert "PRIVATE_RESPONSE" not in str(result)

    async def transport_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("PRIVATE_EXCEPTION", request=request)

    result = await ListUsersTool(
        WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(transport_error))
    ).run()
    assert result["connection_status"] == "unavailable"
    assert "PRIVATE_EXCEPTION" not in str(result)


@pytest.mark.anyio
async def test_list_users_mcp_tool_is_registered_without_url_input(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SITEPILOT_WORDPRESS_URL", "http://127.0.0.1")
    monkeypatch.delenv("SITEPILOT_WP_USERNAME", raising=False)
    monkeypatch.delenv("SITEPILOT_CREDENTIAL_REF", raising=False)
    monkeypatch.delenv("SITEPILOT_CA_CERT", raising=False)

    class FakeListUsersTool:
        def __init__(self, client: object) -> None:
            pass

        async def run(self, page: int, per_page: int) -> dict[str, object]:
            return users_payload([], page=page, per_page=per_page)

    monkeypatch.setattr(server_module, "ListUsersTool", FakeListUsersTool)
    server = server_module.create_server()
    registered = await server.list_tools()
    tool = next(item for item in registered if item.name == "list_users")
    result = await server.call_tool("list_users", {})
    schema = str(tool.input_schema)
    assert "page" in schema and "per_page" in schema
    assert "url" not in schema
    assert result.structured_content["pagination"] == {
        "page": 1,
        "per_page": 10,
        "total_items": 0,
        "total_pages": 0,
    }
