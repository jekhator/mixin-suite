"""logging-mixin stdlib logging adapter: CorrelationLogFilter stamps correlation_id onto every LogRecord."""

from mixin_logging.adapters.stdlib.stdlib_client import (
    CorrelationLogFilter,
)

__all__ = [
    "CorrelationLogFilter",
]
