"""Tests for ASGIApp + CorrelationIdMiddleware."""

from __future__ import annotations

from typing import Any

import pytest

from mixin_logging import clear_correlation_id, get_correlation_id, set_correlation_id
from mixin_logging.adapters.asgi import asgi_client, asgi_objects as asgi_objs
from mixin_logging.adapters.constants import asgi as const
from mixin_logging.common.constants import tests as test_const


@pytest.mark.asyncio
class TestASGIAppCall:
    """Tests for ASGIApp.__call__() async method."""

    async def test_asgi_app_sets_correlation_context(
        self,
        basic_http_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """ASGIApp.__call__() sets correlation ID into context before calling wrapped app."""
        clear_correlation_id()
        correlation = asgi_objs.AsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TRACE,
            from_header=True,
        )
        app_wrapper = asgi_client.ASGIApp(mock_app, correlation)
        await app_wrapper(basic_http_scope, mock_receive, mock_send)
        assert get_correlation_id() == test_const.CORRELATION_ID_TRACE

    async def test_asgi_app_delegates_to_wrapped_app(
        self,
        basic_http_scope,
        mock_receive,
        mock_send,
    ) -> None:
        """ASGIApp.__call__() awaits the wrapped app with original scope/receive/send."""
        called_with: dict[str, Any] = {}

        async def recording_app(
            scope,
            receive,
            send,
        ) -> None:
            called_with["scope"] = scope
            called_with["receive"] = receive
            called_with["send"] = send

        correlation = asgi_objs.AsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TRACE,
            from_header=True,
        )
        app_wrapper = asgi_client.ASGIApp(recording_app, correlation)
        await app_wrapper(basic_http_scope, mock_receive, mock_send)
        assert called_with["scope"] is basic_http_scope
        assert called_with["receive"] is mock_receive
        assert called_with["send"] is mock_send

    async def test_asgi_app_sets_and_does_not_clear_context(
        self,
        basic_http_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """ASGIApp.__call__() sets context; clearing is middleware's responsibility."""
        clear_correlation_id()
        correlation = asgi_objs.AsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TRACE,
            from_header=True,
        )
        app_wrapper = asgi_client.ASGIApp(mock_app, correlation)
        await app_wrapper(basic_http_scope, mock_receive, mock_send)
        assert get_correlation_id() == test_const.CORRELATION_ID_TRACE


@pytest.mark.asyncio
class TestCorrelationIdMiddlewareCall:
    """Tests for CorrelationIdMiddleware.__call__() async method."""

    async def test_middleware_non_http_scope_passes_through(
        self,
        websocket_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware passes non-HTTP scope to app untouched."""
        clear_correlation_id()
        middleware = asgi_client.CorrelationIdMiddleware(mock_app)
        await middleware(websocket_scope, mock_receive, mock_send)
        assert get_correlation_id() is None

    async def test_middleware_http_scope_sets_correlation(
        self,
        basic_http_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware resolves correlation and sets context for HTTP scope."""
        clear_correlation_id()
        set_value: str | None = None

        async def recording_app(
            scope,
            receive,
            send,
        ) -> None:
            nonlocal set_value
            set_value = get_correlation_id()

        middleware = asgi_client.CorrelationIdMiddleware(recording_app)
        await middleware(basic_http_scope, mock_receive, mock_send)
        assert set_value is not None
        assert len(set_value) == 12
        assert all(char in "0123456789abcdef" for char in set_value)

    async def test_middleware_injects_header_on_response_start(
        self,
        basic_http_scope,
        mock_receive,
        http_app_that_sends_response,
    ) -> None:
        """CorrelationIdMiddleware injects correlation ID into http.response.start headers."""
        messages: list[Any] = []

        async def recording_send(message: Any) -> None:
            messages.append(message)

        middleware = asgi_client.CorrelationIdMiddleware(http_app_that_sends_response)
        await middleware(basic_http_scope, mock_receive, recording_send)
        assert len(messages) == 1
        response_msg = messages[0]
        assert response_msg[const.TYPE_KEY] == test_const.HTTP_EVENT_RESPONSE_START
        headers = response_msg[const.HEADERS_KEY]
        correlation_header_found = False
        for header_name, header_value in headers:
            if header_name == const.CORRELATION_ID_HEADER:
                correlation_header_found = True
                assert isinstance(header_value, bytes)
                break
        assert correlation_header_found

    async def test_middleware_clears_context_after_exit(
        self,
        basic_http_scope,
        mock_receive,
        mock_send,
        mock_app,
    ) -> None:
        """CorrelationIdMiddleware clears context on exit via finally block."""
        clear_correlation_id()
        set_correlation_id(test_const.CORRELATION_ID_SHOULD_BE_CLEARED)
        middleware = asgi_client.CorrelationIdMiddleware(mock_app)
        await middleware(basic_http_scope, mock_receive, mock_send)
        assert get_correlation_id() is None

    async def test_middleware_preserves_existing_headers(
        self,
        basic_http_scope,
        mock_receive,
        http_app_that_sends_response,
    ) -> None:
        """CorrelationIdMiddleware appends correlation header without removing others."""
        messages: list[Any] = []

        async def recording_send(message: Any) -> None:
            messages.append(message)

        middleware = asgi_client.CorrelationIdMiddleware(http_app_that_sends_response)
        await middleware(basic_http_scope, mock_receive, recording_send)
        assert len(messages) == 1
        response_msg = messages[0]
        headers = response_msg[const.HEADERS_KEY]
        assert len(headers) == 2
        header_names = [h[0] for h in headers]
        assert b"content-type" in header_names
        assert const.CORRELATION_ID_HEADER in header_names

    async def test_middleware_passes_through_non_response_start_messages(
        self,
        basic_http_scope,
        mock_receive,
    ) -> None:
        """CorrelationIdMiddleware does not modify non-response-start messages."""
        messages: list[Any] = []

        async def app_that_sends_body(
            scope,
            receive,
            send,
        ) -> None:
            await send(
                {
                    const.TYPE_KEY: test_const.HTTP_EVENT_RESPONSE_START,
                    const.RESPONSE_STATUS_KEY: 200,
                    const.HEADERS_KEY: [],
                }
            )
            await send(
                {
                    const.TYPE_KEY: test_const.HTTP_EVENT_RESPONSE_BODY,
                    "body": b"test",
                }
            )

        async def recording_send(message: Any) -> None:
            messages.append(message)

        middleware = asgi_client.CorrelationIdMiddleware(app_that_sends_body)
        await middleware(basic_http_scope, mock_receive, recording_send)
        assert len(messages) == 2
        assert messages[0][const.TYPE_KEY] == test_const.HTTP_EVENT_RESPONSE_START
        assert messages[1][const.TYPE_KEY] == test_const.HTTP_EVENT_RESPONSE_BODY
        assert messages[1]["body"] == b"test"
