"""Latency clock for measuring elapsed time."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager

from mixin_latency.clock._objects import LatencyMeasurement
from mixin_latency.common.constants.clock import LATENCY_ROUNDING_DECIMALS


class LatencyClock:
    """Measure elapsed time with high precision using perf_counter."""

    def __init__(self, start_time: float) -> None:
        """Initialize clock with start time."""
        self._start_time = start_time

    @classmethod
    def start(cls) -> LatencyClock:
        """Start a new clock.

        Returns:
            LatencyClock instance with current perf_counter timestamp.
        """
        return cls(time.perf_counter())

    def stop(self) -> LatencyMeasurement:
        """Stop clock and return measurement.

        Returns:
            LatencyMeasurement with elapsed duration in milliseconds.
        """
        elapsed_seconds = time.perf_counter() - self._start_time
        duration_ms = round(elapsed_seconds * 1000, LATENCY_ROUNDING_DECIMALS)
        return LatencyMeasurement(duration_ms=duration_ms)

    @classmethod
    @contextmanager
    def measure(cls) -> Iterator[LatencyClock]:
        """Context manager for measuring elapsed time.

        Yields:
            LatencyClock instance that will measure duration on context exit.
        """
        clock = cls.start()
        try:
            yield clock
        finally:
            pass
