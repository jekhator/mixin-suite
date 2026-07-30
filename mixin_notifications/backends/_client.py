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

        def should_retry(exc: BaseException) -> bool:
            return isinstance(exc, RetryableDeliveryError)

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
        except RetryableDeliveryError as exc:
            if self.dead_letter is not None:
                try:
                    dead_result = self.dead_letter.send(event)
                    return DeliveryResult(
                        delivered=dead_result.delivered,
                        backend_name=f"RetryingBackend(dead_letter={self.dead_letter.__class__.__name__})",
                        detail=f"exhausted retries, dead_letter outcome: {dead_result.detail}",
                        retryable=False,
                    )
                except Exception as dead_exc:
                    logger.warning(
                        "Dead-letter backend failed during exhaustion fallback",
                        exc_info=dead_exc,
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
                detail=f"exhausted retries: {exc.result.detail}",
                retryable=False,
            )
        except Exception as exc:
            if self.dead_letter is not None:
                try:
                    dead_result = self.dead_letter.send(event)
                    return DeliveryResult(
                        delivered=dead_result.delivered,
                        backend_name=f"RetryingBackend(dead_letter={self.dead_letter.__class__.__name__})",
                        detail=f"exception exhaustion, dead_letter outcome: {dead_result.detail}",
                        retryable=False,
                    )
                except Exception as dead_exc:
                    logger.warning(
                        "Dead-letter backend failed during exception exhaustion fallback",
                        exc_info=dead_exc,
                    )
                    return DeliveryResult(
                        delivered=False,
                        backend_name="RetryingBackend",
                        detail="exception exhaustion and dead_letter failed",
                        retryable=False,
                    )
            return DeliveryResult(
                delivered=False,
                backend_name="RetryingBackend",
                detail=f"exception exhaustion: {exc.__class__.__name__}",
                retryable=False,
            )


@dataclass(frozen=True, slots=True)
class SNSBackend:
    """AWS SNS notification backend.

    Requires: boto3>=1.28.0 (installed via [sns] extra).
    """

    sns_client: object
    default_topic_arn: str

    @property
    def external_egress(self) -> bool:
        """SNS sends data externally to AWS."""
        return True

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Publish notification to SNS topic."""
        from mixin_notifications.common.constants import events as const

        topic_arn = self.default_topic_arn
        for key, value in event.metadata:
            if key == const.METADATA_KEY_TOPIC_ARN:
                topic_arn = value
                break

        title = event.title
        body = event.body

        message_attributes = {
            "category": {
                "DataType": "String",
                "StringValue": event.category,
            },
            "severity": {
                "DataType": "String",
                "StringValue": event.severity.value,
            },
            "fingerprint": {
                "DataType": "String",
                "StringValue": event.fingerprint,
            },
        }

        if event.correlation_id:
            message_attributes["correlation_id"] = {
                "DataType": "String",
                "StringValue": event.correlation_id,
            }

        try:
            response = self.sns_client.publish(
                TopicArn=topic_arn,
                Subject=title,
                Message=body,
                MessageAttributes=message_attributes,
            )

            message_id = response.get("MessageId", "unknown")
            return DeliveryResult(
                delivered=True,
                backend_name="SNSBackend",
                detail=f"message_id: {message_id}",
                retryable=False,
            )
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            retryable_codes = {
                "Throttling",
                "ThrottledException",
                "TooManyRequestsException",
                "ServiceUnavailable",
                "InternalError",
            }
            is_retryable = error_code in retryable_codes

            return DeliveryResult(
                delivered=False,
                backend_name="SNSBackend",
                detail=f"sns_error: {error_code or exc.__class__.__name__}",
                retryable=is_retryable,
            )


@dataclass(frozen=True, slots=True)
class SESBackend:
    """AWS SES notification backend with attachment support.

    Requires: boto3>=1.28.0 (installed via [ses] extra).
    """

    ses_client: object
    to_addresses: tuple[str, ...]
    from_address: str

    @property
    def external_egress(self) -> bool:
        """SES sends data externally to AWS."""
        return True

    def send(self, event: NotificationEvent) -> DeliveryResult:
        """Send notification email via SES with attachments."""
        from email import encoders
        from email.mime.base import MIMEBase
        from email.mime.multipart import MIMEMultipart
        from email.mime.text import MIMEText

        try:
            msg = MIMEMultipart()
            msg["Subject"] = event.title
            msg["From"] = self.from_address
            msg["To"] = ", ".join(self.to_addresses)

            msg.attach(MIMEText(event.body, "plain"))

            for attachment in event.attachments:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.content)
                encoders.encode_base64(part)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename= {attachment.filename}",
                )
                msg.attach(part)

            response = self.ses_client.send_raw_email(
                RawMessage={"Data": msg.as_string()}
            )

            message_id = response.get("MessageId", "unknown")
            return DeliveryResult(
                delivered=True,
                backend_name="SESBackend",
                detail=f"message_id: {message_id}",
                retryable=False,
            )
        except Exception as exc:
            error_code = getattr(exc, "response", {}).get("Error", {}).get("Code", "")
            retryable_codes = {
                "Throttling",
                "ThrottledException",
                "TooManyRequestsException",
                "ServiceUnavailable",
                "InternalError",
            }
            is_retryable = error_code in retryable_codes

            return DeliveryResult(
                delivered=False,
                backend_name="SESBackend",
                detail=f"ses_error: {error_code or exc.__class__.__name__}",
                retryable=is_retryable,
            )
