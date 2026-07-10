"""Tests for CloudCorrelation dataclass validation and value-object semantics."""

from __future__ import annotations

import pytest

from mixin_logging.adapters.cloud import cloud_objects as objs
from mixin_logging.adapters.constants import cloud as const


class TestCloudCorrelationConstruction:
    """Tests for CloudCorrelation construction and validation."""

    def test_construct_with_safe_id_succeeds(self) -> None:
        """CloudCorrelation constructor succeeds with safe correlation_id."""
        correlation = objs.CloudCorrelation(
            correlation_id="safe-id-123",
            extracted=True,
        )
        assert correlation.correlation_id == "safe-id-123"
        assert correlation.extracted is True

    def test_construct_with_unsafe_cr_raises_value_error(self) -> None:
        """CloudCorrelation constructor raises ValueError for carriage return."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CloudCorrelation(correlation_id="bad\rvalue", extracted=True)

    def test_construct_with_unsafe_lf_raises_value_error(self) -> None:
        """CloudCorrelation constructor raises ValueError for line feed."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CloudCorrelation(correlation_id="bad\nvalue", extracted=True)

    def test_construct_with_unsafe_null_raises_value_error(self) -> None:
        """CloudCorrelation constructor raises ValueError for null byte."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CloudCorrelation(correlation_id="bad\x00value", extracted=True)

    def test_construct_with_empty_string_raises_value_error(self) -> None:
        """CloudCorrelation constructor raises ValueError for empty string."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CloudCorrelation(correlation_id="", extracted=True)

    def test_construct_with_overlong_raises_value_error(self) -> None:
        """CloudCorrelation constructor raises ValueError for exceeding length cap."""
        overlong_id = "a" * 129
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CloudCorrelation(correlation_id=overlong_id, extracted=True)


class TestCloudCorrelationIsSafe:
    """Tests for CloudCorrelation._is_safe() static method."""

    def test_is_safe_with_valid_value_returns_true(self) -> None:
        """_is_safe() returns True for valid correlation_id."""
        assert objs.CloudCorrelation._is_safe("valid-id-123") is True

    def test_is_safe_with_empty_returns_false(self) -> None:
        """_is_safe() returns False for empty string."""
        assert objs.CloudCorrelation._is_safe("") is False

    def test_is_safe_with_max_length_returns_true(self) -> None:
        """_is_safe() returns True for exactly max-length value."""
        max_id = "a" * const.CORRELATION_ID_MAX_LENGTH
        assert objs.CloudCorrelation._is_safe(max_id) is True

    def test_is_safe_with_overlong_returns_false(self) -> None:
        """_is_safe() returns False for exceeding max length."""
        overlong_id = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        assert objs.CloudCorrelation._is_safe(overlong_id) is False

    def test_is_safe_with_carriage_return_returns_false(self) -> None:
        """_is_safe() returns False for carriage return character."""
        assert objs.CloudCorrelation._is_safe("test\rvalue") is False

    def test_is_safe_with_line_feed_returns_false(self) -> None:
        """_is_safe() returns False for line feed character."""
        assert objs.CloudCorrelation._is_safe("test\nvalue") is False

    def test_is_safe_with_null_byte_returns_false(self) -> None:
        """_is_safe() returns False for null byte character."""
        assert objs.CloudCorrelation._is_safe("test\x00value") is False

    def test_is_safe_with_alphanumeric_returns_true(self) -> None:
        """_is_safe() returns True for alphanumeric characters."""
        assert objs.CloudCorrelation._is_safe("abc123XYZ") is True

    def test_is_safe_with_special_characters_returns_true(self) -> None:
        """_is_safe() returns True for safe special characters."""
        assert objs.CloudCorrelation._is_safe("id-_./~:") is True

    def test_is_safe_with_generated_length_returns_true(self) -> None:
        """_is_safe() returns True for generated ID length."""
        generated_id = "a" * const.GENERATED_ID_LENGTH
        assert objs.CloudCorrelation._is_safe(generated_id) is True
