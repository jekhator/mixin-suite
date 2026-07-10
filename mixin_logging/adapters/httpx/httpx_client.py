"""CorrelationIdInjector: stateless event-hook surface for httpx Client/AsyncClient."""

from __future__ import annotations

from dataclasses import dataclass

import httpx as httpx_lib

from mixin_logging.adapters.constants import httpx as const
from mixin_logging.adapters.httpx import httpx_objects as objs

__all__ = ["CorrelationIdInjector"]


@dataclass(frozen=True, slots=True)
class CorrelationIdInjector:
    """Stateless event-hook surface for httpx Client/AsyncClient correlation-ID propagation."""

    @classmethod
    def event_hooks(cls) -> objs.EventHooks:
        """Return event_hooks dict ready for httpx.Client / AsyncClient registration."""
        return {const.EVENT_HOOK_REQUEST: [cls.inject_sync, cls.inject_async]}

    @classmethod
    def inject_sync(cls, request: httpx_lib.Request) -> None:
        """Inject X-Correlation-ID header into outbound request when context is populated."""
        correlation = objs.HttpxCorrelation.from_context()
        if correlation is None:
            return
        name, value = correlation.header_tuple
        request.headers[name] = value

    @classmethod
    async def inject_async(cls, request: httpx_lib.Request) -> None:
        """Async wrapper of inject_sync for httpx.AsyncClient event-hook registration."""
        cls.inject_sync(request)
