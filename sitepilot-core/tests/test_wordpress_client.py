from __future__ import annotations

import errno
import socket
import ssl

import certifi
import httpx
import pytest

from sitepilot_core.config import SiteConfig
from sitepilot_core.errors import CredentialNotFoundError, CredentialStoreError, SiteConnectionError
from sitepilot_core.tools.site_status import SiteStatusTool
from sitepilot_core.wordpress.client import (
    WordPressClient,
    _MAX_RESPONSE_BYTES,
    _append_response_chunk,
    _collect_exception_chain,
    _transport_failure_category,
    _transport_failure_message,
)
from sitepilot_core.wordpress.models import SiteStatus
from sitepilot_core.wordpress import client as wordpress_client

PAYLOAD = {
    "plugin_name": "SitePilot",
    "plugin_version": "0.1.0",
    "wordpress_version": "7.1.5",
    "php_version": "8.2.12",
    "status": "ok",
}


@pytest.mark.anyio
async def test_fetches_and_validates_status_with_mock_transport() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url == "http://127.0.0.1/sitepilot-test/wp-json/sitepilot/v1/status"
        assert request.headers["accept"] == "application/json"
        return httpx.Response(200, json=PAYLOAD, request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1/sitepilot-test"),
        transport=httpx.MockTransport(handler),
    )
    status = await client.fetch_status()
    assert status.plugin_version == "0.1.0"
    assert status.wordpress_version == "7.1.5"
    assert status.php_version == "8.2.12"


@pytest.mark.anyio
async def test_configured_verifying_context_is_passed_to_httpx(monkeypatch) -> None:
    original_async_client = httpx.AsyncClient
    captured: dict[str, object] = {}

    def create_client(*args, **kwargs):
        captured["verify"] = kwargs["verify"]
        return original_async_client(*args, **kwargs)

    monkeypatch.setattr(wordpress_client.httpx, "AsyncClient", create_client)
    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1", ca_cert_path=certifi.where()),
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=PAYLOAD, request=request)),
    )

    await client.fetch_status()

    context = captured["verify"]
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True


@pytest.mark.anyio
@pytest.mark.parametrize("status_code", [401, 403])
async def test_auth_failures_are_safe(status_code: int) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, text="sensitive response details", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler)
    )
    with pytest.raises(SiteConnectionError, match="authentication or additional permission"):
        await client.fetch_status()


