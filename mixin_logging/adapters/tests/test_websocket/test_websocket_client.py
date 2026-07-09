"""Tests for CorrelationIdMiddleware WebSocket adapter."""

from __future__ import annotations

from typing import Any

import pytest

from mixin_logging import clear_correlation_id, get_correlation_id
from mixin_logging.adapters.websocket import websocket_client
from mixin_logging.common.constants import tests as test_const


@pytest.mark.asyncio
class TestCorrelationIdMiddlewareCall:
    """Tests for CorrelationIdMiddleware.__call__() async method."""

    async def test_middleware_websocket_scope_sets_correlation(
        self,
        basic_websocket_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware sets correlation context for WebSocket scope."""
        clear_correlation_id()
        set_value: str | None = None

        async def recording_app(
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            nonlocal set_value
            set_value = get_correlation_id()

        middleware = websocket_client.CorrelationIdMiddleware(recording_app)
        await middleware(basic_websocket_scope, mock_receive, mock_send)
        assert set_value is not None
        assert len(set_value) == 12
        assert all(char in "0123456789abcdef" for char in set_value)

    async def test_middleware_websocket_with_header_extracts_correlation(
        self,
        websocket_scope_with_correlation,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware extracts correlation ID from WebSocket handshake header."""
        clear_correlation_id()
        set_value: str | None = None

        async def recording_app(
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            nonlocal set_value
            set_value = get_correlation_id()

        middleware = websocket_client.CorrelationIdMiddleware(recording_app)
        await middleware(websocket_scope_with_correlation, mock_receive, mock_send)
        assert set_value == test_const.CORRELATION_ID_TRACE

    async def test_middleware_http_scope_passes_through(
        self,
        http_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware passes through non-WebSocket scope untouched."""
        clear_correlation_id()
        set_value: str | None = None

        async def recording_app(
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            nonlocal set_value
            set_value = get_correlation_id()

        middleware = websocket_client.CorrelationIdMiddleware(recording_app)
        await middleware(http_scope, mock_receive, mock_send)
        assert set_value is None

    async def test_middleware_clears_context_after_exit(
        self,
        basic_websocket_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware clears context on exit via finally block."""
        clear_correlation_id()
        middleware = websocket_client.CorrelationIdMiddleware(mock_app)
        await middleware(basic_websocket_scope, mock_receive, mock_send)
        assert get_correlation_id() is None

    async def test_middleware_clears_context_even_when_app_raises(
        self,
        basic_websocket_scope,
        mock_receive,
        mock_send,
    ) -> None:
        """CorrelationIdMiddleware clears context even if the wrapped app raises."""
        clear_correlation_id()

        async def failing_app(
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            raise RuntimeError("test error")

        middleware = websocket_client.CorrelationIdMiddleware(failing_app)
        with pytest.raises(RuntimeError, match="test error"):
            await middleware(basic_websocket_scope, mock_receive, mock_send)
        assert get_correlation_id() is None

    async def test_middleware_delegates_to_wrapped_app(
        self,
        basic_websocket_scope,
        mock_receive,
        mock_send,
    ) -> None:
        """CorrelationIdMiddleware awaits the wrapped app with original scope/receive/send."""
        called_with: dict[str, Any] = {}

        async def recording_app(
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            called_with["scope"] = scope
            called_with["receive"] = receive
            called_with["send"] = send

        middleware = websocket_client.CorrelationIdMiddleware(recording_app)
        await middleware(basic_websocket_scope, mock_receive, mock_send)
        assert called_with["scope"] is basic_websocket_scope
        assert called_with["receive"] is mock_receive
        assert called_with["send"] is mock_send

    async def test_middleware_rejects_unsafe_header_and_generates_id(
        self,
        websocket_scope_with_carriage_return_header,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware rejects unsafe header and generates new ID."""
        clear_correlation_id()
        set_value: str | None = None

        async def recording_app(
            scope: dict[str, Any],
            receive: Any,
            send: Any,
        ) -> None:
            nonlocal set_value
            set_value = get_correlation_id()

        middleware = websocket_client.CorrelationIdMiddleware(recording_app)
        await middleware(
            websocket_scope_with_carriage_return_header, mock_receive, mock_send
        )
        assert set_value is not None
        assert len(set_value) == 12
        assert all(char in "0123456789abcdef" for char in set_value)
