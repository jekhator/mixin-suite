"""Notification backend protocol and built-in implementations."""

from mixin_notifications.backends._client import (
    CollectingBackend,
    LoggingBackend,
    NullBackend,
    RetryingBackend,
)
from mixin_notifications.backends._objects import DeliveryResult, NotificationBackend
from mixin_notifications.backends.ses import SESBackend
from mixin_notifications.backends.sns import SNSBackend

__all__ = [
    "CollectingBackend",
    "DeliveryResult",
    "LoggingBackend",
    "NotificationBackend",
    "NullBackend",
    "RetryingBackend",
    "SESBackend",
    "SNSBackend",
]