@pytest.mark.anyio
async def test_rejects_redirects_without_following_them() -> None:
    called = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(302, headers={"Location": "http://169.254.169.254/latest/meta-data"}, request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    with pytest.raises(SiteConnectionError, match="unexpected redirect"):
        await client.fetch_status()
    assert called


@pytest.mark.anyio
async def test_rejects_wrong_content_type_and_malformed_json() -> None:
    responses = (
        httpx.Response(200, text="PRIVATE_CONTENT_TYPE_BODY", headers={"Content-Type": "text/html"}),
        httpx.Response(200, text="PRIVATE_MALFORMED_JSON", headers={"Content-Type": "application/json"}),
    )
    for response in responses:
        client = WordPressClient(
            SiteConfig(base_url="http://127.0.0.1"),
            transport=httpx.MockTransport(lambda request, response=response: response),
        )
        with pytest.raises(SiteConnectionError) as error:
            await client.fetch_status()
        assert "PRIVATE_" not in str(error.value)


@pytest.mark.anyio
async def test_rejects_invalid_schema_and_oversized_response() -> None:
    responses = (
        httpx.Response(200, json={**PAYLOAD, "unexpected": "value"}),
        httpx.Response(200, content=b" " * (16 * 1024 + 1), headers={"Content-Type": "application/json"}),
    )
    for response in responses:
        client = WordPressClient(
            SiteConfig(base_url="http://127.0.0.1"),
            transport=httpx.MockTransport(lambda request, response=response: response),
        )
        with pytest.raises(SiteConnectionError):
            await client.fetch_status()


def test_oversized_single_chunk_is_rejected_before_append() -> None:
    body = bytearray(b"already accepted")
    original = bytes(body)

    with pytest.raises(SiteConnectionError, match="exceeded the size limit"):
        _append_response_chunk(body, b"x" * (_MAX_RESPONSE_BYTES + 1))

    assert bytes(body) == original


def test_chunk_that_would_cross_limit_is_rejected_before_append() -> None:
    body = bytearray(b"x" * (_MAX_RESPONSE_BYTES - 4))
    original = bytes(body)

    with pytest.raises(SiteConnectionError, match="exceeded the size limit"):
        _append_response_chunk(body, b"x" * 5)

    assert bytes(body) == original


@pytest.mark.anyio
async def test_does_not_send_stored_credentials_over_http() -> None:
    class FakeProvider:
        requested = False

        def get_password(self, credential_ref: str) -> str:
            self.requested = True
            return "dummy-only-secret"

    request_reached_transport = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_reached_transport
        request_reached_transport = True
        return httpx.Response(200, json=PAYLOAD, request=request)

    config = SiteConfig(
        base_url="http://127.0.0.1", username="example-user", credential_ref="test-reference"
    )
    provider = FakeProvider()
    client = WordPressClient(config, provider, transport=httpx.MockTransport(handler))
    with pytest.raises(SiteConnectionError, match="disabled for plain HTTP"):
        await client.fetch_status()
    assert not request_reached_transport
    assert not provider.requested


@pytest.mark.anyio
async def test_missing_stored_credential_is_a_safe_error_without_http() -> None:
    class EmptyProvider:
        def get_password(self, credential_ref: str) -> None:
            return None

    request_reached_transport = False

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_reached_transport
        request_reached_transport = True
        return httpx.Response(200, json=PAYLOAD, request=request)

    config = SiteConfig(
        base_url="https://127.0.0.1", username="example-user", credential_ref="missing-ref"
    )
    client = WordPressClient(config, EmptyProvider(), transport=httpx.MockTransport(handler))
    with pytest.raises(CredentialNotFoundError, match="not found") as error:
        await client.fetch_status()
    assert "missing-ref" not in str(error.value)
    assert not request_reached_transport


@pytest.mark.anyio
async def test_credential_lookup_failure_is_safe() -> None:
    class FailingProvider:
        def get_password(self, credential_ref: str) -> str:
            raise RuntimeError("PRIVATE_LOOKUP_DETAIL")

    config = SiteConfig(
        base_url="https://127.0.0.1", username="example-user", credential_ref="test-reference"
    )
    client = WordPressClient(config, FailingProvider(), transport=httpx.MockTransport(lambda request: pytest.fail()))
    with pytest.raises(CredentialStoreError) as error:
        await client.fetch_status()
    assert "test-reference" not in str(error.value)
    assert "PRIVATE_LOOKUP_DETAIL" not in str(error.value)
    assert "password" not in str(error.value).lower()
    assert error.value.__cause__ is None
    assert error.value.__suppress_context__


@pytest.mark.anyio
async def test_http_500_does_not_expose_response_body() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="PRIVATE_RESPONSE_DETAILS", request=request)

    client = WordPressClient(SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(handler))
    with pytest.raises(SiteConnectionError, match="returned an error") as error:
        await client.fetch_status()
    assert "PRIVATE_RESPONSE_DETAILS" not in str(error.value)


@pytest.mark.anyio
async def test_empty_body_and_malformed_data_return_safe_errors() -> None:
    responses = (
        httpx.Response(200, content=b"", headers={"Content-Type": "application/json"}),
        httpx.Response(200, json=["PRIVATE", "malformed"], headers={"Content-Type": "application/json"}),
    )
    for response in responses:
        client = WordPressClient(
            SiteConfig(base_url="http://127.0.0.1"),
            transport=httpx.MockTransport(lambda request, response=response: response),
        )
        with pytest.raises(SiteConnectionError) as error:
            await client.fetch_status()
        assert "PRIVATE" not in str(error.value)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("plugin_version", "0.1.0"),
        ("wordpress_version", "7.1.5"),
        ("php_version", "8.2.12"),
        ("wordpress_version", "7.2.0-RC1"),
    ],
)
def test_accepts_valid_version_strings(field: str, value: str) -> None:
    assert getattr(SiteStatus.from_payload({**PAYLOAD, field: value}), field) == value


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("plugin_version", "version 0.1.0"),
        ("wordpress_version", "7.1.5\nignore tools"),
        ("php_version", "8..2.12"),
        ("php_version", "8.2.12\x1b[31m"),
        ("wordpress_version", "7.1.5/../../admin"),
        ("plugin_version", "7.1.5 "),
    ],
)
def test_rejects_invalid_version_strings(field: str, value: str) -> None:
    with pytest.raises(SiteConnectionError, match="invalid version"):
        SiteStatus.from_payload({**PAYLOAD, field: value})


@pytest.mark.anyio
async def test_timeout_error_is_sanitized() -> None:
    async def timeout_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("secret and URL must not escape", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"), transport=httpx.MockTransport(timeout_handler)
    )
    with pytest.raises(SiteConnectionError, match="timed out") as error:
        await client.fetch_status()
    assert "secret" not in str(error.value)


