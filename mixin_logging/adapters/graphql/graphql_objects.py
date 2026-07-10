"""GraphQLCorrelation value object for GraphQL adapter."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Self

from mixin_logging import get_correlation_id
from mixin_logging.adapters.constants import graphql as const

__all__ = ["GraphQLCorrelation"]


@dataclass(frozen=True, slots=True)
class GraphQLCorrelation:
    """Value object exposing the current correlation_id for resolver context injection."""

    correlation_id: str | None

    @classmethod
    def from_context(cls) -> Self:
        """Read correlation_id from ContextVar (set upstream by ASGI/WSGI); may be None."""
        return cls(correlation_id=get_correlation_id())

    def as_context_dict(self) -> dict[str, str | None]:
        """Return a dict suitable for merging into resolver info.context."""
        return {const.CONTEXT_KEY: self.correlation_id}
