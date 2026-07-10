"""CorrelationIdInjector: botocore event-hook for correlation-ID injection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from mixin_logging.adapters.botocore import botocore_objects as objs
from mixin_logging.adapters.constants import botocore as const


@dataclass(frozen=True, slots=True)
class CorrelationIdInjector:
    """Stateless event-hook surface for botocore correlation-ID propagation."""

    @classmethod
    def register_on_session(cls, session: Any) -> None:
        """Register the correlation-ID injection handler on a botocore session."""
        session.register(const.BEFORE_SIGN_EVENT, cls.inject_before_sign)

    @classmethod
    def register_on_client(cls, client: Any) -> None:
        """Register the correlation-ID injection handler on a boto3 client."""
        client.meta.events.register(const.BEFORE_SIGN_EVENT, cls.inject_before_sign)

    @classmethod
    def inject_before_sign(cls, request: Any, **kwargs: Any) -> None:
        """Inject the correlation-ID header into the request before SigV4 signing."""
        correlation = objs.BotocoreCorrelation.from_context()
        if correlation is None:
            return
        name, value = correlation.header_tuple
        if name in request.headers:
            request.headers.replace_header(name, value)
        else:
            request.headers[name] = value
