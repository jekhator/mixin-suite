"""CorrelationIdPoolManager: urllib3 PoolManager for correlation-ID propagation."""

from __future__ import annotations

from typing import Any

import urllib3

from mixin_logging.adapters.urllib3 import urllib3_objects as objs

__all__ = ["CorrelationIdPoolManager"]


class CorrelationIdPoolManager(urllib3.PoolManager):
    """PoolManager that injects correlation-ID header into outbound requests."""

    def urlopen(  # type: ignore[override]
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> urllib3.BaseHTTPResponse:
        """Inject X-Correlation-ID header from context before send."""
        correlation = objs.Urllib3Correlation.from_context()
        if correlation is not None:
            name, value = correlation.header_tuple
            headers = dict(kwargs.get("headers") or {})
            headers[name] = value
            kwargs["headers"] = headers
        return super().urlopen(method, url, **kwargs)
