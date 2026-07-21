"""Fixtures for mixin_notifications tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from mixin_logging import clear_correlation_id
from mixin_notifications import NotificationEvent
from mixin_notifications import Severity


@pytest.fixture(autouse=True)
def _clear_correlation_context() -> Iterator[None]:
    """Clear correlation context before and after each test."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture
def _test_event() -> NotificationEvent:
    """Provide a test notification event."""
    return NotificationEvent(
        category="test",
        severity=Severity.INFO,
        title="Test Event",
        body="Test body",
        fingerprint="test-001",
        occurred_at="2026-07-21T10:00:00+00:00",
        correlation_id="test-corr",
    )


@pytest.fixture(name="test_event")
def _test_event_fixture() -> NotificationEvent:
    """Provide a test notification event."""
    return NotificationEvent(
        category="test",
        severity=Severity.INFO,
        title="Test Event",
        body="Test body",
        fingerprint="test-001",
        occurred_at="2026-07-21T10:00:00+00:00",
        correlation_id="test-corr",
    )


@pytest.fixture(name="capturing_external_backend")
def _capturing_external_backend():
    """Provide a backend that captures events and declares external_egress=True."""

    class CapturingExternalBackend:
        def __init__(self):
            self.events = []

        @property
        def external_egress(self) -> bool:
            return True

        def send(self, event: NotificationEvent):
            self.events.append(event)
            return {
                "delivered": True,
                "backend_name": "CapturingExternalBackend",
                "detail": "captured",
                "retryable": False,
            }

    return CapturingExternalBackend()


@pytest.fixture(name="capturing_internal_backend")
def _capturing_internal_backend():
    """Provide a backend that captures events and declares external_egress=False."""

    class CapturingInternalBackend:
        def __init__(self):
            self.events = []

        @property
        def external_egress(self) -> bool:
            return False

        def send(self, event: NotificationEvent):
            self.events.append(event)
            return {
                "delivered": True,
                "backend_name": "CapturingInternalBackend",
                "detail": "captured",
                "retryable": False,
            }

    return CapturingInternalBackend()
