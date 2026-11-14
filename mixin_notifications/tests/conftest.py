"""Fixtures for mixin_notifications tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from mixin_logging import clear_correlation_id
from mixin_notifications import DeliveryResult, NotificationEvent, Severity


class CapturingBackend:
    """Backend that records delivered events and reports a fixed egress flag."""

    def __init__(self, *, egress: bool, name: str) -> None:
        """Start with no events; egress and name decide the reported identity."""
        self.events: list[NotificationEvent] = []
        self._egress = egress
        self._name = name

    @property
    def external_egress(self) -> bool:
        """Return the egress flag this backend was built with."""
        return self._egress

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Record the event and report a successful delivery."""
        self.events.append(event)
        return DeliveryResult(
            delivered=True,
            backend_name=self._name,
            detail="captured",
            retryable=False,
        )


@pytest.fixture(autouse=True)
def _clear_correlation_context() -> Iterator[None]:
    """Clear correlation context before and after each test."""
    clear_correlation_id()
    yield
    clear_correlation_id()


@pytest.fixture(name="test_event")
def _test_event_fixture() -> NotificationEvent:
    """Provide a test notification event.

    Used by: TestNullBackend, TestCollectingBackend, TestRetryingBackend,
    TestSNSBackend, TestSESBackend, TestDispatcher, TestDispatcherGuardedDispatch,
    TestDispatcherSuppression.
    """
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
def _capturing_external_backend() -> CapturingBackend:
    """Provide a backend that captures events and declares external_egress=True.

    Used by: TestEgressGate.
    """
    return CapturingBackend(egress=True, name="CapturingExternalBackend")


@pytest.fixture(name="capturing_internal_backend")
def _capturing_internal_backend() -> CapturingBackend:
    """Provide a backend that captures events and declares external_egress=False.

    Used by: TestEgressGate.
    """
    return CapturingBackend(egress=False, name="CapturingInternalBackend")
