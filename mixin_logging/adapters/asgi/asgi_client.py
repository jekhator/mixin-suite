"""ASGIApp + CorrelationIdMiddleware: ASGI middleware for correlation ID propagation."""

from __future__ import annotations

from dataclasses import dataclass

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.adapters.asgi import asgi_objects as objs
from mixin_logging.adapters.constants import asgi as const


@dataclass(frozen=True, slots=True)
class ASGIApp:
    """Set the resolved correlation ID into context, then run the wrapped app."""

    app: objs.App
    correlation: objs.AsgiCorrelation

    async def __call__(
        self,
        scope: objs.Scope,
        receive: objs.Receive,
        send: objs.Send,
    ) -> None:
        """Set correlation context, then delegate to the wrapped app."""
        set_correlation_id(self.correlation.correlation_id)
        await self.app(scope, receive, send)


@dataclass(frozen=True, slots=True)
class CorrelationIdMiddleware:
    """ASGI middleware for correlation ID context propagation."""

    app: objs.App

    async def __call__(
        self,
        scope: objs.Scope,
        receive: objs.Receive,
        send: objs.Send,
    ) -> None:
        """Resolve, wrap send, execute via ASGIApp, clear on exit."""
        if scope[const.TYPE_KEY] != const.HTTP_SCOPE_TYPE:
            await self.app(scope, receive, send)
            return

        correlation = objs.AsgiCorrelation.from_scope(scope)

        async def wrapped_send(message: objs.Message) -> None:
            """Inject correlation ID into response start message."""
            if message[const.TYPE_KEY] == const.RESPONSE_START_MESSAGE_TYPE:
                headers = list(message.get(const.HEADERS_KEY, []))
                headers.append(correlation.response_header)
                message[const.HEADERS_KEY] = headers
            await send(message)

        try:
            await ASGIApp(self.app, correlation)(scope, receive, wrapped_send)
        finally:
            clear_correlation_id()
