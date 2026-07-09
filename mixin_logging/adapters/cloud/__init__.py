"""Cloud adapter: inbound correlation-ID extraction from AWS events."""

from mixin_logging.adapters.cloud.cloud_client import CloudSetup
from mixin_logging.adapters.cloud.cloud_objects import (
    CloudCorrelation,
)

__all__ = [
    "CloudCorrelation",
    "CloudSetup",
]
