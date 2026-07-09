"""Tests for WebSocketCorrelation dataclass."""

from __future__ import annotations

import pytest

from mixin_logging.adapters.constants import websocket as const
from mixin_logging.adapters.websocket import websocket_objects as objs
from mixin_logging.common.constants import tests as test_const


class TestWebSocketCorrelationFromHeaders:
    """Tests for WebSocketCorrelation.from_headers() class method."""

    def test_from_headers_with_header_present(
        self, websocket_scope_with_correlation
    ) -> None:
        """from_headers() decodes header and sets extracted=True."""
        headers = websocket_scope_with_correlation["headers"]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert correlation.correlation_id == test_const.CORRELATION_ID_TRACE
        assert correlation.extracted is True

    def test_from_headers_without_header_generates_id(
        self, basic_websocket_scope
    ) -> None:
        """from_headers() generates 12-hex correlation ID and sets extracted=False."""
        headers = basic_websocket_scope["headers"]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_headers_case_insensitive_header_match(
        self, websocket_scope_with_case_insensitive_header
    ) -> None:
        """from_headers() matches correlation ID header case-insensitively."""
        headers = websocket_scope_with_case_insensitive_header["headers"]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert correlation.correlation_id == test_const.CORRELATION_ID_CUSTOM
        assert correlation.extracted is True

    def test_from_headers_rejects_carriage_return_in_header(
        self, websocket_scope_with_carriage_return_header
    ) -> None:
        """from_headers() rejects header with CR and falls back to generated ID."""
        headers = websocket_scope_with_carriage_return_header["headers"]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_headers_rejects_newline_in_header(
        self, websocket_scope_with_newline_header
    ) -> None:
        """from_headers() rejects header with LF and falls back to generated ID."""
        headers = websocket_scope_with_newline_header["headers"]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_headers_rejects_null_byte_in_header(
        self, websocket_scope_with_null_byte_header
    ) -> None:
        """from_headers() rejects header with null byte and falls back to generated ID."""
        headers = websocket_scope_with_null_byte_header["headers"]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_headers_rejects_oversized_header(
        self, websocket_scope_with_oversized_header
    ) -> None:
        """from_headers() rejects header exceeding MAX_LENGTH and falls back to generated ID."""
        headers = websocket_scope_with_oversized_header["headers"]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_headers_stops_after_first_correlation_header(self) -> None:
        """from_headers() processes only the first correlation ID header and ignores later ones."""
        headers = [
            (b"other-header", b"value1"),
            (
                const.CORRELATION_ID_HEADER.encode(),
                test_const.CORRELATION_ID_TRACE.encode(),
            ),
            (b"another-header", b"value2"),
            (const.CORRELATION_ID_HEADER.encode(), b"should-be-ignored"),
        ]
        correlation = objs.WebSocketCorrelation.from_headers(headers)
        assert correlation.correlation_id == test_const.CORRELATION_ID_TRACE
        assert correlation.extracted is True


class TestWebSocketCorrelationIsSafe:
    """Tests for WebSocketCorrelation._is_safe() static method."""

    def test_is_safe_rejects_empty_string(self) -> None:
        """_is_safe() returns False for empty string."""
        assert objs.WebSocketCorrelation._is_safe("") is False

    def test_is_safe_with_valid_value(self) -> None:
        """_is_safe() returns True for clean alphanumeric value."""
        assert (
            objs.WebSocketCorrelation._is_safe(test_const.CORRELATION_ID_VALID_ID_123)
            is True
        )

    def test_is_safe_with_hex_value(self) -> None:
        """_is_safe() returns True for 12-hex UUID value."""
        assert objs.WebSocketCorrelation._is_safe(test_const.CORRELATION_ID_HEX) is True

    def test_is_safe_with_carriage_return(self) -> None:
        """_is_safe() returns False if value contains CR."""
        assert objs.WebSocketCorrelation._is_safe("test\rid") is False

    def test_is_safe_with_newline(self) -> None:
        """_is_safe() returns False if value contains LF."""
        assert objs.WebSocketCorrelation._is_safe("test\nid") is False

    def test_is_safe_with_null_byte(self) -> None:
        """_is_safe() returns False if value contains null byte."""
        assert objs.WebSocketCorrelation._is_safe("test\x00id") is False

    def test_is_safe_with_oversized_value(self) -> None:
        """_is_safe() returns False if value exceeds MAX_LENGTH."""
        oversized = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        assert objs.WebSocketCorrelation._is_safe(oversized) is False

    def test_is_safe_at_max_length_boundary(self) -> None:
        """_is_safe() returns True for value at exactly MAX_LENGTH."""
        at_max = "a" * const.CORRELATION_ID_MAX_LENGTH
        assert objs.WebSocketCorrelation._is_safe(at_max) is True

    def test_is_safe_just_under_max_length(self) -> None:
        """_is_safe() returns True for value just under MAX_LENGTH."""
        just_under = "a" * (const.CORRELATION_ID_MAX_LENGTH - 1)
        assert objs.WebSocketCorrelation._is_safe(just_under) is True


class TestWebSocketCorrelationPostInit:
    """Tests for WebSocketCorrelation.__post_init__() validation."""

    def test_post_init_raises_on_unsafe_correlation_id(self) -> None:
        """__post_init__() raises ValueError if correlation_id is unsafe."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.WebSocketCorrelation(correlation_id="test\rid", extracted=False)

    def test_post_init_raises_on_empty_correlation_id(self) -> None:
        """__post_init__() raises ValueError if correlation_id is empty string."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.WebSocketCorrelation(correlation_id="", extracted=False)

    def test_post_init_accepts_safe_string(self) -> None:
        """__post_init__() accepts any safe correlation_id."""
        correlation = objs.WebSocketCorrelation(
            correlation_id=test_const.CORRELATION_ID_VALID_ID_123, extracted=True
        )
        assert correlation.correlation_id == test_const.CORRELATION_ID_VALID_ID_123

    def test_post_init_raises_on_oversized_correlation_id(self) -> None:
        """__post_init__() raises ValueError if correlation_id exceeds MAX_LENGTH."""
        oversized = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.WebSocketCorrelation(correlation_id=oversized, extracted=False)
