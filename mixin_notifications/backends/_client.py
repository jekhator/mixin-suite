"""Built-in notification backends."""

from __future__ import annotations

import logging
from dataclasses import field
from dataclasses import dataclass

from mixin_notifications.backends._objects import DeliveryResult
from mixin_notifications.events._objects import NotificationEvent


class NullBackend:
    """No-op backend for testing."""

    @property
    def external_egress(self) -> bool:
        """Does not egress data."""
        return False

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Accept but discard the event."""
        return DeliveryResult(
            delivered=False,
            backend_name="NullBackend",
            detail="discarded",
            retryable=False,
        )


@dataclass(slots=True)
class CollectingBackend:
    """Collects all delivered events for testing and introspection."""

    events: list[NotificationEvent] = field(default_factory=list)

    @property
    def external_egress(self) -> bool:
        """Does not egress data."""
        return False

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Collect the event."""
        self.events.append(event)
        return DeliveryResult(
            delivered=True,
            backend_name="CollectingBackend",
            detail=f"collected event {event.fingerprint}",
            retryable=False,
        )


class LoggingBackend:
    """Emits notifications via stdlib logging."""

    def __init__(self, logger_name: str = "mixin_notifications"):
        """Initialize with a logger.

        Args:
            logger_name: Name of the logger to use.
        """
        self.logger = logging.getLogger(logger_name)

    @property
    def external_egress(self) -> bool:
        """Does not egress data."""
        return False

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Emit the event via logging."""
        log_level = {
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "CRITICAL": logging.CRITICAL,
        }.get(event.severity.value, logging.INFO)

        self.logger.log(
            log_level,
            f"[{event.category}] {event.title}",
            extra={
                "body": event.body,
                "fingerprint": event.fingerprint,
                "correlation_id": event.correlation_id,
            },
        )
        return DeliveryResult(
            delivered=True,
            backend_name="LoggingBackend",
            detail=f"logged {event.severity.value}",
            retryable=False,
        )
