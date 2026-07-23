"""Retry policy configuration for exponential backoff."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Final

ERR_RETRY_MAX_ATTEMPTS: Final = "max_attempts must be >= 1"
ERR_RETRY_BACKOFF_BASE: Final = "backoff_base_seconds must be > 0"
ERR_RETRY_BACKOFF_MULTIPLIER: Final = "backoff_multiplier must be > 0"
ERR_RETRY_BACKOFF_MAX: Final = "backoff_max_seconds must be > 0"


@dataclass(frozen=True, slots=True)
class RetryPolicy:
    """Exponential backoff retry strategy with jitter and predicates.

    Attributes:
        max_attempts: Maximum number of retry attempts (>= 1).
        backoff_base_seconds: Base delay for first retry.
        backoff_multiplier: Multiplier for exponential backoff (>= 1).
        backoff_max_seconds: Maximum backoff delay.
        jitter: If True, add ±10% random jitter to each backoff.
        should_retry: Predicate function to determine if exception is retryable.
            If provided, takes precedence over retry_on. Unwraps __cause__
            to find the root exception in a chain.
        retry_on: Tuple of exception types to retry on (fallback if
            should_retry is None).
    """

    max_attempts: int
    backoff_base_seconds: float
    backoff_multiplier: float
    backoff_max_seconds: float
    jitter: bool
    should_retry: Callable[[BaseException], bool] | None = None
    retry_on: tuple[type[BaseException], ...] = ()

    def __post_init__(self) -> None:
        """Validate policy constraints."""
        if self.max_attempts < 1:
            raise ValueError(ERR_RETRY_MAX_ATTEMPTS)
        if self.backoff_base_seconds <= 0:
            raise ValueError(ERR_RETRY_BACKOFF_BASE)
        if self.backoff_multiplier <= 0:
            raise ValueError(ERR_RETRY_BACKOFF_MULTIPLIER)
        if self.backoff_max_seconds <= 0:
            raise ValueError(ERR_RETRY_BACKOFF_MAX)
