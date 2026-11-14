"""Fixtures for mixin_latency tests."""

from __future__ import annotations

import time

import pytest

from mixin_latency.tests.fakes import FakePerfCounter


@pytest.fixture
def fake_perf_counter(monkeypatch: pytest.MonkeyPatch) -> FakePerfCounter:
    """Replace time.perf_counter with a settable counter for TestLatencyClock.

    Used by: TestLatencyClock.
    """
    counter = FakePerfCounter()
    monkeypatch.setattr(time, "perf_counter", counter.now)
    return counter
