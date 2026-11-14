"""Built-in notification backends."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from typing import Final

from mixin_notifications.backends._objects import DeliveryResult, NotificationBackend
from mixin_notifications.common.constants import backends as const
from mixin_notifications.events._objects import NotificationEvent, Severity
from mixin_retry import RetryExecutor, RetryPolicy

_LOGGER = logging.getLogger("mixin_notifications")


class _RetryableDeliveryError(Exception):
    """Signal that the wrapped backend reported a retryable delivery failure."""

    def __init__(self, result: DeliveryResult) -> None:
        """Keep the delivery result that asked for a retry."""
        super().__init__(result.detail)
        self.result = result


class NullBackend:
    """No-op backend for testing."""

    @property
    def external_egress(self) -> bool:
        """Does not egress data."""
        return False

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Accept but discard the event."""
        return DeliveryResult(
            delivered=False,
            backend_name="NullBackend",
            detail="discarded",
            retryable=False,
        )


@dataclass(slots=True)
class CollectingBackend:
    """Collects all delivered events for testing and introspection."""

    events: list[NotificationEvent] = field(default_factory=list)

    @property
    def external_egress(self) -> bool:
        """Does not egress data."""
        return False

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Collect the event."""
        self.events.append(event)
        return DeliveryResult(
            delivered=True,
            backend_name="CollectingBackend",
            detail=f"collected event {event.fingerprint}",
            retryable=False,
        )


class LoggingBackend:
    """Emits notifications via stdlib logging."""

    _LEVEL_BY_SEVERITY: Final[Mapping[Severity, int]] = {
        Severity.INFO: logging.INFO,
        Severity.WARNING: logging.WARNING,
        Severity.CRITICAL: logging.CRITICAL,
    }

    def __init__(self, logger_name: str = "mixin_notifications") -> None:
        """Initialize with a logger.

        Args:
            logger_name: Name of the logger to use.
        """
        self.logger = logging.getLogger(logger_name)

    @property
    def external_egress(self) -> bool:
        """Does not egress data."""
        return False

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Emit the event via logging."""
        log_level = self._LEVEL_BY_SEVERITY.get(event.severity, logging.INFO)

        self.logger.log(
            log_level,
            f"[{event.category}] {event.title}",
            extra={
                "body": event.body,
                "fingerprint": event.fingerprint,
                "correlation_id": event.correlation_id,
            },
        )
        return DeliveryResult(
            delivered=True,
            backend_name="LoggingBackend",
            detail=f"logged {event.severity.value}",
            retryable=False,
        )


@dataclass(frozen=True, slots=True)
class RetryingBackend:
    """Wraps a backend with retry logic via mixin_retry."""

    inner: NotificationBackend
    policy: RetryPolicy
    dead_letter: NotificationBackend | None = None

    @property
    def external_egress(self) -> bool:
        """Combines egress status of inner and dead_letter backends."""
        if self.dead_letter is not None:
            return self.inner.external_egress or self.dead_letter.external_egress
        return self.inner.external_egress

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Deliver with retry logic; exhaustion and failures fall back to dead_letter."""
        executor = RetryExecutor()
        policy = replace(self.policy, should_retry=self._should_retry)

        def attempt_send() -> DeliveryResult:
            result = self.inner.send(event)
            if result.retryable:
                raise _RetryableDeliveryError(result)
            return result

        try:
            return executor.call(attempt_send, policy=policy)
        except _RetryableDeliveryError as error:
            return self._fallback(
                event, const.RETRY_EXHAUSTED_DETAIL, error.result.detail
            )
        except Exception as error:
            if self._should_retry(error):
                prefix = const.RETRY_EXHAUSTED_DETAIL
            else:
                prefix = const.RETRY_NON_RETRYABLE_DETAIL
            return self._fallback(event, prefix, error.__class__.__name__)

    def _should_retry(self, error: BaseException) -> bool:
        """Decide whether a failure from the inner backend is retryable."""
        if isinstance(error, _RetryableDeliveryError):
            return True
        if self.policy.should_retry is not None:
            return self.policy.should_retry(error)
        if self.policy.retry_on:
            return isinstance(error, self.policy.retry_on)
        return False

    def _fallback(
        self, event: NotificationEvent, prefix: str, failure_detail: str
    ) -> DeliveryResult:
        """Hand the event to dead_letter once retries end, or report the failure."""
        if self.dead_letter is None:
            return DeliveryResult(
                delivered=False,
                backend_name=const.RETRYING_BACKEND_NAME,
                detail=f"{prefix}: {failure_detail}",
                retryable=False,
            )
        try:
            dead_result = self.dead_letter.send(event)
        except Exception as error:
            _LOGGER.warning(f"Dead-letter backend failed ({prefix})", exc_info=error)
            return DeliveryResult(
                delivered=False,
                backend_name=const.RETRYING_BACKEND_NAME,
                detail=f"{prefix} and {const.DEAD_LETTER_FAILED_DETAIL}",
                retryable=False,
            )
        dead_letter_name = self.dead_letter.__class__.__name__
        return DeliveryResult(
            delivered=dead_result.delivered,
            backend_name=f"{const.RETRYING_BACKEND_NAME}(dead_letter={dead_letter_name})",
            detail=f"{prefix}, {const.DEAD_LETTER_OUTCOME_DETAIL}: {dead_result.detail}",
            retryable=False,
        )
