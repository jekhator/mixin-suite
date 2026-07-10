"""logging-mixin urllib3 adapter: urllib3_objects (Urllib3Correlation) + urllib3_client (CorrelationIdPoolManager)."""

from mixin_logging.adapters.urllib3.urllib3_client import (
    CorrelationIdPoolManager,
)
from mixin_logging.adapters.urllib3.urllib3_objects import (
    Urllib3Correlation,
)

__all__ = [
    "CorrelationIdPoolManager",
    "Urllib3Correlation",
]
