"""CorrelationIdInjector: stateless TraceConfig surface for aiohttp ClientSession."""

from __future__ import annotations

import aiohttp

from mixin_logging.adapters.aiohttp import aiohttp_objects as objs

__all__ = ["CorrelationIdInjector"]


class CorrelationIdInjector:
    """Stateless TraceConfig surface for aiohttp correlation-ID propagation."""

    @classmethod
    def trace_config(cls) -> aiohttp.TraceConfig:
        """Return a configured TraceConfig ready for ClientSession(trace_configs=[...])."""
        config = aiohttp.TraceConfig()
        config.on_request_start.append(cls._inject)
        return config

    @staticmethod
    async def _inject(
        session: aiohttp.ClientSession,
        trace_config_ctx: object,
        params: aiohttp.TraceRequestStartParams,
    ) -> None:
        """Inject X-Correlation-ID header into outbound request when context is populated."""
        correlation = objs.AiohttpCorrelation.from_context()
        if correlation is None:
            return
        name, value = correlation.header_tuple
        params.headers[name] = value
