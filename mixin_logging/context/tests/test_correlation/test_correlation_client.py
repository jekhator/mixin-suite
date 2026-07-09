"""Tests for context-var helpers."""

# ruff: noqa: S101

from __future__ import annotations

from mixin_logging import (
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from mixin_logging.common.constants import tests as test_const


class TestGetCorrelationId:
    """Tests for get_correlation_id() helper."""

    def test_get_correlation_id_returns_none_by_default(self) -> None:
        """get_correlation_id() returns None when no value is set."""
        assert get_correlation_id() is None

    def test_get_correlation_id_returns_set_value(self) -> None:
        """get_correlation_id() returns the value set by set_correlation_id()."""
        test_id = test_const.CORRELATION_ID_TRACE
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id

    def test_get_correlation_id_returns_typed_str_or_none(self) -> None:
        """get_correlation_id() return type is str | None."""
        result = get_correlation_id()
        assert isinstance(result, (type(None), str))

        set_correlation_id(test_const.CORRELATION_ID_ABC)
        result = get_correlation_id()
        assert isinstance(result, str)


class TestSetCorrelationId:
    """Tests for set_correlation_id(value) helper."""

    def test_set_correlation_id_with_string(self) -> None:
        """set_correlation_id(str) stores the value."""
        test_id = test_const.CORRELATION_ID_CUSTOM
        set_correlation_id(test_id)
        assert get_correlation_id() == test_id

    def test_set_correlation_id_overwrites_previous_then_clear(self) -> None:
        """set_correlation_id() overwrites; use clear_correlation_id() to reset."""
        set_correlation_id(test_const.CORRELATION_ID_SOMETHING)
        assert get_correlation_id() == test_const.CORRELATION_ID_SOMETHING
        clear_correlation_id()
        assert get_correlation_id() is None

    def test_set_correlation_id_overwrites_previous(self) -> None:
        """set_correlation_id() overwrites any previous value."""
        set_correlation_id(test_const.CORRELATION_ID_FIRST)
        assert get_correlation_id() == test_const.CORRELATION_ID_FIRST

        set_correlation_id(test_const.CORRELATION_ID_SECOND)
        assert get_correlation_id() == test_const.CORRELATION_ID_SECOND

    def test_set_correlation_id_accepts_str(self) -> None:
        """set_correlation_id() accepts str; use clear_correlation_id() for reset."""
        set_correlation_id(test_const.CORRELATION_ID_ABC)
        assert get_correlation_id() == test_const.CORRELATION_ID_ABC

        clear_correlation_id()
        assert get_correlation_id() is None


class TestClearCorrelationId:
    """Tests for clear_correlation_id() helper."""

    def test_clear_correlation_id_resets_to_none(self) -> None:
        """clear_correlation_id() resets the context to None."""
        set_correlation_id(test_const.CORRELATION_ID_SOME)
        assert get_correlation_id() == test_const.CORRELATION_ID_SOME

        clear_correlation_id()
        assert get_correlation_id() is None

    def test_clear_correlation_id_idempotent(self) -> None:
        """clear_correlation_id() is idempotent: multiple calls are safe."""
        set_correlation_id(test_const.CORRELATION_ID_ID1)
        clear_correlation_id()
        clear_correlation_id()
        assert get_correlation_id() is None


class TestContextVarBehavior:
    """Tests for ContextVar async/task isolation (context-local behavior)."""

    def test_context_is_isolated_per_call_to_set(self) -> None:
        """Each set_correlation_id() call creates a new context snapshot."""
        set_correlation_id(test_const.CORRELATION_ID_ID1)
        id1 = get_correlation_id()

        set_correlation_id(test_const.CORRELATION_ID_ID2)
        id2 = get_correlation_id()

        assert id1 == test_const.CORRELATION_ID_ID1
        assert id2 == test_const.CORRELATION_ID_ID2
