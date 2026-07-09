"""Tests for CorrelationInterceptor gRPC server interceptor."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import grpc
import pytest

from mixin_logging import get_correlation_id
from mixin_logging.adapters.grpc import grpc_client
from mixin_logging.common.constants import tests as test_const


class TestCorrelationInterceptorIntercept:
    """Tests for CorrelationInterceptor.intercept_service() method."""

    def test_intercept_extracts_and_sets_correlation_from_metadata(self) -> None:
        """intercept_service() extracts correlation ID and sets it in context."""
        interceptor = grpc_client.CorrelationInterceptor()

        metadata: list[tuple[str, str]] = [
            ("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),
            ("other-header", "value"),
        ]
        handler_call_details = MagicMock(spec=grpc.HandlerCallDetails)
        handler_call_details.invocation_metadata = tuple(metadata)

        called_with_correlation_id: list[str | None] = []

        def side_effect_track_correlation(call_details: Any) -> MagicMock:
            called_with_correlation_id.append(get_correlation_id())
            return MagicMock(spec=grpc.RpcMethodHandler)

        continuation = MagicMock(side_effect=side_effect_track_correlation)

        result = interceptor.intercept_service(continuation, handler_call_details)

        assert result is not None
        assert len(called_with_correlation_id) == 1
        assert called_with_correlation_id[0] == test_const.CORRELATION_ID_VALID_ID_123
        continuation.assert_called_once_with(handler_call_details)

    def test_intercept_clears_correlation_after_continuation_returns(self) -> None:
        """intercept_service() clears correlation context in finally block."""
        interceptor = grpc_client.CorrelationInterceptor()

        metadata: list[tuple[str, str]] = [
            ("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),
        ]
        handler_call_details = MagicMock(spec=grpc.HandlerCallDetails)
        handler_call_details.invocation_metadata = tuple(metadata)

        continuation = MagicMock(return_value=MagicMock(spec=grpc.RpcMethodHandler))

        result = interceptor.intercept_service(continuation, handler_call_details)

        assert result is not None
        assert get_correlation_id() is None

    def test_intercept_clears_correlation_even_if_continuation_raises(self) -> None:
        """intercept_service() clears context even if continuation raises exception."""
        interceptor = grpc_client.CorrelationInterceptor()

        metadata: list[tuple[str, str]] = [
            ("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),
        ]
        handler_call_details = MagicMock(spec=grpc.HandlerCallDetails)
        handler_call_details.invocation_metadata = tuple(metadata)

        def failing_continuation(call_details: Any) -> None:
            raise RuntimeError("test error")

        with pytest.raises(RuntimeError, match="test error"):
            interceptor.intercept_service(failing_continuation, handler_call_details)

        assert get_correlation_id() is None

    def test_intercept_returns_continuation_result(self) -> None:
        """intercept_service() returns the result from continuation."""
        interceptor = grpc_client.CorrelationInterceptor()

        metadata: list[tuple[str, str]] = []
        handler_call_details = MagicMock(spec=grpc.HandlerCallDetails)
        handler_call_details.invocation_metadata = tuple(metadata)

        expected_handler = MagicMock(spec=grpc.RpcMethodHandler)
        continuation = MagicMock(return_value=expected_handler)

        result = interceptor.intercept_service(continuation, handler_call_details)

        assert result is expected_handler

    def test_intercept_generates_id_when_absent_from_metadata(self) -> None:
        """intercept_service() generates correlation ID when x-correlation-id absent."""
        interceptor = grpc_client.CorrelationInterceptor()

        metadata: list[tuple[str, str]] = [
            ("other-header", "value"),
        ]
        handler_call_details = MagicMock(spec=grpc.HandlerCallDetails)
        handler_call_details.invocation_metadata = tuple(metadata)

        captured_correlation_ids: list[str | None] = []

        def side_effect_capture_id(call_details: Any) -> MagicMock:
            captured_correlation_ids.append(get_correlation_id())
            return MagicMock(spec=grpc.RpcMethodHandler)

        continuation = MagicMock(side_effect=side_effect_capture_id)

        result = interceptor.intercept_service(continuation, handler_call_details)

        assert result is not None
        assert len(captured_correlation_ids) == 1
        captured_id = captured_correlation_ids[0]
        assert captured_id is not None
        assert len(captured_id) == 12
        assert all(char in "0123456789abcdef" for char in captured_id)

    def test_intercept_generates_id_when_metadata_unsafe(self) -> None:
        """intercept_service() generates ID when metadata value is unsafe."""
        interceptor = grpc_client.CorrelationInterceptor()

        metadata: list[tuple[str, str]] = [
            ("x-correlation-id", "test\r-bad"),
        ]
        handler_call_details = MagicMock(spec=grpc.HandlerCallDetails)
        handler_call_details.invocation_metadata = tuple(metadata)

        captured_correlation_ids: list[str | None] = []

        def side_effect_capture_unsafe_id(call_details: Any) -> MagicMock:
            captured_correlation_ids.append(get_correlation_id())
            return MagicMock(spec=grpc.RpcMethodHandler)

        continuation = MagicMock(side_effect=side_effect_capture_unsafe_id)

        result = interceptor.intercept_service(continuation, handler_call_details)

        assert result is not None
        assert len(captured_correlation_ids) == 1
        captured_id = captured_correlation_ids[0]
        assert captured_id is not None
        assert len(captured_id) == 12
        assert all(char in "0123456789abcdef" for char in captured_id)

    def test_intercept_with_empty_metadata(self) -> None:
        """intercept_service() generates ID with empty metadata tuple."""
        interceptor = grpc_client.CorrelationInterceptor()

        handler_call_details = MagicMock(spec=grpc.HandlerCallDetails)
        handler_call_details.invocation_metadata = ()

        captured_correlation_ids: list[str | None] = []

        def side_effect_capture_empty_meta_id(call_details: Any) -> MagicMock:
            captured_correlation_ids.append(get_correlation_id())
            return MagicMock(spec=grpc.RpcMethodHandler)

        continuation = MagicMock(side_effect=side_effect_capture_empty_meta_id)

        result = interceptor.intercept_service(continuation, handler_call_details)

        assert result is not None
        assert len(captured_correlation_ids) == 1
        captured_id = captured_correlation_ids[0]
        assert captured_id is not None
        assert len(captured_id) == 12

    def test_intercept_inherits_from_server_interceptor(self) -> None:
        """CorrelationInterceptor is a grpc.ServerInterceptor."""
        interceptor = grpc_client.CorrelationInterceptor()
        assert isinstance(interceptor, grpc.ServerInterceptor)
