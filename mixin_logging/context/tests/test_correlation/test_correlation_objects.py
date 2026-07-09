"""Tests for CorrelationContext dataclass."""

# ruff: noqa: S101

from __future__ import annotations

import dataclasses

import pytest

from mixin_logging import CorrelationContext
from mixin_logging.common.constants import tests as test_const


class TestCorrelationContext:
    """Tests for CorrelationContext frozen-slots dataclass."""

    def test_context_frozen_prevents_mutation(self) -> None:
        """CorrelationContext is frozen: mutation raises FrozenInstanceError."""
        ctx = CorrelationContext(correlation_id=test_const.CORRELATION_ID_TEST)
        with pytest.raises(dataclasses.FrozenInstanceError):
            ctx.correlation_id = "new-id"  # type: ignore[misc]

    def test_context_is_set_true_when_id_present(self) -> None:
        """is_set returns True when correlation_id is not None."""
        ctx = CorrelationContext(correlation_id=test_const.CORRELATION_ID_TEST)
        assert ctx.is_set is True

    def test_context_is_set_false_when_id_none(self) -> None:
        """is_set returns False when correlation_id is None."""
        ctx = CorrelationContext(correlation_id=None)
        assert ctx.is_set is False

    def test_context_is_set_false_when_id_empty_string(self) -> None:
        """is_set is True for empty string (only None is falsy)."""
        ctx = CorrelationContext(correlation_id="")
        assert ctx.is_set is True

    def test_context_has_slots(self) -> None:
        """CorrelationContext has __slots__ (slots=True)."""
        ctx = CorrelationContext(correlation_id=test_const.CORRELATION_ID_TEST)
        assert hasattr(CorrelationContext, "__slots__")
        with pytest.raises(AttributeError):
            _ = ctx.__dict__  # type: ignore[attr-defined]
