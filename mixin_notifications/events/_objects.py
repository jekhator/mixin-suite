"""NotificationEvent frozen dataclass and related types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Severity(StrEnum):
    """Notification severity levels."""

    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """Immutable notification event with validation."""

    category: str
    severity: Severity
    title: str
    body: str
    fingerprint: str
    occurred_at: str
    correlation_id: str | None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        """Validate non-empty required fields."""
        from mixin_notifications.common.constants import events as const

        if not self.category:
            raise ValueError(const.ERR_NOTIFICATION_EMPTY_CATEGORY)
        if not self.title:
            raise ValueError(const.ERR_NOTIFICATION_EMPTY_TITLE)
        if not self.fingerprint:
            raise ValueError(const.ERR_NOTIFICATION_EMPTY_FINGERPRINT)
