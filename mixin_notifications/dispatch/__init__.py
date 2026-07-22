"""Notification dispatcher with guarded delivery, suppression, and egress gating."""

from mixin_notifications.dispatch._client import Dispatcher
from mixin_notifications.dispatch._objects import DispatchResult

__all__ = [
    "Dispatcher",
    "DispatchResult",
]
