"""mixin-notifications: Cross-cutting notification dispatch abstraction."""

from mixin_notifications.backends import (
    CollectingBackend,
    DeliveryResult,
    LoggingBackend,
    NotificationBackend,
    NullBackend,
)
from mixin_notifications.config._version import __version__
from mixin_notifications.dispatch import Dispatcher, DispatchResult
from mixin_notifications.events import (
    NotificationEvent,
    NotificationEventClient,
    Severity,
)
from mixin_notifications.suppression import SuppressionPolicy, SuppressionTracker

__all__ = [
    "CollectingBackend",
    "DeliveryResult",
    "Dispatcher",
    "DispatchResult",
    "LoggingBackend",
    "NotificationBackend",
    "NotificationEvent",
    "NotificationEventClient",
    "NullBackend",
    "Severity",
    "SuppressionPolicy",
    "SuppressionTracker",
    "__version__",
]
