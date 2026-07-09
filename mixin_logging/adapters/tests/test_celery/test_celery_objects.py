"""Tests for CeleryCorrelation dataclass."""

from __future__ import annotations

import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.celery import celery_objects as objs
from mixin_logging.adapters.constants import celery as const
from mixin_logging.common.constants import tests as test_const


class TestCeleryCorrelationFromContext:
    """Tests for CeleryCorrelation.from_context() class method."""

    def test_from_context_with_set_correlation_returns_instance(self) -> None:
        """from_context() returns instance when correlation_id is set and safe."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        correlation = objs.CeleryCorrelation.from_context()
        assert correlation is not None
        assert correlation.correlation_id == test_const.CORRELATION_ID_VALID_ID_123

    def test_from_context_with_unset_context_returns_none(self) -> None:
        """from_context() returns None when context is unset."""
        correlation = objs.CeleryCorrelation.from_context()
        assert correlation is None

    @pytest.mark.parametrize("unsafe_char", ["\r", "\n", "\0"])
    def test_from_context_with_unsafe_chars_returns_none(
        self,
        unsafe_char: str,
    ) -> None:
        """from_context() returns None when correlation_id contains unsafe chars."""
        unsafe_id = f"id-with-{unsafe_char}-char"
        set_correlation_id(unsafe_id)
        correlation = objs.CeleryCorrelation.from_context()
        assert correlation is None

    def test_from_context_with_overlong_value_returns_none(self) -> None:
        """from_context() returns None when correlation_id exceeds length cap."""
        overlong_id = "a" * 129
        set_correlation_id(overlong_id)
        correlation = objs.CeleryCorrelation.from_context()
        assert correlation is None


class TestCeleryCorrelationConstruction:
    """Tests for CeleryCorrelation construction and validation."""

    def test_construct_with_unsafe_chars_raises_value_error(self) -> None:
        """CeleryCorrelation constructor raises ValueError for unsafe chars."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CeleryCorrelation(correlation_id="abc\r\n")

    def test_construct_with_empty_string_raises_value_error(self) -> None:
        """CeleryCorrelation constructor raises ValueError for empty string."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CeleryCorrelation(correlation_id="")

    def test_construct_with_overlong_raises_value_error(self) -> None:
        """CeleryCorrelation constructor raises ValueError for overlong correlation_id."""
        overlong_id = "a" * 129
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CeleryCorrelation(correlation_id=overlong_id)

    def test_construct_with_null_byte_raises_value_error(self) -> None:
        """CeleryCorrelation constructor raises ValueError for null byte."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.CeleryCorrelation(correlation_id="abc\x00def")


class TestCeleryCorrelationHeaderPair:
    """Tests for CeleryCorrelation.header_pair property."""

    def test_header_pair_returns_canonical_pair(self) -> None:
        """header_pair returns (header_name, correlation_id) pair."""
        correlation = objs.CeleryCorrelation(
            correlation_id=test_const.CORRELATION_ID_XYZ
        )
        name, value = correlation.header_pair
        assert name == const.CORRELATION_ID_HEADER
        assert value == test_const.CORRELATION_ID_XYZ


class TestCeleryCorrelationIsSafe:
    """Tests for CeleryCorrelation._is_safe() static method."""

    def test_is_safe_with_valid_value_returns_true(self) -> None:
        """_is_safe() returns True for valid correlation_id."""
        assert (
            objs.CeleryCorrelation._is_safe(test_const.CORRELATION_ID_VALID_ID_123)
            is True
        )

    def test_is_safe_with_empty_returns_false(self) -> None:
        """_is_safe() returns False for empty string."""
        assert objs.CeleryCorrelation._is_safe("") is False

    def test_is_safe_with_exactly_max_length_returns_true(self) -> None:
        """_is_safe() returns True for string at exactly 128 chars."""
        exactly_max = "a" * const.CORRELATION_ID_MAX_LENGTH
        assert objs.CeleryCorrelation._is_safe(exactly_max) is True

    def test_is_safe_with_one_over_max_length_returns_false(self) -> None:
        """_is_safe() returns False for string exceeding 128 chars."""
        over_max = "a" * (const.CORRELATION_ID_MAX_LENGTH + 1)
        assert objs.CeleryCorrelation._is_safe(over_max) is False

    @pytest.mark.parametrize("unsafe_char", ["\r", "\n", "\0"])
    def test_is_safe_with_unsafe_chars_returns_false(self, unsafe_char: str) -> None:
        """_is_safe() returns False for strings containing unsafe chars."""
        unsafe_value = f"test{unsafe_char}value"
        assert objs.CeleryCorrelation._is_safe(unsafe_value) is False

    def test_is_safe_with_clean_value_returns_true(self) -> None:
        """_is_safe() returns True for clean alphanumeric and symbol value."""
        clean_value = "trace-id-123-abc-xyz"
        assert objs.CeleryCorrelation._is_safe(clean_value) is True
