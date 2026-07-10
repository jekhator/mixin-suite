"""Tests for GraphQLCorrelation dataclass."""

from __future__ import annotations

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import graphql as const
from mixin_logging.adapters.graphql import graphql_objects as objs
from mixin_logging.common.constants import tests as test_const


class TestGraphQLCorrelationFromContext:
    """Tests for GraphQLCorrelation.from_context() class method."""

    def test_from_context_with_set_correlation_returns_instance(self) -> None:
        """from_context() returns instance when correlation_id is set."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        correlation = objs.GraphQLCorrelation.from_context()
        assert correlation is not None
        assert correlation.correlation_id == test_const.CORRELATION_ID_VALID_ID_123

    def test_from_context_with_unset_context_returns_none_correlation_id(self) -> None:
        """from_context() returns instance with None correlation_id when context is unset."""
        correlation = objs.GraphQLCorrelation.from_context()
        assert correlation is not None
        assert correlation.correlation_id is None


class TestGraphQLCorrelationAsContextDict:
    """Tests for GraphQLCorrelation.as_context_dict() method."""

    def test_as_context_dict_with_set_correlation_returns_dict(self) -> None:
        """as_context_dict() returns dict with correlation_id key when set."""
        set_correlation_id(test_const.CORRELATION_ID_HEX)
        correlation = objs.GraphQLCorrelation.from_context()
        result = correlation.as_context_dict()
        assert result == {const.CONTEXT_KEY: test_const.CORRELATION_ID_HEX}

    def test_as_context_dict_with_unset_correlation_returns_dict_with_none(
        self,
    ) -> None:
        """as_context_dict() returns dict with None value when correlation_id is unset."""
        correlation = objs.GraphQLCorrelation.from_context()
        result = correlation.as_context_dict()
        assert result == {const.CONTEXT_KEY: None}
