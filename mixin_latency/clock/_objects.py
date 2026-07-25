"""Latency measurement data structure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LatencyMeasurement:
    """Measured elapsed time in milliseconds.

    Attributes:
        duration_ms: Elapsed duration in milliseconds, rounded to
            LATENCY_ROUNDING_DECIMALS decimal places.
    """

    duration_ms: float
