"""gRPC-specific pytest fixtures for adapter tests.

Used by TestCorrelationInterceptorIntercept, TestCorrelationInterceptorBinding and
TestCorrelationInterceptorServer.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from concurrent import futures

import grpc
import pytest

from mixin_logging import clear_correlation_id
from mixin_logging.adapters.grpc import grpc_client


@pytest.fixture(autouse=True)
def reset_correlation() -> Iterator[None]:
    """Clear correlation context before and after each test for isolation."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def grpc_server_factory() -> Iterator[
    Callable[[dict[str, grpc.RpcMethodHandler]], int]
]:
    """In-process sync gRPC server on an ephemeral port with CorrelationInterceptor installed.

    Used by TestCorrelationInterceptorServer. Yields a callable that takes a
    full-method-name to handler mapping and returns the bound port.
    """
    servers: list[grpc.Server] = []

    def start(handlers: dict[str, grpc.RpcMethodHandler]) -> int:
        """Start a server exposing the given method handlers and return its port."""
        server = grpc.server(
            futures.ThreadPoolExecutor(max_workers=2),
            interceptors=[grpc_client.CorrelationInterceptor()],
        )
        server.add_generic_rpc_handlers((_GenericHandler(handlers),))
        port = server.add_insecure_port("localhost:0")
        server.start()
        servers.append(server)
        return port

    yield start
    for server in servers:
        server.stop(None)


class _GenericHandler(grpc.GenericRpcHandler):
    """Route full method names to prebuilt handlers for the in-process test server."""

    def __init__(self, handlers: dict[str, grpc.RpcMethodHandler]) -> None:
        """Store the method-name to handler mapping."""
        self._handlers = handlers

    def service(
        self, handler_call_details: grpc.HandlerCallDetails
    ) -> grpc.RpcMethodHandler | None:
        """Return the handler registered for the called method, or None."""
        return self._handlers.get(handler_call_details.method)
