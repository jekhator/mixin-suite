"""NotificationEvent factory and client methods."""

from __future__ import annotations

from datetime import datetime, timezone

from mixin_notifications.events._objects import NotificationEvent, Severity


class NotificationEventClient:
    """Factory and utilities for NotificationEvent."""

    @staticmethod
    def create(
        category: str,
        severity: str | Severity,
        title: str,
        body: str,
        fingerprint: str,
        metadata: tuple[tuple[str, str], ...] = (),
    ) -> NotificationEvent:
        """Create a NotificationEvent with auto-captured correlation context.

        Args:
            category: Event category (non-empty).
            severity: Severity level (INFO, WARNING, CRITICAL).
            title: Event title (non-empty).
            body: Event body/description.
            fingerprint: Unique fingerprint for deduplication (non-empty).
            metadata: Optional tuple of (key, value) pairs.

        Returns:
            Configured NotificationEvent with correlation_id and occurred_at populated.
        """
        from mixin_logging import get_correlation_id

        resolved_severity = (
            Severity(severity) if isinstance(severity, str) else severity
        )

        now_utc = datetime.now(timezone.utc).isoformat()

        return NotificationEvent(
            category=category,
            severity=resolved_severity,
            title=title,
            body=body,
            fingerprint=fingerprint,
            occurred_at=now_utc,
            correlation_id=get_correlation_id(),
            metadata=metadata,
        )
