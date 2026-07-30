"""mixin-notifications: Cross-cutting notification dispatch abstraction."""

from mixin_notifications.backends import (
    CollectingBackend,
    DeliveryResult,
    LoggingBackend,
    NotificationBackend,
    NullBackend,
    RetryingBackend,
    SESBackend,
    SNSBackend,
)
from mixin_notifications.config._version import __version__
from mixin_notifications.dispatch import Dispatcher, DispatchResult
from mixin_notifications.events import (
    Attachment,
    NotificationEvent,
    NotificationEventClient,
    Severity,
)
from mixin_notifications.suppression import SuppressionPolicy, SuppressionTracker

__all__ = [
    "Attachment",
    "CollectingBackend",
    "DeliveryResult",
    "Dispatcher",
    "DispatchResult",
    "LoggingBackend",
    "NotificationBackend",
    "NotificationEvent",
    "NotificationEventClient",
    "NullBackend",
    "RetryingBackend",
    "SESBackend",
    "SNSBackend",
    "Severity",
    "SuppressionPolicy",
    "SuppressionTracker",
    "__version__",
]
