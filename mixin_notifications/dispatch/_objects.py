"""Dispatcher result and related types."""

from __future__ import annotations

from dataclasses import dataclass

from mixin_notifications.backends._objects import DeliveryResult


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Outcome of dispatching a single event to all backends."""

    total_backends: int
    results: tuple[DeliveryResult, ...]
    suppressed: bool
