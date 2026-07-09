"""CorrelationInterceptor: gRPC inbound entry surface for correlation-ID setup."""

from __future__ import annotations

from collections.abc import Callable

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
        """Extract and set the correlation ID from gRPC invocation metadata."""
        metadata: objs.Metadata = handler_call_details.invocation_metadata
        correlation = objs.GRPCCorrelation.from_metadata(metadata)
        set_correlation_id(correlation.correlation_id)
        try:
            return continuation(handler_call_details)
        finally:
            clear_correlation_id()
