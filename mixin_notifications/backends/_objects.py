"""Backend protocol and DTOs for notification delivery."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from mixin_notifications.events._objects import NotificationEvent


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    """Result of a notification delivery attempt."""

    delivered: bool
    backend_name: str
    detail: str
    retryable: bool


class NotificationBackend(Protocol):
    """Protocol for notification delivery backends."""

    @property
    def external_egress(self) -> bool:
        """Whether this backend sends data outside the system."""
        ...

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Deliver the notification event.

        Args:
            event: The notification event to send.

        Returns:
            DeliveryResult with outcome and optional retry hint.
        """
        ...
