"""Notification backend protocol and built-in implementations."""

from mixin_notifications.backends._client import (
    CollectingBackend,
    LoggingBackend,
    NullBackend,
)
from mixin_notifications.backends._objects import DeliveryResult, NotificationBackend

__all__ = [
    "CollectingBackend",
    "DeliveryResult",
    "LoggingBackend",
    "NotificationBackend",
    "NullBackend",
]
