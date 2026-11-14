"""Tests for LatencyClock capability."""

from __future__ import annotations

import pytest

from mixin_latency import LatencyClock, LatencyMeasurement
from mixin_latency.common.constants import clock as const
from mixin_latency.tests.fakes import FakePerfCounter


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

    def test_stop_measures_duration(self, fake_perf_counter: FakePerfCounter) -> None:
        """stop() reports the elapsed time between start and stop."""
        clock = LatencyClock.start()
        fake_perf_counter.advance(0.05)
        measurement = clock.stop()

        assert measurement.duration_ms == pytest.approx(50.0)

    def test_measurement_rounding(self, fake_perf_counter: FakePerfCounter) -> None:
        """Measurements are rounded to LATENCY_ROUNDING_DECIMALS."""
        clock = LatencyClock.start()
        fake_perf_counter.advance(0.0123456)
        measurement = clock.stop()

        assert measurement.duration_ms == round(
            12.3456, const.LATENCY_ROUNDING_DECIMALS
        )

    def test_fast_operation_duration(self, fake_perf_counter: FakePerfCounter) -> None:
        """An operation that advances no time reports zero duration."""
        clock = LatencyClock.start()
        measurement = clock.stop()

        assert measurement.duration_ms == 0.0

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
        """Context manager form yields a started LatencyClock."""
        with LatencyClock.measure() as clock:
            assert isinstance(clock, LatencyClock)

    def test_context_manager_captures_duration(
        self, fake_perf_counter: FakePerfCounter
    ) -> None:
        """A clock from the context manager reports duration after exit."""
        with LatencyClock.measure() as clock:
            fake_perf_counter.advance(0.02)

        measurement = clock.stop()
        assert measurement.duration_ms == pytest.approx(20.0)

    def test_rounding_decimals_constant(self) -> None:
        """LATENCY_ROUNDING_DECIMALS is the documented two decimal places."""
        assert isinstance(const.LATENCY_ROUNDING_DECIMALS, int)
        assert const.LATENCY_ROUNDING_DECIMALS == 2

    def test_multiple_measurements_independent(
        self, fake_perf_counter: FakePerfCounter
    ) -> None:
        """Multiple clocks measure independently."""
        clock1 = LatencyClock.start()
        fake_perf_counter.advance(0.01)
        measurement1 = clock1.stop()

        clock2 = LatencyClock.start()
        fake_perf_counter.advance(0.02)
        measurement2 = clock2.stop()

        assert measurement1.duration_ms == pytest.approx(10.0)
        assert measurement2.duration_ms == pytest.approx(20.0)

    def test_measurement_dataclass_properties(
        self, fake_perf_counter: FakePerfCounter
    ) -> None:
        """LatencyMeasurement dataclass is properly structured."""
        clock = LatencyClock.start()
        fake_perf_counter.advance(0.01)
        measurement = clock.stop()

        assert hasattr(measurement, const.LATENCY_DURATION_MS_FIELD)
        assert isinstance(measurement.duration_ms, float)

    def test_measurement_repr(self) -> None:
        """LatencyMeasurement has readable repr."""
        clock = LatencyClock.start()
        measurement = clock.stop()
        repr_str = repr(measurement)

        assert LatencyMeasurement.__name__ in repr_str
        assert const.LATENCY_DURATION_MS_FIELD in repr_str
