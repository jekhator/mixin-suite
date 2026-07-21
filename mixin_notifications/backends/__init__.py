"""Notification backend protocol and built-in implementations."""

from mixin_notifications.backends._client import CollectingBackend
from mixin_notifications.backends._client import LoggingBackend
from mixin_notifications.backends._client import NullBackend
from mixin_notifications.backends._objects import DeliveryResult
from mixin_notifications.backends._objects import NotificationBackend

__all__ = [
    "CollectingBackend",
    "DeliveryResult",
    "LoggingBackend",
    "NotificationBackend",
    "NullBackend",
]
