"""CorrelationIdMiddleware: WebSocket inbound entry surface for correlation-ID setup."""

from __future__ import annotations

from typing import Any

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.adapters.constants import websocket as const
from mixin_logging.adapters.websocket import websocket_objects as objs

__all__ = ["CorrelationIdMiddleware"]

Scope = dict[str, Any]
Receive = Any
Send = Any
App = Any


class CorrelationIdMiddleware:
    """ASGI middleware that extracts correlation-ID from WebSocket handshake headers."""

    def __init__(self, app: App) -> None:
        """Wrap the downstream ASGI app."""
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """Set correlation context for websocket scopes only; passthrough otherwise."""
        if scope[const.TYPE_KEY] != const.WEBSOCKET_SCOPE_TYPE:
            await self.app(scope, receive, send)
            return

        headers: objs.Headers = scope.get(const.HEADERS_KEY, [])
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        set_correlation_id(correlation.correlation_id)
        try:
            await self.app(scope, receive, send)
        finally:
            clear_correlation_id()
