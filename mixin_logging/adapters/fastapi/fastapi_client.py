"""FastAPI middleware and dependency for correlation-ID propagation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.adapters.fastapi import fastapi_objects as objs
from mixin_logging.adapters.fastapi.constants import ERR_FASTAPI_NO_CORRELATION_ID


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for correlation-ID context propagation."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Extract correlation ID, set context, execute handler, inject response header, clear context."""
        headers = dict(request.headers)
        correlation = objs.FastApiCorrelation.from_headers(headers)

        set_correlation_id(correlation.correlation_id)
        try:
            response = await call_next(request)
            response.headers[correlation.response_header[0]] = (
                correlation.response_header[1]
            )
            return response
        finally:
            clear_correlation_id()


async def get_correlation_id_dependency() -> str:
    """FastAPI dependency that returns the current correlation ID from context.

    Raises ValueError if no correlation ID is set in context (should not happen if middleware is installed).
    Use in route handlers: `async def my_handler(corr_id: str = Depends(get_correlation_id_dependency))`
    """
    from mixin_logging import get_correlation_id

    corr_id = get_correlation_id()
    if corr_id is None:
        raise ValueError(ERR_FASTAPI_NO_CORRELATION_ID)
    return corr_id
