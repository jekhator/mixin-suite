"""Config and envelope objects for FlushOnWarningHandler."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mixin_logging.adapters.constants import stdlib as const


@dataclass(frozen=True, slots=True)
class FlushOnWarningConfig:
    """Configuration for FlushOnWarningHandler."""

    target_handler: logging.Handler
    flush_level: int = const.DEFAULT_FLUSH_LEVEL
    ttl_seconds: float = const.DEFAULT_TTL_SECONDS
    capacity: int = const.DEFAULT_CAPACITY
    max_correlations: int = const.DEFAULT_MAX_CORRELATIONS

    def __post_init__(self) -> None:
        """Validate all config values; raise on invariant breach."""
        if self.target_handler is None:
            raise ValueError(const.ERR_TARGET_HANDLER_REQUIRED)
        if self.flush_level < logging.WARNING:
            raise ValueError(const.ERR_FLUSH_LEVEL_INVALID)
        if self.ttl_seconds <= 0:
            raise ValueError(const.ERR_TTL_POSITIVE)
        if self.capacity <= 0:
            raise ValueError(const.ERR_CAPACITY_POSITIVE)
        if self.max_correlations <= 0:
            raise ValueError(const.ERR_MAX_CORRELATIONS_POSITIVE)
