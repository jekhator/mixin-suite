"""NotificationEvent frozen dataclass and related types."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


@dataclass(frozen=True, slots=True)
class Attachment:
    """Immutable notification attachment with validation."""

    filename: str
    content_type: str
    content: bytes
    egress_safe: bool = False

    def __post_init__(self) -> None:
        """Validate non-empty required fields."""
        from mixin_notifications.common.constants import events as const

        if not self.filename:
            raise ValueError(const.ERR_ATTACHMENT_EMPTY_FILENAME)
        if not self.content_type:
            raise ValueError(const.ERR_ATTACHMENT_EMPTY_CONTENT_TYPE)


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
    attachments: tuple[Attachment, ...] = ()

    def __post_init__(self) -> None:
        """Validate non-empty required fields."""
        from mixin_notifications.common.constants import events as const

        if not self.category:
            raise ValueError(const.ERR_NOTIFICATION_EMPTY_CATEGORY)
        if not self.title:
            raise ValueError(const.ERR_NOTIFICATION_EMPTY_TITLE)
        if not self.fingerprint:
            raise ValueError(const.ERR_NOTIFICATION_EMPTY_FINGERPRINT)
