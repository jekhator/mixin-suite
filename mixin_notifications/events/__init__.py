"""Notification event objects and factory."""

from mixin_notifications.events._client import NotificationEventClient
from mixin_notifications.events._objects import NotificationEvent, Severity

__all__ = [
    "NotificationEvent",
    "NotificationEventClient",
    "Severity",
]
