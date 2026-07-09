"""logging-mixin aiohttp adapter: aiohttp_objects (AiohttpCorrelation) + aiohttp_client (CorrelationIdInjector)."""

from mixin_logging.adapters.aiohttp.aiohttp_client import (
    CorrelationIdInjector,
)
from mixin_logging.adapters.aiohttp.aiohttp_objects import (
    AiohttpCorrelation,
)

__all__ = [
    "AiohttpCorrelation",
    "CorrelationIdInjector",
]
