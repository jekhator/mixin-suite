"""Tests for AsgiCorrelation dataclass."""

from __future__ import annotations

import pytest

from mixin_logging.adapters.asgi import asgi_objects as asgi_objs
from mixin_logging.adapters.constants import asgi as const
from mixin_logging.common.constants import tests as test_const


class TestAsgiCorrelationFromScope:
    """Tests for AsgiCorrelation.from_scope() class method."""

    def test_from_scope_with_header_present(self, http_scope_with_correlation) -> None:
        """from_scope() decodes header and sets from_header=True."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(http_scope_with_correlation)
        assert correlation.correlation_id == test_const.CORRELATION_ID_TRACE
        assert correlation.from_header is True

    def test_from_scope_without_header_generates_id(self, basic_http_scope) -> None:
        """from_scope() generates 12-hex correlation ID and sets from_header=False."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(basic_http_scope)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_case_insensitive_header_match(
        self, http_scope_with_case_insensitive_header
    ) -> None:
        """from_scope() matches correlation ID header case-insensitively."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_case_insensitive_header
        )
        assert correlation.correlation_id == test_const.CORRELATION_ID_CUSTOM
        assert correlation.from_header is True

    def test_from_scope_rejects_carriage_return_in_header(
        self, http_scope_with_carriage_return_header
    ) -> None:
        """from_scope() rejects header with CR and falls back to generated ID."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_carriage_return_header
        )
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_rejects_newline_in_header(
        self, http_scope_with_newline_header
    ) -> None:
        """from_scope() rejects header with LF and falls back to generated ID."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_newline_header
        )
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_rejects_null_byte_in_header(
        self, http_scope_with_null_byte_header
    ) -> None:
        """from_scope() rejects header with null byte and falls back to generated ID."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_null_byte_header
        )
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_rejects_oversized_header(
        self, http_scope_with_oversized_header
    ) -> None:
        """from_scope() rejects header exceeding MAX_LENGTH and falls back to generated ID."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_oversized_header
        )
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_rejects_invalid_utf8_header(
        self, http_scope_with_invalid_utf8_header
    ) -> None:
        """from_scope() rejects invalid UTF-8 header and falls back to generated ID without exception."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_invalid_utf8_header
        )
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_rejects_string_header_name(
        self, http_scope_with_string_header_name
    ) -> None:
        """from_scope() skips headers with string (non-bytes) name and falls back to generated ID."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_string_header_name
        )
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_rejects_string_header_value(
        self, http_scope_with_string_header_value
    ) -> None:
        """from_scope() skips headers with string (non-bytes) value and falls back to generated ID."""
        correlation = asgi_objs.AsgiCorrelation.from_scope(
            http_scope_with_string_header_value
        )
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.from_header is False

    def test_from_scope_stops_after_first_correlation_header(self) -> None:
        """from_scope() processes only the first correlation ID header and ignores later ones."""
        scope = {
            const.TYPE_KEY: "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            const.HEADERS_KEY: [
                (b"other-header", b"value1"),
                (
                    const.CORRELATION_ID_HEADER,
                    test_const.CORRELATION_ID_TRACE.encode(),
                ),
                (b"another-header", b"value2"),
                (const.CORRELATION_ID_HEADER, b"should-be-ignored"),
            ],
        }
        correlation = asgi_objs.AsgiCorrelation.from_scope(scope)
        assert correlation.correlation_id == test_const.CORRELATION_ID_TRACE
        assert correlation.from_header is True


class TestAsgiCorrelationIsSafe:
    """Tests for AsgiCorrelation._is_safe() static method."""

    def test_is_safe_rejects_empty_string(self) -> None:
        """_is_safe() returns False for empty string."""
        assert asgi_objs.AsgiCorrelation._is_safe("") is False

    def test_is_safe_with_valid_value(self) -> None:
        """_is_safe() returns True for clean alphanumeric value."""
        assert (
            asgi_objs.AsgiCorrelation._is_safe(test_const.CORRELATION_ID_VALID_ID_123)
            is True
        )

    def test_is_safe_with_hex_value(self) -> None:
        """_is_safe() returns True for 12-hex UUID value."""
        assert asgi_objs.AsgiCorrelation._is_safe(test_const.CORRELATION_ID_HEX) is True

    def test_is_safe_with_carriage_return(self) -> None:
        """_is_safe() returns False if value contains CR."""
        assert asgi_objs.AsgiCorrelation._is_safe("test\rid") is False

    def test_is_safe_with_newline(self) -> None:
        """_is_safe() returns False if value contains LF."""
        assert asgi_objs.AsgiCorrelation._is_safe("test\nid") is False

    def test_is_safe_with_null_byte(self) -> None:
        """_is_safe() returns False if value contains null byte."""
        assert asgi_objs.AsgiCorrelation._is_safe("test\x00id") is False

    def test_is_safe_with_oversized_value(self) -> None:
        """_is_safe() returns False if value exceeds MAX_LENGTH."""
        oversized = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        assert asgi_objs.AsgiCorrelation._is_safe(oversized) is False

    def test_is_safe_at_max_length_boundary(self) -> None:
        """_is_safe() returns True for value at exactly MAX_LENGTH."""
        at_max = "a" * const.CORRELATION_ID_MAX_LENGTH
        assert asgi_objs.AsgiCorrelation._is_safe(at_max) is True

    def test_is_safe_just_under_max_length(self) -> None:
        """_is_safe() returns True for value just under MAX_LENGTH."""
        just_under = "a" * (const.CORRELATION_ID_MAX_LENGTH - 1)
        assert asgi_objs.AsgiCorrelation._is_safe(just_under) is True


class TestAsgiCorrelationPostInit:
    """Tests for AsgiCorrelation.__post_init__() validation."""

    def test_post_init_raises_on_empty_correlation_id(self) -> None:
        """__post_init__() raises ValueError if correlation_id is empty string."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_EMPTY):
            asgi_objs.AsgiCorrelation(correlation_id="", from_header=False)

    def test_post_init_accepts_non_empty_string(self) -> None:
        """__post_init__() accepts any non-empty correlation_id."""
        correlation = asgi_objs.AsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_VALID_ID_123, from_header=True
        )
        assert correlation.correlation_id == test_const.CORRELATION_ID_VALID_ID_123


class TestAsgiCorrelationResponseHeader:
    """Tests for AsgiCorrelation.response_header property."""

    def test_response_header_returns_tuple(self) -> None:
        """response_header returns (header_name, header_value) tuple of bytes."""
        correlation = asgi_objs.AsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TRACE,
            from_header=True,
        )
        header_name, header_value = correlation.response_header
        assert isinstance(header_name, bytes)
        assert isinstance(header_value, bytes)

    def test_response_header_encodes_correlation_id(self) -> None:
        """response_header encodes correlation_id to bytes."""
        correlation = asgi_objs.AsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TRACE,
            from_header=True,
        )
        _, header_value = correlation.response_header
        assert header_value == test_const.CORRELATION_ID_TRACE.encode()

    def test_response_header_uses_correct_header_name(self) -> None:
        """response_header uses CORRELATION_ID_HEADER constant."""
        correlation = asgi_objs.AsgiCorrelation(
            correlation_id=test_const.CORRELATION_ID_TRACE,
            from_header=True,
        )
        header_name, _ = correlation.response_header
        assert header_name == const.CORRELATION_ID_HEADER
