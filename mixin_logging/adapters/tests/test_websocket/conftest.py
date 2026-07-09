"""WebSocket adapter-specific pytest fixtures."""

from __future__ import annotations

from typing import Any, Iterator

import pytest

from mixin_logging import clear_correlation_id
from mixin_logging.adapters.constants import websocket as const
from mixin_logging.common.constants import tests as test_const


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def basic_websocket_scope() -> dict[str, Any]:
    """ASGI WebSocket scope without correlation ID header."""
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [],
    }


@pytest.fixture
def websocket_scope_with_correlation() -> dict[str, Any]:
    """ASGI WebSocket scope with X-Correlation-ID header set."""
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [
            (
                const.CORRELATION_ID_HEADER.encode(),
                test_const.CORRELATION_ID_TRACE.encode(),
            ),
        ],
    }


@pytest.fixture
def websocket_scope_with_case_insensitive_header() -> dict[str, Any]:
    """ASGI WebSocket scope with mixed-case correlation ID header."""
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [
            (b"X-CORRELATION-ID", test_const.CORRELATION_ID_CUSTOM.encode()),
        ],
    }


@pytest.fixture
def websocket_scope_with_carriage_return_header() -> dict[str, Any]:
    """ASGI WebSocket scope with CR-injected correlation ID header."""
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [
            (const.CORRELATION_ID_HEADER.encode(), b"test-id\r-bad"),
        ],
    }


@pytest.fixture
def websocket_scope_with_newline_header() -> dict[str, Any]:
    """ASGI WebSocket scope with LF-injected correlation ID header."""
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [
            (const.CORRELATION_ID_HEADER.encode(), b"test-id\n-bad"),
        ],
    }


@pytest.fixture
def websocket_scope_with_null_byte_header() -> dict[str, Any]:
    """ASGI WebSocket scope with null-byte-injected correlation ID header."""
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [
            (const.CORRELATION_ID_HEADER.encode(), b"test-id\x00-bad"),
        ],
    }


@pytest.fixture
def websocket_scope_with_oversized_header() -> dict[str, Any]:
    """ASGI WebSocket scope with correlation ID exceeding MAX_LENGTH."""
    oversized_id = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
    return {
        "type": "websocket",
        "path": "/ws",
        "headers": [
            (const.CORRELATION_ID_HEADER.encode(), oversized_id.encode()),
        ],
    }


@pytest.fixture
def http_scope() -> dict[str, Any]:
    """ASGI HTTP scope for passthrough testing (non-websocket)."""
    return {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
    }


@pytest.fixture
def mock_receive() -> Any:
    """Mock ASGI receive callable for WebSocket."""

    async def receive() -> dict[str, Any]:
        return {"type": "websocket.connect"}

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
