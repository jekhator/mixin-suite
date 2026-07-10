"""CloudSetup: cloud adapter inbound entry surface for correlation-ID setup."""

from __future__ import annotations

from typing import Any

from mixin_logging import set_correlation_id
from mixin_logging.adapters.cloud import cloud_objects as objs


class CloudSetup:
    """Entry surface for resolving correlation-ID from cloud events."""

    @staticmethod
    def setup_correlation_id(
        event: dict[str, Any],
        context: Any = None,  # noqa: ARG004, ANN401
    ) -> str:
        """Extract and set the correlation ID from a cloud event."""
        correlation = objs.CloudCorrelation.from_event(event)
        set_correlation_id(correlation.correlation_id)
        return correlation.correlation_id
