"""RetryContainer: retry parameters derived from a decorated operation."""

from __future__ import annotations

from dataclasses import dataclass

from mixin_retry.decorators.constants import decorators as const


@dataclass(frozen=True, slots=True)
class RetryContainer:
    """Retry parameters for one decorated operation."""

    max_attempts: int
    base_delay_s: float
    max_delay_s: float
    jitter: bool

    def __post_init__(self) -> None:
        """Validate all parameters are in valid ranges."""
        if self.max_attempts < 1:
            raise ValueError(const.ERROR_MSG_MAX_ATTEMPTS_INVALID)
