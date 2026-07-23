"""Tests for LatencyClock capability."""

from __future__ import annotations

import time

import pytest

from mixin_latency import LatencyClock, LatencyMeasurement
from mixin_latency.common.constants.clock import LATENCY_ROUNDING_DECIMALS


class TestLatencyClock:
    """Test LatencyClock measurement capability."""

    def test_start_returns_clock(self) -> None:
        """LatencyClock.start() returns clock instance."""
        clock = LatencyClock.start()
        assert isinstance(clock, LatencyClock)

    def test_stop_returns_measurement(self) -> None:
        """stop() returns LatencyMeasurement."""
        clock = LatencyClock.start()
        measurement = clock.stop()
        assert isinstance(measurement, LatencyMeasurement)

    def test_stop_measures_duration(self) -> None:
        """stop() correctly measures elapsed time."""
        clock = LatencyClock.start()
        time.sleep(0.05)
        measurement = clock.stop()

        assert measurement.duration_ms >= 50.0
        assert measurement.duration_ms < 200.0

    def test_measurement_rounding(self) -> None:
        """Measurements are rounded to LATENCY_ROUNDING_DECIMALS."""
        clock = LatencyClock.start()
        time.sleep(0.01)
        measurement = clock.stop()

        decimal_places = len(str(measurement.duration_ms).split(".")[-1])
        assert decimal_places <= LATENCY_ROUNDING_DECIMALS

    def test_fast_operation_duration(self) -> None:
        """Fast operation has near-zero duration."""
        clock = LatencyClock.start()
        measurement = clock.stop()

        assert measurement.duration_ms >= 0
        assert measurement.duration_ms < 10.0

    def test_measurement_frozen(self) -> None:
        """LatencyMeasurement is frozen."""
        clock = LatencyClock.start()
        measurement = clock.stop()

        with pytest.raises(AttributeError):
            measurement.duration_ms = 999  # type: ignore[misc]

    def test_measurement_has_slots(self) -> None:
        """LatencyMeasurement uses slots."""
        clock = LatencyClock.start()
        measurement = clock.stop()

        with pytest.raises(AttributeError):
            measurement.__dict__

    def test_context_manager_form(self) -> None:
        """Context manager form measures duration on exit."""
        with LatencyClock.measure() as clock:
            time.sleep(0.01)
            assert isinstance(clock, LatencyClock)

    def test_context_manager_captures_duration(self) -> None:
        """Context manager can capture duration after exit."""
        clock = None
        with LatencyClock.measure() as c:
            clock = c
            time.sleep(0.02)

        measurement = clock.stop()
        assert measurement.duration_ms >= 20.0

    def test_rounding_decimals_constant(self) -> None:
        """LATENCY_ROUNDING_DECIMALS is imported correctly."""
        assert isinstance(LATENCY_ROUNDING_DECIMALS, int)
        assert LATENCY_ROUNDING_DECIMALS == 2

    def test_multiple_measurements_independent(self) -> None:
        """Multiple clocks measure independently."""
        clock1 = LatencyClock.start()
        time.sleep(0.01)
        measurement1 = clock1.stop()

        clock2 = LatencyClock.start()
        time.sleep(0.02)
        measurement2 = clock2.stop()

        assert measurement2.duration_ms > measurement1.duration_ms

    def test_measurement_dataclass_properties(self) -> None:
        """LatencyMeasurement dataclass is properly structured."""
        clock = LatencyClock.start()
        time.sleep(0.01)
        measurement = clock.stop()

        assert hasattr(measurement, "duration_ms")
        assert isinstance(measurement.duration_ms, float)

    def test_measurement_repr(self) -> None:
        """LatencyMeasurement has readable repr."""
        clock = LatencyClock.start()
        measurement = clock.stop()
        repr_str = repr(measurement)

        assert "LatencyMeasurement" in repr_str
        assert "duration_ms" in repr_str
