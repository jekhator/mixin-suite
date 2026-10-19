"""Backoff jitter constants for retry operations."""

from typing import Final

JITTER_MIN_FACTOR: Final = 0.9
JITTER_MAX_FACTOR: Final = 1.1
