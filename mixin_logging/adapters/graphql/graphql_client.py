"""CorrelationContextInjector: GraphQL resolver-context entry surface."""

from __future__ import annotations

from typing import Any

from mixin_logging.adapters.graphql import graphql_objects as objs

__all__ = ["CorrelationContextInjector"]


class CorrelationContextInjector:
    """Stateless surface for injecting correlation_id into GraphQL resolver context."""

    @staticmethod
    def inject(context: dict[str, Any]) -> dict[str, Any]:
        """Merge correlation_id into an existing resolver context dict; return new dict."""
        correlation = objs.GraphQLCorrelation.from_context()
        return {**context, **correlation.as_context_dict()}
