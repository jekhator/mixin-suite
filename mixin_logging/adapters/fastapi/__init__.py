"""logging-mixin FastAPI adapter: fastapi_objects (value objects) + fastapi_client (middleware + dependency)."""

from mixin_logging.adapters.fastapi.fastapi_client import (
    CorrelationIdMiddleware,
    get_correlation_id_dependency,
)
from mixin_logging.adapters.fastapi.fastapi_objects import (
    FastApiCorrelation,
)

__all__ = [
    "CorrelationIdMiddleware",
    "FastApiCorrelation",
    "get_correlation_id_dependency",
]