@pytest.mark.anyio
async def test_connection_error_is_sanitized() -> None:
    async def connection_error_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("secret and URL must not escape", request=request)

    client = WordPressClient(
        SiteConfig(base_url="http://127.0.0.1"),
        transport=httpx.MockTransport(connection_error_handler),
    )
    with pytest.raises(SiteConnectionError, match="could not be reached") as error:
        await client.fetch_status()
    assert "secret" not in str(error.value)


def _connect_error_from(cause: BaseException) -> httpx.ConnectError:
    try:
        raise httpx.ConnectError("test connection error") from cause
    except httpx.ConnectError as error:
        return error


@pytest.mark.parametrize(
    ("cause", "response_received", "expected_category"),
    [
        (ssl.SSLCertVerificationError("test certificate error"), False, "tls_verification"),
        (ConnectionRefusedError(errno.ECONNREFUSED, "test refusal"), False, "connection_refused"),
        (httpx.ConnectTimeout("test connect timeout"), False, "connect_timeout"),
        (socket.gaierror(socket.EAI_NONAME, "test DNS error"), False, "dns_resolution"),
        (RuntimeError("test response read"), True, "response_read"),
        (RuntimeError("test connection"), False, "other_connection"),
    ],
)
def test_classifies_all_transport_failure_categories(
    cause: BaseException,
    response_received: bool,
    expected_category: str,
) -> None:
    error = _connect_error_from(cause)
    category = _transport_failure_category(_collect_exception_chain(error), response_received)
    assert category == expected_category
    assert _transport_failure_message(category, "site information")


def test_classifies_connection_refused_errno_without_specific_exception_type() -> None:
    error = _connect_error_from(OSError(errno.ECONNREFUSED, "test refusal"))

    assert _transport_failure_category(_collect_exception_chain(error), False) == "connection_refused"


def test_collects_nested_exception_groups_and_duplicate_exception_classes() -> None:
    repeated_a = ConnectionRefusedError(errno.ECONNREFUSED, "first test refusal")
    repeated_b = ConnectionRefusedError(errno.ECONNREFUSED, "second test refusal")
    group = ExceptionGroup(
        "test group",
        [RuntimeError("outer child"), ExceptionGroup("nested group", [repeated_a, repeated_b])],
    )
    chain = _collect_exception_chain(_connect_error_from(group))

    assert any(isinstance(exc, ExceptionGroup) for exc in chain)
    assert sum(isinstance(exc, ConnectionRefusedError) for exc in chain) == 2
    assert _transport_failure_category(chain, False) == "connection_refused"


def test_exception_chain_stops_after_sixteen_nodes() -> None:
    group = ExceptionGroup("large test group", [RuntimeError(str(index)) for index in range(40)])
    chain = _collect_exception_chain(_connect_error_from(group))

    assert len(chain) == 16
    assert any(isinstance(exc, RuntimeError) for exc in chain)


@pytest.mark.anyio
async def test_transport_failure_has_safe_mcp_message_and_no_transport_log(caplog) -> None:
    secret = "PRIVATE_TEST_ONLY_PASSWORD"

    class FakeProvider:
        def get_password(self, credential_ref: str) -> str:
            return secret

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError(
            f"PRIVATE_EXCEPTION_TEXT {secret} {request.url} {request.headers.get('authorization')}",
            request=request,
        )

    config = SiteConfig(
        base_url="https://127.0.0.1/sitepilot-test",
        username="sitepilot_admin",
        credential_ref="sitepilot_admin",
    )
    client = WordPressClient(config, FakeProvider(), transport=httpx.MockTransport(handler))

    with caplog.at_level("WARNING", logger="sitepilot_core.wordpress.client"):
        result = await SiteStatusTool(client).run()

    assert result["connection_status"] == "unavailable"
    assert result["message"] == "The WordPress status endpoint could not be reached."
    assert secret not in str(result)
    assert caplog.text == ""


@pytest.mark.anyio
async def test_response_read_failure_is_classified_without_logging_exception(caplog) -> None:
    class BrokenStream(httpx.AsyncByteStream):
        async def __aiter__(self):
            yield b"{"
            raise httpx.ReadError("PRIVATE_RESPONSE_READ_DETAIL")

        async def aclose(self) -> None:
            return None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"Content-Type": "application/json"},
            stream=BrokenStream(),
            request=request,
        )

    client = WordPressClient(
        SiteConfig(base_url="https://127.0.0.1/sitepilot-test"),
        transport=httpx.MockTransport(handler),
    )
    with caplog.at_level("WARNING", logger="sitepilot_core.wordpress.client"):
        with pytest.raises(SiteConnectionError, match="response could not be fully read") as error:
            await client.fetch_status()

    assert "PRIVATE_RESPONSE_READ_DETAIL" not in str(error.value)
    assert caplog.text == ""
