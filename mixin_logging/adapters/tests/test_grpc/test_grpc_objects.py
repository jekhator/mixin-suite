"""Tests for GRPCCorrelation dataclass."""

from __future__ import annotations

import pytest

from mixin_logging.adapters.constants import grpc as const
from mixin_logging.adapters.grpc import grpc_objects as grpc_objs
from mixin_logging.common.constants import tests as test_const


class TestGRPCCorrelationFromMetadata:
    """Tests for GRPCCorrelation.from_metadata() class method."""

    def test_from_metadata_with_present_safe_id(self) -> None:
        """from_metadata() extracts correlation ID and sets extracted=True."""
        metadata: grpc_objs.Metadata = (
            ("x-correlation-id", test_const.CORRELATION_ID_VALID_ID_123),
            ("other-key", "other-value"),
        )
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert correlation.correlation_id == test_const.CORRELATION_ID_VALID_ID_123
        assert correlation.extracted is True

    def test_from_metadata_without_id_generates_id(self) -> None:
        """from_metadata() generates 12-hex ID and sets extracted=False when key absent."""
        metadata: grpc_objs.Metadata = (("other-key", "other-value"),)
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_metadata_with_unsafe_carriage_return(self) -> None:
        """from_metadata() rejects ID with CR and generates new ID."""
        metadata: grpc_objs.Metadata = (
            ("x-correlation-id", "test-id\r-bad"),
            ("other-key", "other-value"),
        )
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_metadata_with_unsafe_newline(self) -> None:
        """from_metadata() rejects ID with LF and generates new ID."""
        metadata: grpc_objs.Metadata = (
            ("x-correlation-id", "test-id\n-bad"),
            ("other-key", "other-value"),
        )
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_metadata_with_unsafe_null_byte(self) -> None:
        """from_metadata() rejects ID with null byte and generates new ID."""
        metadata: grpc_objs.Metadata = (
            ("x-correlation-id", "test-id\x00-bad"),
            ("other-key", "other-value"),
        )
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_metadata_with_oversized_id(self) -> None:
        """from_metadata() rejects ID exceeding MAX_LENGTH and generates new ID."""
        oversized_id = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        metadata: grpc_objs.Metadata = (("x-correlation-id", oversized_id),)
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False

    def test_from_metadata_with_hex_id(self) -> None:
        """from_metadata() accepts hex correlation ID."""
        metadata: grpc_objs.Metadata = (
            ("x-correlation-id", test_const.CORRELATION_ID_HEX),
        )
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert correlation.correlation_id == test_const.CORRELATION_ID_HEX
        assert correlation.extracted is True

    def test_from_metadata_with_empty_metadata(self) -> None:
        """from_metadata() generates ID from empty metadata."""
        metadata: grpc_objs.Metadata = ()
        correlation = grpc_objs.GRPCCorrelation.from_metadata(metadata)
        assert len(correlation.correlation_id) == 12
        assert all(char in "0123456789abcdef" for char in correlation.correlation_id)
        assert correlation.extracted is False


class TestGRPCCorrelationIsSafe:
    """Tests for GRPCCorrelation._is_safe() static method."""

    def test_is_safe_rejects_empty_string(self) -> None:
        """_is_safe() returns False for empty string."""
        assert grpc_objs.GRPCCorrelation._is_safe("") is False

    def test_is_safe_with_valid_id(self) -> None:
        """_is_safe() returns True for valid alphanumeric ID."""
        assert (
            grpc_objs.GRPCCorrelation._is_safe(test_const.CORRELATION_ID_VALID_ID_123)
            is True
        )

    def test_is_safe_with_hex_id(self) -> None:
        """_is_safe() returns True for hex ID."""
        assert grpc_objs.GRPCCorrelation._is_safe(test_const.CORRELATION_ID_HEX) is True

    def test_is_safe_with_carriage_return(self) -> None:
        """_is_safe() returns False if value contains CR."""
        assert grpc_objs.GRPCCorrelation._is_safe("test\rid") is False

    def test_is_safe_with_newline(self) -> None:
        """_is_safe() returns False if value contains LF."""
        assert grpc_objs.GRPCCorrelation._is_safe("test\nid") is False

    def test_is_safe_with_null_byte(self) -> None:
        """_is_safe() returns False if value contains null byte."""
        assert grpc_objs.GRPCCorrelation._is_safe("test\x00id") is False

    def test_is_safe_with_oversized_value(self) -> None:
        """_is_safe() returns False if value exceeds MAX_LENGTH."""
        oversized = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        assert grpc_objs.GRPCCorrelation._is_safe(oversized) is False

    def test_is_safe_at_max_length_boundary(self) -> None:
        """_is_safe() returns True for value at exactly MAX_LENGTH."""
        at_max = "a" * const.CORRELATION_ID_MAX_LENGTH
        assert grpc_objs.GRPCCorrelation._is_safe(at_max) is True

    def test_is_safe_just_under_max_length(self) -> None:
        """_is_safe() returns True for value just under MAX_LENGTH."""
        just_under = "a" * (const.CORRELATION_ID_MAX_LENGTH - 1)
        assert grpc_objs.GRPCCorrelation._is_safe(just_under) is True


class TestGRPCCorrelationPostInit:
    """Tests for GRPCCorrelation.__post_init__() validation."""

    def test_post_init_raises_on_unsafe_correlation_id(self) -> None:
        """__post_init__() raises ValueError if correlation_id is unsafe."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            grpc_objs.GRPCCorrelation(
                correlation_id="test\r-bad",
                extracted=False,
            )

    def test_post_init_raises_on_empty_correlation_id(self) -> None:
        """__post_init__() raises ValueError if correlation_id is empty."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            grpc_objs.GRPCCorrelation(
                correlation_id="",
                extracted=False,
            )

    def test_post_init_raises_on_oversized_correlation_id(self) -> None:
        """__post_init__() raises ValueError if correlation_id exceeds MAX_LENGTH."""
        oversized = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            grpc_objs.GRPCCorrelation(
                correlation_id=oversized,
                extracted=False,
            )

    def test_post_init_accepts_safe_correlation_id(self) -> None:
        """__post_init__() accepts safe correlation_id."""
        correlation = grpc_objs.GRPCCorrelation(
            correlation_id=test_const.CORRELATION_ID_VALID_ID_123,
            extracted=True,
        )
        assert correlation.correlation_id == test_const.CORRELATION_ID_VALID_ID_123
