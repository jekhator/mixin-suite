"""Tests for CorrelationContextInjector."""

from __future__ import annotations

from typing import Any

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import graphql as const
from mixin_logging.adapters.graphql import graphql_client
from mixin_logging.common.constants import tests as test_const


class TestCorrelationContextInjectorInject:
    """Tests for CorrelationContextInjector.inject() static method."""

    def test_inject_with_set_correlation_merges_context(self) -> None:
        """inject() merges correlation_id into resolver context dict when set."""
        set_correlation_id(test_const.CORRELATION_ID_ABC_123)
        context: dict[str, Any] = {"user_id": "42"}
        result = graphql_client.CorrelationContextInjector.inject(context)
        assert result[const.CONTEXT_KEY] == test_const.CORRELATION_ID_ABC_123
        assert result["user_id"] == "42"

    def test_inject_without_context_merges_none_correlation(self) -> None:
        """inject() merges None correlation_id when context is unset."""
        context: dict[str, Any] = {"user_id": "42"}
        result = graphql_client.CorrelationContextInjector.inject(context)
        assert result[const.CONTEXT_KEY] is None
        assert result["user_id"] == "42"

    def test_inject_returns_new_dict(self) -> None:
        """inject() returns a new dict without mutating the input."""
        set_correlation_id(test_const.CORRELATION_ID_TEST_ID_456)
        context: dict[str, Any] = {"user_id": "42"}
        original_context = context.copy()
        result = graphql_client.CorrelationContextInjector.inject(context)
        assert context == original_context
        assert result is not context

    def test_inject_with_multiple_keys_preserves_all(self) -> None:
        """inject() preserves all existing keys in the input dict."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        context: dict[str, Any] = {
            "user_id": "42",
            "request": "req",
            "info": "info_obj",
        }
        result = graphql_client.CorrelationContextInjector.inject(context)
        assert result[const.CONTEXT_KEY] == test_const.CORRELATION_ID_VALID_ID_123
        assert result["user_id"] == "42"
        assert result["request"] == "req"
        assert result["info"] == "info_obj"

    def test_inject_with_empty_context_dict(self) -> None:
        """inject() adds correlation_id to empty input dict."""
        set_correlation_id(test_const.CORRELATION_ID_HEX)
        context: dict[str, Any] = {}
        result = graphql_client.CorrelationContextInjector.inject(context)
        assert result == {const.CONTEXT_KEY: test_const.CORRELATION_ID_HEX}
