"""Tests for BotocoreCorrelation dataclass."""

from __future__ import annotations

import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.botocore import botocore_objects as objs
from mixin_logging.adapters.constants import botocore as const
from mixin_logging.common.constants import tests as test_const


class TestBotocoreCorrelationFromContext:
    """Tests for BotocoreCorrelation.from_context() class method."""

    def test_from_context_with_set_correlation_returns_instance(self) -> None:
        """from_context() returns instance when correlation_id is set and safe."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        correlation = objs.BotocoreCorrelation.from_context()
        assert correlation is not None
        assert correlation.correlation_id == test_const.CORRELATION_ID_VALID_ID_123

    def test_from_context_with_unset_context_returns_none(self) -> None:
        """from_context() returns None when context is unset."""
        correlation = objs.BotocoreCorrelation.from_context()
        assert correlation is None

    @pytest.mark.parametrize("unsafe_char", ["\r", "\n", "\0"])
    def test_from_context_with_unsafe_chars_returns_none(
        self,
        unsafe_char: str,
    ) -> None:
        """from_context() returns None when correlation_id contains unsafe chars."""
        unsafe_id = f"id-with-{unsafe_char}-char"
        set_correlation_id(unsafe_id)
        correlation = objs.BotocoreCorrelation.from_context()
        assert correlation is None

    def test_from_context_with_overlong_value_returns_none(self) -> None:
        """from_context() returns None when correlation_id exceeds length cap."""
        overlong_id = "a" * 129
        set_correlation_id(overlong_id)
        correlation = objs.BotocoreCorrelation.from_context()
        assert correlation is None


class TestBotocoreCorrelationConstruction:
    """Tests for BotocoreCorrelation construction and validation."""

    def test_construct_with_unsafe_chars_raises_value_error(self) -> None:
        """BotocoreCorrelation constructor raises ValueError for unsafe chars."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.BotocoreCorrelation(correlation_id="abc\r\n")

    def test_construct_with_empty_string_raises_value_error(self) -> None:
        """BotocoreCorrelation constructor raises ValueError for empty string."""
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.BotocoreCorrelation(correlation_id="")

    def test_construct_with_overlong_raises_value_error(self) -> None:
        """BotocoreCorrelation constructor raises ValueError for overlong correlation_id."""
        overlong_id = "a" * 129
        with pytest.raises(ValueError, match=const.ERR_CORRELATION_ID_UNSAFE):
            objs.BotocoreCorrelation(correlation_id=overlong_id)


class TestBotocoreCorrelationHeaderTuple:
    """Tests for BotocoreCorrelation.header_tuple property."""

    def test_header_tuple_returns_canonical_pair(self) -> None:
        """header_tuple returns (header_name, correlation_id) pair."""
        correlation = objs.BotocoreCorrelation(
            correlation_id=test_const.CORRELATION_ID_XYZ
        )
        name, value = correlation.header_tuple
        assert name == const.CORRELATION_ID_HEADER
        assert value == test_const.CORRELATION_ID_XYZ


class TestBotocoreCorrelationIsSafe:
    """Tests for BotocoreCorrelation._is_safe() static method."""

    def test_is_safe_with_valid_value_returns_true(self) -> None:
        """_is_safe() returns True for valid correlation_id."""
        assert (
            objs.BotocoreCorrelation._is_safe(test_const.CORRELATION_ID_VALID_ID_123)
            is True
        )

    def test_is_safe_with_empty_returns_false(self) -> None:
        """_is_safe() returns False for empty string."""
        assert objs.BotocoreCorrelation._is_safe("") is False

    def test_is_safe_with_overlong_returns_false(self) -> None:
        """_is_safe() returns False for string exceeding 128 chars."""
        overlong = "a" * 129
        assert objs.BotocoreCorrelation._is_safe(overlong) is False

    @pytest.mark.parametrize("unsafe_char", ["\r", "\n", "\0"])
    def test_is_safe_with_unsafe_chars_returns_false(self, unsafe_char: str) -> None:
        """_is_safe() returns False for strings containing unsafe chars."""
        unsafe_value = f"test{unsafe_char}value"
        assert objs.BotocoreCorrelation._is_safe(unsafe_value) is False
