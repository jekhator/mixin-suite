"""Built-in notification backends."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from mixin_notifications.backends._objects import DeliveryResult, NotificationBackend
from mixin_notifications.events._objects import NotificationEvent
from mixin_retry import RetryPolicy


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

    def __init__(self, logger_name: str = "mixin_notifications"):
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
        log_level = {
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "CRITICAL": logging.CRITICAL,
        }.get(event.severity.value, logging.INFO)

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
        """Deliver with retry logic, exhaustion → dead_letter fallback."""
        from mixin_retry import RetryExecutor

        class RetryableDeliveryError(Exception):
            """Exception to signal a retryable delivery failure."""

            def __init__(self, result: DeliveryResult):
                self.result = result
                super().__init__(result.detail)

        logger = logging.getLogger("mixin_notifications")
        executor = RetryExecutor()

        def attempt_send() -> DeliveryResult:
            result = self.inner.send(event)
            if result.retryable:
                raise RetryableDeliveryError(result)
            return result

        def should_retry(error: BaseException) -> bool:
            if isinstance(error, RetryableDeliveryError):
                return True
            if self.policy.should_retry is not None:
                return self.policy.should_retry(error)
            if self.policy.retry_on:
                return isinstance(error, self.policy.retry_on)
            return False

        policy_with_predicate = RetryPolicy(
            max_attempts=self.policy.max_attempts,
            backoff_base_seconds=self.policy.backoff_base_seconds,
            backoff_multiplier=self.policy.backoff_multiplier,
            backoff_max_seconds=self.policy.backoff_max_seconds,
            jitter=self.policy.jitter,
            should_retry=should_retry,
        )

        try:
            result = executor.call(attempt_send, policy=policy_with_predicate)
            return result
        except RetryableDeliveryError as error:
            if self.dead_letter is not None:
                try:
                    dead_result = self.dead_letter.send(event)
                    return DeliveryResult(
                        delivered=dead_result.delivered,
                        backend_name=f"RetryingBackend(dead_letter={self.dead_letter.__class__.__name__})",
                        detail=f"exhausted retries, dead_letter outcome: {dead_result.detail}",
                        retryable=False,
                    )
                except Exception as dlq_error:
                    logger.warning(
                        "Dead-letter backend failed during exhaustion fallback",
                        exc_info=dlq_error,
                    )
                    return DeliveryResult(
                        delivered=False,
                        backend_name="RetryingBackend",
                        detail="exhausted retries and dead_letter failed",
                        retryable=False,
                    )
            return DeliveryResult(
                delivered=False,
                backend_name="RetryingBackend",
                detail=f"exhausted retries: {error.result.detail}",
                retryable=False,
            )
        except Exception as error:
            is_retryable_exception = should_retry(error)
            detail_prefix = (
                "exhausted retries"
                if is_retryable_exception
                else "non-retryable exception"
            )

            if self.dead_letter is not None:
                try:
                    dead_result = self.dead_letter.send(event)
                    return DeliveryResult(
                        delivered=dead_result.delivered,
                        backend_name=f"RetryingBackend(dead_letter={self.dead_letter.__class__.__name__})",
                        detail=f"{detail_prefix}, dead_letter outcome: {dead_result.detail}",
                        retryable=False,
                    )
                except Exception as dlq_error:
                    logger.warning(
                        f"Dead-letter backend failed ({detail_prefix})",
                        exc_info=dlq_error,
                    )
                    return DeliveryResult(
                        delivered=False,
                        backend_name="RetryingBackend",
                        detail=f"{detail_prefix} and dead_letter failed",
                        retryable=False,
                    )

            return DeliveryResult(
                delivered=False,
                backend_name="RetryingBackend",
                detail=f"{detail_prefix}: {error.__class__.__name__}",
                retryable=False,
            )
