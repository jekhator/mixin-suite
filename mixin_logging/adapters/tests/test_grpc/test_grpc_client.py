"""Tests for CorrelationInterceptor gRPC server interceptor."""

from __future__ import annotations

from collections.abc import Callable, Generator, Iterator
from typing import Any, cast
from unittest.mock import MagicMock

import grpc
import pytest

from mixin_logging import get_correlation_id
from mixin_logging.adapters.constants import grpc as const
from mixin_logging.adapters.grpc import grpc_client
from mixin_logging.common.constants import tests as test_const

HEX_CHARS = "0123456789abcdef"


def _context() -> grpc.ServicerContext:
    """Return a mock servicer context for calling handler callables directly."""
    return MagicMock(spec=grpc.ServicerContext)


def _unary(handler: grpc.RpcMethodHandler) -> Callable[..., object]:
    """Return the unary-unary callable of a handler, failing the test if it is absent."""
    method = handler.unary_unary
    assert method is not None
    return method


def _stream(
    handler: grpc.RpcMethodHandler,
) -> Callable[..., Iterator[object]]:
    """Return the unary-stream callable of a handler, failing the test if it is absent."""
    method = handler.unary_stream
    assert method is not None
    return method


def _details(metadata: tuple[tuple[str, str], ...]) -> grpc.HandlerCallDetails:
    """Build handler call details carrying the given invocation metadata."""
    details = MagicMock(spec=grpc.HandlerCallDetails)
    details.invocation_metadata = metadata
    details.method = "/test.Service/Method"
    return details


def _unary_handler(seen: list[str | None]) -> grpc.RpcMethodHandler:
    """Build a unary handler that records the correlation ID seen while it runs."""

    def method(request: bytes, context: Any) -> bytes:
        """Record the active correlation ID and echo the request."""
        seen.append(get_correlation_id())
        return request

    return grpc.unary_unary_rpc_method_handler(method)


def _stream_handler(seen: list[str | None], items: int) -> grpc.RpcMethodHandler:
    """Build a unary-stream handler that records the correlation ID for each produced item."""

    def method(request: bytes, context: Any) -> Iterator[bytes]:
        """Yield items, recording the correlation ID as each one is produced."""
        for index in range(items):
            seen.append(get_correlation_id())
            yield str(index).encode()

    return grpc.unary_stream_rpc_method_handler(method)


class TestCorrelationInterceptorIntercept:
    """Tests for CorrelationInterceptor.intercept_service() method."""

    def test_intercept_returns_none_when_no_handler_matches(self) -> None:
        """intercept_service() returns None when the continuation finds no handler."""
        interceptor = grpc_client.CorrelationInterceptor()
        continuation = MagicMock(return_value=None)

        result = interceptor.intercept_service(
            continuation,
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert result is None
        continuation.assert_called_once()

    def test_intercept_does_not_set_context_during_continuation(self) -> None:
        """intercept_service() leaves the context unset while the continuation runs."""
        interceptor = grpc_client.CorrelationInterceptor()
        observed: list[str | None] = []

        def continuation(call_details: Any) -> grpc.RpcMethodHandler:
            """Record the correlation ID visible to the continuation."""
            observed.append(get_correlation_id())
            return _unary_handler([])

        interceptor.intercept_service(
            continuation,
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert observed == [None]

    def test_intercept_clears_correlation_after_returning_handler(self) -> None:
        """intercept_service() leaves no correlation context behind after binding the handler."""
        interceptor = grpc_client.CorrelationInterceptor()
        continuation = MagicMock(return_value=_unary_handler([]))

        result = interceptor.intercept_service(
            continuation,
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert result is not None
        assert get_correlation_id() is None

    def test_intercept_clears_correlation_even_if_continuation_raises(self) -> None:
        """intercept_service() propagates a continuation error without leaving context set."""
        interceptor = grpc_client.CorrelationInterceptor()

        def failing_continuation(call_details: Any) -> None:
            """Raise to simulate a failing continuation."""
            raise RuntimeError(test_const.ERR_TEST_CONTINUATION_FAILED)

        with pytest.raises(RuntimeError, match=test_const.ERR_TEST_CONTINUATION_FAILED):
            interceptor.intercept_service(
                failing_continuation,
                _details(
                    (("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)
                ),
            )

        assert get_correlation_id() is None

    def test_intercept_generates_id_when_absent_from_metadata(self) -> None:
        """intercept_service() binds a generated 12-character hex ID when the header is absent."""
        seen: list[str | None] = []
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_unary_handler(seen)),
            _details((("other-header", "value"),)),
        )

        assert handler is not None
        _unary(handler)(b"", _context())

        assert len(seen) == 1
        assert seen[0] is not None
        assert len(seen[0]) == const.GENERATED_ID_LENGTH
        assert all(char in HEX_CHARS for char in seen[0])

    def test_intercept_generates_id_when_metadata_unsafe(self) -> None:
        """intercept_service() binds a generated ID when the header value contains a CR."""
        seen: list[str | None] = []
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_unary_handler(seen)),
            _details((("x-correlation-id", test_const.CORRELATION_ID_UNSAFE_CR),)),
        )

        assert handler is not None
        _unary(handler)(b"", _context())

        assert len(seen) == 1
        assert seen[0] is not None
        assert len(seen[0]) == const.GENERATED_ID_LENGTH

    def test_intercept_with_empty_metadata(self) -> None:
        """intercept_service() binds a generated ID when the metadata tuple is empty."""
        seen: list[str | None] = []
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_unary_handler(seen)), _details(())
        )

        assert handler is not None
        _unary(handler)(b"", _context())

        assert seen[0] is not None
        assert len(seen[0]) == const.GENERATED_ID_LENGTH

    def test_intercept_inherits_from_server_interceptor(self) -> None:
        """CorrelationInterceptor is a grpc.ServerInterceptor."""
        interceptor = grpc_client.CorrelationInterceptor()
        assert isinstance(interceptor, grpc.ServerInterceptor)


