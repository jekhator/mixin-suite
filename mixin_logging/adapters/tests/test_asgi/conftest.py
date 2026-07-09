"""ASGI-specific pytest fixtures for adapter tests."""

from __future__ import annotations

import logging
from typing import Any, Iterator

import pytest

from mixin_logging import LoggingMixin, clear_correlation_id
from mixin_logging.adapters.constants import asgi as const
from mixin_logging.common.constants import tests as test_const
from mixin_logging.common.utils.record_collector import _RecordCollector


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def basic_http_scope() -> dict[str, Any]:
    """ASGI HTTP scope without correlation ID header."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [],
    }


@pytest.fixture
def http_scope_with_correlation() -> dict[str, Any]:
    """ASGI HTTP scope with X-Correlation-ID header set."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (const.CORRELATION_ID_HEADER, test_const.CORRELATION_ID_TRACE.encode()),
        ],
    }


@pytest.fixture
def http_scope_with_case_insensitive_header() -> dict[str, Any]:
    """ASGI HTTP scope with mixed-case correlation ID header."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (b"X-CORRELATION-ID", test_const.CORRELATION_ID_CUSTOM.encode()),
        ],
    }


@pytest.fixture
def websocket_scope() -> dict[str, Any]:
    """ASGI WebSocket scope (non-HTTP) for passthrough testing."""
    return {
        const.TYPE_KEY: "websocket",
        "path": "/ws",
        const.HEADERS_KEY: [],
    }


@pytest.fixture
def http_scope_with_carriage_return_header() -> dict[str, Any]:
    """ASGI HTTP scope with CR-injected correlation ID header."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (const.CORRELATION_ID_HEADER, b"test-id\r-bad"),
        ],
    }


@pytest.fixture
def http_scope_with_newline_header() -> dict[str, Any]:
    """ASGI HTTP scope with LF-injected correlation ID header."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (const.CORRELATION_ID_HEADER, b"test-id\n-bad"),
        ],
    }


@pytest.fixture
def http_scope_with_null_byte_header() -> dict[str, Any]:
    """ASGI HTTP scope with null-byte-injected correlation ID header."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (const.CORRELATION_ID_HEADER, b"test-id\x00-bad"),
        ],
    }


@pytest.fixture
def http_scope_with_oversized_header() -> dict[str, Any]:
    """ASGI HTTP scope with correlation ID exceeding MAX_LENGTH."""
    oversized_id = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (const.CORRELATION_ID_HEADER, oversized_id.encode()),
        ],
    }


@pytest.fixture
def http_scope_with_invalid_utf8_header() -> dict[str, Any]:
    """ASGI HTTP scope with invalid UTF-8 bytes in correlation ID header."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (const.CORRELATION_ID_HEADER, b"\xff\xfe"),
        ],
    }


@pytest.fixture
def http_scope_with_string_header_name() -> dict[str, Any]:
    """ASGI HTTP scope with string (not bytes) header name (malformed)."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            ("x-correlation-id", test_const.CORRELATION_ID_TRACE.encode()),
        ],
    }


@pytest.fixture
def http_scope_with_string_header_value() -> dict[str, Any]:
    """ASGI HTTP scope with string (not bytes) header value (malformed)."""
    return {
        const.TYPE_KEY: "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        const.HEADERS_KEY: [
            (const.CORRELATION_ID_HEADER, test_const.CORRELATION_ID_TRACE),
        ],
    }


@pytest.fixture
def mock_receive() -> Any:
    """Mock ASGI receive callable returning an empty http.request message."""

    async def receive() -> dict[str, Any]:
        return {"type": test_const.HTTP_EVENT_REQUEST, "body": b""}

    return receive


@pytest.fixture
def mock_send() -> Any:
    """Mock ASGI send callable that discards messages."""

    async def send(message: dict[str, Any]) -> None:
        return None

    return send


@pytest.fixture
def mock_app() -> Any:
    """Mock ASGI app that does nothing."""

    async def app(
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        return None

    return app


@pytest.fixture
def http_app_that_sends_response() -> Any:
    """Mock ASGI app that emits an http.response.start message."""

    async def app(
        scope: dict[str, Any],
        receive: Any,
        send: Any,
    ) -> None:
        await send(
            {
                const.TYPE_KEY: test_const.HTTP_EVENT_RESPONSE_START,
                const.RESPONSE_STATUS_KEY: 200,
                const.HEADERS_KEY: [(b"content-type", b"text/plain")],
            }
        )

    return app


@pytest.fixture
def log_capture(
    service_class: type[LoggingMixin],
) -> tuple[LoggingMixin, _RecordCollector]:
    """Service instance + collector handler attached at DEBUG level."""
    svc = service_class()
    collector = _RecordCollector()
    svc._logger.addHandler(collector)
    svc._logger.setLevel(logging.DEBUG)
    return svc, collector


@pytest.fixture
def service_class() -> type[LoggingMixin]:
    """Bare LoggingMixin subclass with slots: base for service-class tests."""

    class Svc(LoggingMixin):
        """LoggingMixin subclass with slots for service-class fixture tests."""

        __slots__ = ()

    return Svc
