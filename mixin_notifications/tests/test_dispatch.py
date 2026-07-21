"""Tests for Dispatcher."""

from __future__ import annotations

import pytest

from mixin_notifications import CollectingBackend
from mixin_notifications import Dispatcher
from mixin_notifications import NotificationEvent
from mixin_notifications import NullBackend
from mixin_notifications import Severity
from mixin_notifications import SuppressionPolicy


class TestDispatcher:
    """Test Dispatcher basic functionality."""

    def test_dispatcher_requires_explicit_backends(self) -> None:
        """Dispatcher requires explicit tuple of backends."""
        null_backend = NullBackend()
        dispatcher = Dispatcher(backends=(null_backend,))
        assert dispatcher.backends == (null_backend,)

    def test_notify_dispatches_to_all_backends(self, test_event: NotificationEvent) -> None:
        """Dispatcher sends event to all backends."""
        backend1 = CollectingBackend()
        backend2 = CollectingBackend()
        dispatcher = Dispatcher(backends=(backend1, backend2))

        result = dispatcher.notify(test_event)

        assert len(backend1.events) == 1
        assert len(backend2.events) == 1
        assert result.total_backends == 2
        assert len(result.results) == 2
        assert result.suppressed is False

    def test_notify_returns_all_results(self, test_event: NotificationEvent) -> None:
        """Dispatcher returns results from all backends."""
        backend1 = CollectingBackend()
        backend2 = NullBackend()
        dispatcher = Dispatcher(backends=(backend1, backend2))

        result = dispatcher.notify(test_event)

        assert len(result.results) == 2
        assert result.results[0].delivered is True
        assert result.results[1].delivered is False


class TestDispatcherGuardedDispatch:
    """Test Dispatcher guarded dispatch (exception handling)."""

    def test_backend_exception_does_not_raise(self, test_event: NotificationEvent, caplog: pytest.LogCaptureFixture) -> None:
        """Backend exception logs warning but does not raise."""

        class FailingBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event: NotificationEvent):
                raise RuntimeError("Backend failed")

        dispatcher = Dispatcher(backends=(FailingBackend(),))  # type: ignore

        result = dispatcher.notify(test_event)

        assert result.suppressed is False
        assert len(result.results) == 1
        assert result.results[0].delivered is False
        assert "FailingBackend" in caplog.text

    def test_multiple_backends_one_fails(self, test_event: NotificationEvent) -> None:
        """If one backend fails, others still deliver."""

        class FailingBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event: NotificationEvent):
                raise RuntimeError("Backend failed")

        collecting = CollectingBackend()
        dispatcher = Dispatcher(backends=(FailingBackend(), collecting))  # type: ignore

        result = dispatcher.notify(test_event)

        assert len(result.results) == 2
        assert result.results[0].delivered is False
        assert result.results[1].delivered is True
        assert len(collecting.events) == 1


class TestDispatcherSuppression:
    """Test Dispatcher suppression logic."""

    def test_no_suppression_by_default(self, test_event: NotificationEvent) -> None:
        """Dispatcher allows duplicates by default."""
        backend = CollectingBackend()
        dispatcher = Dispatcher(backends=(backend,))

        result1 = dispatcher.notify(test_event)
        result2 = dispatcher.notify(test_event)

        assert result1.suppressed is False
        assert result2.suppressed is False
        assert len(backend.events) == 2

    def test_suppression_within_window(self, test_event: NotificationEvent) -> None:
        """Duplicate within window is suppressed."""
        backend = CollectingBackend()
        policy = SuppressionPolicy(window_seconds=60)
        dispatcher = Dispatcher(backends=(backend,), suppression_policy=policy)

        result1 = dispatcher.notify(test_event)
        result2 = dispatcher.notify(test_event)

        assert result1.suppressed is False
        assert result2.suppressed is True
        assert len(backend.events) == 1

    def test_suppression_after_window(self, test_event: NotificationEvent) -> None:
        """Duplicate after window expires is allowed."""
        import time

        backend = CollectingBackend()
        policy = SuppressionPolicy(window_seconds=1)
        dispatcher = Dispatcher(backends=(backend,), suppression_policy=policy)

        result1 = dispatcher.notify(test_event)
        time.sleep(1.1)
        result2 = dispatcher.notify(test_event)

        assert result1.suppressed is False
        assert result2.suppressed is False
        assert len(backend.events) == 2

    def test_different_fingerprints_not_suppressed(self) -> None:
        """Different fingerprints are not suppressed."""
        policy = SuppressionPolicy(window_seconds=60)
        backend = CollectingBackend()
        dispatcher = Dispatcher(backends=(backend,), suppression_policy=policy)

        event1 = NotificationEvent(
            category="test",
            severity=Severity.INFO,
            title="Event 1",
            body="Body",
            fingerprint="fp-1",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )
        event2 = NotificationEvent(
            category="test",
            severity=Severity.INFO,
            title="Event 2",
            body="Body",
            fingerprint="fp-2",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        dispatcher.notify(event1)
        dispatcher.notify(event2)

        assert len(backend.events) == 2

    def test_different_categories_not_suppressed(self) -> None:
        """Different categories are not suppressed."""
        policy = SuppressionPolicy(window_seconds=60)
        backend = CollectingBackend()
        dispatcher = Dispatcher(backends=(backend,), suppression_policy=policy)

        event1 = NotificationEvent(
            category="auth",
            severity=Severity.INFO,
            title="Event",
            body="Body",
            fingerprint="fp",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )
        event2 = NotificationEvent(
            category="system",
            severity=Severity.INFO,
            title="Event",
            body="Body",
            fingerprint="fp",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        dispatcher.notify(event1)
        dispatcher.notify(event2)

        assert len(backend.events) == 2

    def test_suppression_tracker_capacity_eviction(self) -> None:
        """Tracker evicts oldest entry when capacity exceeded."""
        from mixin_notifications import SuppressionTracker

        tracker = SuppressionTracker(window_seconds=60, max_capacity=2)
        current_time = 1000.0

        tracker.record("cat1", "fp1", current_time)
        tracker.record("cat1", "fp2", current_time + 1)
        tracker.record("cat1", "fp3", current_time + 2)

        assert len(tracker._seen) == 2
