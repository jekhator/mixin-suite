"""Dispatcher for guarded notification delivery with suppression and egress gating."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from mixin_notifications.backends._objects import DeliveryResult, NotificationBackend
from mixin_notifications.dispatch._objects import DispatchResult
from mixin_notifications.events._objects import NotificationEvent
from mixin_notifications.suppression._objects import (
    SuppressionPolicy,
    SuppressionTracker,
)


@dataclass(slots=True)
class Dispatcher:
    """Guarded dispatcher for notification delivery."""

    backends: tuple[NotificationBackend, ...]
    suppression_policy: SuppressionPolicy | None = None
    _suppression_tracker: SuppressionTracker | None = field(default=None, init=False)
    _logger: logging.Logger = field(
        default_factory=lambda: logging.getLogger("mixin_notifications"), init=False
    )

    def __post_init__(self) -> None:
        """Initialize suppression tracker if policy provided."""
        if self.suppression_policy:
            object.__setattr__(
                self,
                "_suppression_tracker",
                SuppressionTracker(
                    window_seconds=self.suppression_policy.window_seconds
                ),
            )

    def notify(self, event: NotificationEvent) -> DispatchResult:
        """Dispatch event to all backends with suppression and egress gating.

        Args:
            event: The notification event to dispatch.

        Returns:
            DispatchResult with per-backend outcomes and suppression status.
        """
        current_time = time.time()

        if self._suppression_tracker and self._suppression_tracker.is_suppressed(
            event.category,
            event.fingerprint,
            current_time,
        ):
            return DispatchResult(
                total_backends=len(self.backends),
                results=(),
                suppressed=True,
            )

        if self._suppression_tracker:
            self._suppression_tracker.record(
                event.category,
                event.fingerprint,
                current_time,
            )

        results: list[DeliveryResult] = []

        for backend in self.backends:
            egress_event = self._apply_egress_gate(event, backend)
            try:
                result = backend.send(egress_event)
                results.append(result)
            except Exception as exc:
                self._logger.warning(
                    f"Backend {backend.__class__.__name__} failed to deliver notification",
                    exc_info=exc,
                )
                results.append(
                    DeliveryResult(
                        delivered=False,
                        backend_name=backend.__class__.__name__,
                        detail=f"exception: {exc.__class__.__name__}",
                        retryable=True,
                    )
                )

        return DispatchResult(
            total_backends=len(self.backends),
            results=tuple(results),
            suppressed=False,
        )

    def _apply_egress_gate(
        self,
        event: NotificationEvent,
        backend: NotificationBackend,
    ) -> NotificationEvent:
        """Gate sensitive content for external_egress backends.

        Args:
            event: Original event.
            backend: Target backend.

        Returns:
            Original event if backend is not external_egress; sanitized event otherwise.
        """
        if not backend.external_egress:
            return event

        metadata_counts = len(event.metadata)
        masked_body = "[content redacted for external delivery]"

        return NotificationEvent(
            category=event.category,
            severity=event.severity,
            title=event.title,
            body=masked_body,
            fingerprint=event.fingerprint,
            occurred_at=event.occurred_at,
            correlation_id=event.correlation_id,
            metadata=(("sensitive_count_metadata", str(metadata_counts)),),
        )
