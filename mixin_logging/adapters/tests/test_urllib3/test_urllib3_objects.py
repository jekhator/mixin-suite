"""Tests for Urllib3Correlation dataclass."""

from __future__ import annotations

import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import urllib3 as const
from mixin_logging.adapters.urllib3 import urllib3_objects as objs
from mixin_logging.common.constants import tests as test_const


class TestUrllib3CorrelationFromContext:
    """Tests for Urllib3Correlation.from_context() class method."""

    def test_from_context_with_set_correlation_returns_instance(self) -> None:
        """from_context() returns instance when correlation_id is set and safe."""
        set_correlation_id(test_const.HTTPX_CORR_ID_SAFE)
        correlation = objs.Urllib3Correlation.from_context()
        assert correlation is not None
        assert correlation.correlation_id == test_const.HTTPX_CORR_ID_SAFE

    def test_from_context_with_unset_context_returns_none(self) -> None:
        """from_context() returns None when context is unset."""
        correlation = objs.Urllib3Correlation.from_context()
        assert correlation is None

    @pytest.mark.parametrize("unsafe_char", ["\r", "\n", "\0"])
    def test_from_context_with_unsafe_chars_returns_none(
        self,
        unsafe_char: str,
    ) -> None:
        """from_context() returns None when correlation_id contains unsafe chars."""
        unsafe_id = f"id-with-{unsafe_char}-char"
        set_correlation_id(unsafe_id)
        correlation = objs.Urllib3Correlation.from_context()
        assert correlation is None

    def test_from_context_with_overlong_value_returns_none(self) -> None:
        """from_context() returns None when correlation_id exceeds length cap."""
        overlong_id = "a" * 129
        set_correlation_id(overlong_id)
        correlation = objs.Urllib3Correlation.from_context()
        assert correlation is None


class TestUrllib3CorrelationConstruction:
    """Tests for Urllib3Correlation construction and validation."""

    def test_construct_with_unsafe_chars_raises_value_error(self) -> None:
        """Urllib3Correlation constructor raises ValueError for unsafe chars."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.Urllib3Correlation(correlation_id="abc\r\n")

    def test_construct_with_empty_string_raises_value_error(self) -> None:
        """Urllib3Correlation constructor raises ValueError for empty string."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.Urllib3Correlation(correlation_id="")

    def test_construct_with_overlong_raises_value_error(self) -> None:
        """Urllib3Correlation constructor raises ValueError for overlong correlation_id."""
        overlong_id = "a" * 129
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.Urllib3Correlation(correlation_id=overlong_id)

    def test_construct_with_exactly_max_length_succeeds(self) -> None:
        """Urllib3Correlation constructor succeeds with exactly 128 chars."""
        exact_max_id = "a" * const.CORRELATION_ID_MAX_LENGTH
        correlation = objs.Urllib3Correlation(correlation_id=exact_max_id)
        assert correlation.correlation_id == exact_max_id


class TestUrllib3CorrelationHeaderTuple:
    """Tests for Urllib3Correlation.header_tuple property."""

    def test_header_tuple_returns_canonical_pair(self) -> None:
        """header_tuple returns (header_name, correlation_id) pair."""
        test_id = test_const.HTTPX_CORR_ID_XYZ
        correlation = objs.Urllib3Correlation(correlation_id=test_id)
        name, value = correlation.header_tuple
        assert name == const.CORRELATION_ID_HEADER
        assert value == test_id


class TestUrllib3CorrelationIsSafe:
    """Tests for Urllib3Correlation._is_safe() static method."""

    def test_is_safe_with_valid_value_returns_true(self) -> None:
        """_is_safe() returns True for valid correlation_id."""
        assert objs.Urllib3Correlation._is_safe(test_const.HTTPX_CORR_ID_SAFE) is True

    def test_is_safe_with_empty_returns_false(self) -> None:
        """_is_safe() returns False for empty string."""
        assert objs.Urllib3Correlation._is_safe("") is False

    def test_is_safe_with_overlong_returns_false(self) -> None:
        """_is_safe() returns False for string exceeding 128 chars."""
        overlong = "a" * 129
        assert objs.Urllib3Correlation._is_safe(overlong) is False

    def test_is_safe_with_exactly_max_length_returns_true(self) -> None:
        """_is_safe() returns True for string of exactly 128 chars."""
        exact_max = "x" * const.CORRELATION_ID_MAX_LENGTH
        assert objs.Urllib3Correlation._is_safe(exact_max) is True

    @pytest.mark.parametrize("unsafe_char", ["\r", "\n", "\0"])
    def test_is_safe_with_unsafe_chars_returns_false(self, unsafe_char: str) -> None:
        """_is_safe() returns False for strings containing unsafe chars."""
        unsafe_value = f"test{unsafe_char}value"
        assert objs.Urllib3Correlation._is_safe(unsafe_value) is False
