"""Owns the correlation ContextVar and its current/set/clear operations."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass

from mixin_logging.context.constants import correlation as const
from mixin_logging.context.correlation import correlation_objects as objs


@dataclass(frozen=True, slots=True)
class ContextVarClient:
    """Owns the correlation ContextVar and its current/set/clear operations."""

    correlation_ctx: ContextVar[objs.CorrelationContext]

    def current_id(self) -> str | None:
        """Return the current correlation id, or None if unset."""
        return self.correlation_ctx.get().correlation_id

    def set_id(self, value: str) -> None:
        """Set correlation id for the current context."""
        self.correlation_ctx.set(objs.CorrelationContext(value))

    def clear(self) -> None:
        """Reset the correlation context to unset."""
        self.correlation_ctx.set(objs.CorrelationContext(None))


_correlation_var: ContextVar[objs.CorrelationContext] = ContextVar(
    const.CORRELATION_CONTEXT_VAR_NAME,
)
_correlation_var.set(objs.CorrelationContext(None))

_client: ContextVarClient = ContextVarClient(_correlation_var)

get_correlation_id = _client.current_id
set_correlation_id = _client.set_id
clear_correlation_id = _client.clear
