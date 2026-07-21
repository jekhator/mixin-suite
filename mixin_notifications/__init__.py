"""mixin-notifications: Cross-cutting notification dispatch abstraction."""

from mixin_notifications.backends import CollectingBackend
from mixin_notifications.backends import DeliveryResult
from mixin_notifications.backends import LoggingBackend
from mixin_notifications.backends import NotificationBackend
from mixin_notifications.backends import NullBackend
from mixin_notifications.config._version import __version__
from mixin_notifications.dispatch import Dispatcher
from mixin_notifications.dispatch import DispatchResult
from mixin_notifications.events import NotificationEvent
from mixin_notifications.events import NotificationEventClient
from mixin_notifications.events import Severity
from mixin_notifications.suppression import SuppressionPolicy
from mixin_notifications.suppression import SuppressionTracker

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
