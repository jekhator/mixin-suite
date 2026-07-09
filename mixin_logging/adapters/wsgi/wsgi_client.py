"""WsgiApp + CorrelationIdMiddleware: WSGI middleware for correlation ID propagation."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Optional

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.adapters.wsgi import wsgi_objects as objs


@dataclass(frozen=True, slots=True)
class WsgiApp:
    """Set the resolved correlation ID into context, then run the wrapped app."""

    app: objs.App
    correlation: objs.WsgiCorrelation

    def __call__(
        self,
        environ: objs.Environ,
        start_response: objs.StartResponse,
    ) -> Iterable[bytes]:
        """Set correlation context, then delegate to the wrapped WSGI app."""
        set_correlation_id(self.correlation.correlation_id)
        return self.app(environ, start_response)


@dataclass(frozen=True, slots=True)
class CorrelationIdMiddleware:
    """WSGI middleware for correlation ID context propagation."""

    app: objs.App

    def __call__(
        self,
        environ: objs.Environ,
        start_response: objs.StartResponse,
    ) -> Iterable[bytes]:
        """Resolve correlation, wrap start_response to inject header, execute, clear on exit."""
        correlation = objs.WsgiCorrelation.from_environ(environ)
        set_correlation_id(correlation.correlation_id)

        def wrapped_start_response(
            status: str,
            headers: objs.Headers,
            exc_info: Optional[objs.ExcInfo] = None,
        ) -> Callable[[bytes], None]:
            """Inject correlation ID header before delegating to original start_response."""
            headers.append(correlation.response_header)
            return start_response(status, headers, exc_info)

        try:
            yield from self.app(environ, wrapped_start_response)
        finally:
            clear_correlation_id()
