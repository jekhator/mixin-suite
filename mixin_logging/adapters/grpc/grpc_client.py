"""CorrelationInterceptor: gRPC inbound entry surface for correlation-ID setup."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterable

import grpc

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.adapters.grpc import grpc_objects as objs


class CorrelationInterceptor(grpc.ServerInterceptor):
    """Entry surface for extracting correlation-ID from inbound gRPC metadata."""

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler | None],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler | None:
        """Extract the correlation ID and bind it to each handler callable."""
        metadata: objs.Metadata = handler_call_details.invocation_metadata
        correlation = objs.GRPCCorrelation.from_metadata(metadata)
        handler = continuation(handler_call_details)
        if handler is None:
            return None
        correlation_id = correlation.correlation_id
        # Concrete grpc handlers are namedtuples; the abstract stub does not declare _replace.
        return handler._replace(  # type: ignore[attr-defined]
            unary_unary=self._bind_unary(handler.unary_unary, correlation_id),
            stream_unary=self._bind_unary(handler.stream_unary, correlation_id),
            unary_stream=self._bind_stream(handler.unary_stream, correlation_id),
            stream_stream=self._bind_stream(handler.stream_stream, correlation_id),
        )

    def _bind_unary(
        self, method: Callable[..., object] | None, correlation_id: str
    ) -> Callable[..., object] | None:
        """Wrap a handler that returns one response so the context is set during the call."""
        if method is None:
            return None

        def bound(*args: object) -> object:
            """Run the handler with the correlation context set."""
            set_correlation_id(correlation_id)
            try:
                return method(*args)
            finally:
                clear_correlation_id()

        return bound

    def _bind_stream(
        self, method: Callable[..., Iterable[object]] | None, correlation_id: str
    ) -> Callable[..., Generator[object, None, None]] | None:
        """Wrap a handler that returns a response iterator so each step runs with the context set."""
        if method is None:
            return None

        def bound(*args: object) -> Generator[object, None, None]:
            """Yield the handler's responses, setting the context only while each one is produced."""
            set_correlation_id(correlation_id)
            try:
                iterator = iter(method(*args))
            finally:
                clear_correlation_id()
            while True:
                set_correlation_id(correlation_id)
                try:
                    item = next(iterator)
                except StopIteration:
                    return
                finally:
                    clear_correlation_id()
                yield item

        return bound