class TestCorrelationInterceptorBinding:
    """Tests that the correlation context is active while handler callables run."""

    def test_unary_handler_sees_extracted_correlation_id(self) -> None:
        """A unary handler runs with the correlation ID extracted from metadata."""
        seen: list[str | None] = []
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_unary_handler(seen)),
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert handler is not None
        assert _unary(handler)(b"payload", _context()) == b"payload"

        assert seen == [test_const.CORRELATION_ID_VALID_ID_123]
        assert get_correlation_id() is None

    def test_unary_handler_context_cleared_when_handler_raises(self) -> None:
        """A failing unary handler propagates its error and leaves no context behind."""

        def method(request: bytes, context: Any) -> bytes:
            """Raise to simulate a failing handler."""
            raise RuntimeError(test_const.ERR_TEST_HANDLER_FAILED)

        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=grpc.unary_unary_rpc_method_handler(method)),
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert handler is not None
        with pytest.raises(RuntimeError, match=test_const.ERR_TEST_HANDLER_FAILED):
            _unary(handler)(b"", _context())

        assert get_correlation_id() is None

    def test_stream_handler_sees_correlation_id_for_every_item(self) -> None:
        """Each item of a server-streaming response is produced with the correlation context set."""
        seen: list[str | None] = []
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_stream_handler(seen, items=3)),
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert handler is not None
        produced = list(_stream(handler)(b"", _context()))

        assert produced == [b"0", b"1", b"2"]
        assert seen == [test_const.CORRELATION_ID_VALID_ID_123] * 3
        assert get_correlation_id() is None

    def test_stream_handler_context_cleared_between_items(self) -> None:
        """Between streamed items the context is not left set on the consuming thread."""
        seen: list[str | None] = []
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_stream_handler(seen, items=2)),
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert handler is not None
        stream = _stream(handler)(b"", _context())
        next(stream)

        assert get_correlation_id() is None
        assert list(stream) == [b"1"]

    def test_stream_handler_context_cleared_when_stream_closed_early(self) -> None:
        """Closing a server stream before it is exhausted leaves no context behind."""
        seen: list[str | None] = []
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_stream_handler(seen, items=3)),
            _details((("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),)),
        )

        assert handler is not None
        stream = cast(Generator[object, None, None], _stream(handler)(b"", _context()))
        next(stream)
        stream.close()

        assert get_correlation_id() is None

    def test_handler_callables_absent_from_handler_stay_none(self) -> None:
        """Only the callables a handler defines are bound; the others stay None."""
        interceptor = grpc_client.CorrelationInterceptor()
        handler = interceptor.intercept_service(
            MagicMock(return_value=_unary_handler([])), _details(())
        )

        assert handler is not None
        assert handler.unary_stream is None
        assert handler.stream_unary is None
        assert handler.stream_stream is None
        assert handler.unary_unary is not None


class TestCorrelationInterceptorServer:
    """End-to-end tests against an in-process gRPC server with the interceptor installed."""

    def test_rpc_handler_observes_metadata_correlation_id(
        self, grpc_server_factory: Callable[[dict[str, grpc.RpcMethodHandler]], int]
    ) -> None:
        """A real RPC carrying x-correlation-id runs its handler with that ID set."""
        seen: list[str | None] = []
        port = grpc_server_factory({"/test.Service/Method": _unary_handler(seen)})

        with grpc.insecure_channel(f"localhost:{port}") as channel:
            call: grpc.UnaryUnaryMultiCallable = channel.unary_unary(
                "/test.Service/Method"
            )
            reply = call(
                b"ping",
                metadata=(
                    ("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),
                ),
                timeout=test_const.GRPC_CALL_TIMEOUT_SECONDS,
            )

        assert reply == b"ping"
        assert seen == [test_const.CORRELATION_ID_VALID_ID_123]
