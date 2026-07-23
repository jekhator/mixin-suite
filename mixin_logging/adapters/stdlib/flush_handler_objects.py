"""Config and envelope objects for FlushOnWarningHandler."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Final

# Error message constants
ERR_TARGET_HANDLER_REQUIRED: Final = "target_handler must not be None"
ERR_FLUSH_LEVEL_INVALID: Final = "flush_level must be >= logging.WARNING"
ERR_TTL_POSITIVE: Final = "ttl_seconds must be > 0"
ERR_CAPACITY_POSITIVE: Final = "capacity must be > 0"
ERR_MAX_CORRELATIONS_POSITIVE: Final = "max_correlations must be > 0"

# Default configuration constants
DEFAULT_FLUSH_LEVEL: Final = logging.WARNING
DEFAULT_TTL_SECONDS: Final = 300
DEFAULT_CAPACITY: Final = 1000
DEFAULT_MAX_CORRELATIONS: Final = 100


@dataclass(frozen=True, slots=True)
class FlushOnWarningConfig:
    """Configuration for FlushOnWarningHandler."""

    target_handler: logging.Handler
    flush_level: int = DEFAULT_FLUSH_LEVEL
    ttl_seconds: float = DEFAULT_TTL_SECONDS
    capacity: int = DEFAULT_CAPACITY
    max_correlations: int = DEFAULT_MAX_CORRELATIONS

    def __post_init__(self) -> None:
        """Validate all config values; raise on invariant breach."""
        if self.target_handler is None:
            raise ValueError(ERR_TARGET_HANDLER_REQUIRED)
        if self.flush_level < logging.WARNING:
            raise ValueError(ERR_FLUSH_LEVEL_INVALID)
        if self.ttl_seconds <= 0:
            raise ValueError(ERR_TTL_POSITIVE)
        if self.capacity <= 0:
            raise ValueError(ERR_CAPACITY_POSITIVE)
        if self.max_correlations <= 0:
            raise ValueError(ERR_MAX_CORRELATIONS_POSITIVE)
