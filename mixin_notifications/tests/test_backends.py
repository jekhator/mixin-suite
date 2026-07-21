"""Tests for notification backends."""

from __future__ import annotations

import pytest

from mixin_notifications import (
    CollectingBackend,
    LoggingBackend,
    NotificationEvent,
    NullBackend,
    Severity,
)


class TestNullBackend:
    """Test NullBackend."""

    def test_external_egress_is_false(self) -> None:
        """NullBackend does not egress."""
        backend = NullBackend()
        assert backend.external_egress is False

    def test_send_returns_not_delivered(self, test_event: NotificationEvent) -> None:
        """NullBackend returns not delivered."""
        backend = NullBackend()
        result = backend.send(test_event)

        assert result.delivered is False
        assert result.backend_name == "NullBackend"
        assert result.retryable is False


class TestCollectingBackend:
    """Test CollectingBackend."""

    def test_external_egress_is_false(self) -> None:
        """CollectingBackend does not egress."""
        backend = CollectingBackend()
        assert backend.external_egress is False

    def test_send_collects_event(self, test_event: NotificationEvent) -> None:
        """CollectingBackend collects the event."""
        backend = CollectingBackend()
        result = backend.send(test_event)

        assert result.delivered is True
        assert result.backend_name == "CollectingBackend"
        assert len(backend.events) == 1
        assert backend.events[0] == test_event

    def test_send_multiple_events(self, test_event: NotificationEvent) -> None:
        """CollectingBackend collects multiple events."""
        backend = CollectingBackend()

        event1 = test_event
        event2 = NotificationEvent(
            category="other",
            severity=Severity.WARNING,
            title="Other Event",
            body="Other body",
            fingerprint="other-001",
            occurred_at="2026-07-21T10:01:00+00:00",
            correlation_id=None,
        )

        backend.send(event1)
        backend.send(event2)

        assert len(backend.events) == 2
        assert backend.events[0].fingerprint == "test-001"
        assert backend.events[1].fingerprint == "other-001"


class TestLoggingBackend:
    """Test LoggingBackend."""

    def test_external_egress_is_false(self) -> None:
        """LoggingBackend does not egress."""
        backend = LoggingBackend()
        assert backend.external_egress is False

    def test_send_logs_event(self, test_event: NotificationEvent, caplog: pytest.LogCaptureFixture) -> None:
        """LoggingBackend logs the event."""
        import logging

        with caplog.at_level(logging.INFO):
            backend = LoggingBackend("test_logger")
            result = backend.send(test_event)

        assert result.delivered is True
        assert result.backend_name == "LoggingBackend"
        assert "[test] Test Event" in caplog.text

    def test_send_respects_severity(self, caplog: pytest.LogCaptureFixture) -> None:
        """LoggingBackend uses correct log level."""
        backend = LoggingBackend("test_severity")

        critical_event = NotificationEvent(
            category="critical",
            severity=Severity.CRITICAL,
            title="Critical",
            body="Critical issue",
            fingerprint="crit-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        backend.send(critical_event)
        assert "[critical] Critical" in caplog.text
