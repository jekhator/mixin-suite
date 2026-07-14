"""Tests for FastAPI correlation object."""

from __future__ import annotations

# ruff: noqa: S101
import pytest

from mixin_logging.adapters.constants import fastapi as const
from mixin_logging.adapters.fastapi.fastapi_objects import (
    FastApiCorrelation,
)


class TestFastApiCorrelationFromHeaders:
    """Tests for FastApiCorrelation.from_headers() classmethod."""

    def test_from_headers_extracts_correlation_id_from_header(
        self,
        correlation_id_abc: str,
    ) -> None:
        """from_headers() extracts correlation ID from x-correlation-id header."""
        headers = {const.CORRELATION_ID_HEADER: correlation_id_abc}
        corr = FastApiCorrelation.from_headers(headers)
        assert corr.correlation_id == correlation_id_abc
        assert corr.from_header is True

    def test_from_headers_generates_uuid_when_header_missing(self) -> None:
        """from_headers() generates UUID when header is missing."""
        headers: dict[str, str] = {}
        corr = FastApiCorrelation.from_headers(headers)
        assert corr.correlation_id is not None
        assert len(corr.correlation_id) == 12
        assert corr.from_header is False

    def test_from_headers_rejects_unsafe_header_value(self) -> None:
        """from_headers() rejects correlation ID with unsafe characters."""
        unsafe_value = "abc\r\ndef"
        headers = {const.CORRELATION_ID_HEADER: unsafe_value}
        corr = FastApiCorrelation.from_headers(headers)
        assert corr.correlation_id != unsafe_value
        assert corr.from_header is False

    def test_from_headers_rejects_oversized_header_value(self) -> None:
        """from_headers() rejects correlation ID exceeding max length."""
        oversized = "x" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        headers = {const.CORRELATION_ID_HEADER: oversized}
        corr = FastApiCorrelation.from_headers(headers)
        assert corr.correlation_id != oversized
        assert corr.from_header is False

    def test_from_headers_rejects_empty_header_value(self) -> None:
        """from_headers() rejects empty correlation ID from header."""
        headers = {const.CORRELATION_ID_HEADER: ""}
        corr = FastApiCorrelation.from_headers(headers)
        assert corr.correlation_id != ""
        assert corr.from_header is False


class TestFastApiCorrelationIsSafe:
    """Tests for FastApiCorrelation._is_safe() staticmethod."""

    def test_is_safe_accepts_valid_id(self, correlation_id_abc: str) -> None:
        """_is_safe() accepts valid correlation IDs."""
        assert FastApiCorrelation._is_safe(correlation_id_abc) is True

    def test_is_safe_rejects_empty_string(self) -> None:
        """_is_safe() rejects empty strings."""
        assert FastApiCorrelation._is_safe("") is False

    def test_is_safe_rejects_oversized_id(self) -> None:
        """_is_safe() rejects IDs exceeding max length."""
        oversized = "x" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        assert FastApiCorrelation._is_safe(oversized) is False

    def test_is_safe_rejects_carriage_return(self) -> None:
        """_is_safe() rejects correlation IDs with carriage return."""
        assert FastApiCorrelation._is_safe("abc\r123") is False

    def test_is_safe_rejects_line_feed(self) -> None:
        """_is_safe() rejects correlation IDs with line feed."""
        assert FastApiCorrelation._is_safe("abc\n123") is False

    def test_is_safe_rejects_null_byte(self) -> None:
        """_is_safe() rejects correlation IDs with null byte."""
        assert FastApiCorrelation._is_safe("abc\x00123") is False


class TestFastApiCorrelationPostInit:
    """Tests for FastApiCorrelation.__post_init__() validation."""

    def test_post_init_raises_on_empty_correlation_id(self) -> None:
        """__post_init__() raises ValueError when correlation_id is empty."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_EMPTY):
            FastApiCorrelation(correlation_id="", from_header=False)

    def test_post_init_accepts_non_empty_correlation_id(
        self,
        correlation_id_abc: str,
    ) -> None:
        """__post_init__() accepts non-empty correlation_id."""
        corr = FastApiCorrelation(correlation_id=correlation_id_abc, from_header=True)
        assert corr.correlation_id == correlation_id_abc


class TestFastApiCorrelationResponseHeader:
    """Tests for FastApiCorrelation.response_header property."""

    def test_response_header_returns_tuple(self, correlation_id_custom: str) -> None:
        """response_header property returns (name, value) tuple."""
        corr = FastApiCorrelation(
            correlation_id=correlation_id_custom, from_header=False
        )
        header = corr.response_header
        assert isinstance(header, tuple)
        assert len(header) == 2

    def test_response_header_includes_correlation_id_value(
        self,
        correlation_id_custom: str,
    ) -> None:
        """response_header property includes the correlation ID value."""
        corr = FastApiCorrelation(
            correlation_id=correlation_id_custom, from_header=False
        )
        name, value = corr.response_header
        assert name == const.CORRELATION_ID_HEADER
        assert value == correlation_id_custom
