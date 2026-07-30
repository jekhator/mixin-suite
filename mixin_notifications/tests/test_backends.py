"""Tests for notification backends."""

from __future__ import annotations

import pytest

from mixin_notifications import (
    Attachment,
    CollectingBackend,
    LoggingBackend,
    NotificationEvent,
    NullBackend,
    RetryingBackend,
    SESBackend,
    Severity,
    SNSBackend,
)
from mixin_retry import (
    RetryPolicy,
)


class TestNullBackend:
    """Test NullBackend."""

    def test_external_egress_is_false(self) -> None:
        """NullBackend does not egress."""
        backend = NullBackend()
        assert backend.external_egress is False

    def test_send_returns_not_delivered(self, test_event: NotificationEvent) -> None:
        """NullBackend returns not delivered."""
        backend = NullBackend()
        result = backend.send(test_event)

        assert result.delivered is False
        assert result.backend_name == "NullBackend"
        assert result.retryable is False


class TestCollectingBackend:
    """Test CollectingBackend."""

    def test_external_egress_is_false(self) -> None:
        """CollectingBackend does not egress."""
        backend = CollectingBackend()
        assert backend.external_egress is False

    def test_send_collects_event(self, test_event: NotificationEvent) -> None:
        """CollectingBackend collects the event."""
        backend = CollectingBackend()
        result = backend.send(test_event)

        assert result.delivered is True
        assert result.backend_name == "CollectingBackend"
        assert len(backend.events) == 1
        assert backend.events[0] == test_event

    def test_send_multiple_events(self, test_event: NotificationEvent) -> None:
        """CollectingBackend collects multiple events."""
        backend = CollectingBackend()

        event1 = test_event
        event2 = NotificationEvent(
            category="other",
            severity=Severity.WARNING,
            title="Other Event",
            body="Other body",
            fingerprint="other-001",
            occurred_at="2026-07-21T10:01:00+00:00",
            correlation_id=None,
        )

        backend.send(event1)
        backend.send(event2)

        assert len(backend.events) == 2
        assert backend.events[0].fingerprint == "test-001"
        assert backend.events[1].fingerprint == "other-001"


class TestLoggingBackend:
    """Test LoggingBackend."""

    def test_external_egress_is_false(self) -> None:
        """LoggingBackend does not egress."""
        backend = LoggingBackend()
        assert backend.external_egress is False

    def test_send_logs_event(
        self, test_event: NotificationEvent, caplog: pytest.LogCaptureFixture
    ) -> None:
        """LoggingBackend logs the event."""
        import logging

        with caplog.at_level(logging.INFO):
            backend = LoggingBackend("test_logger")
            result = backend.send(test_event)

        assert result.delivered is True
        assert result.backend_name == "LoggingBackend"
        assert "[test] Test Event" in caplog.text

    def test_send_respects_severity(self, caplog: pytest.LogCaptureFixture) -> None:
        """LoggingBackend uses correct log level."""
        backend = LoggingBackend("test_severity")

        critical_event = NotificationEvent(
            category="critical",
            severity=Severity.CRITICAL,
            title="Critical",
            body="Critical issue",
            fingerprint="crit-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        backend.send(critical_event)
        assert "[critical] Critical" in caplog.text


class TestAttachment:
    """Test Attachment DTO."""

    def test_attachment_frozen(self) -> None:
        """Attachment is frozen."""
        att = Attachment(
            filename="test.txt",
            content_type="text/plain",
            content=b"test data",
        )
        with pytest.raises(AttributeError):
            att.filename = "other.txt"  # type: ignore

    def test_attachment_validation_empty_filename(self) -> None:
        """Attachment rejects empty filename."""
        with pytest.raises(ValueError) as exc_info:
            Attachment(
                filename="",
                content_type="text/plain",
                content=b"test",
            )
        assert "filename" in str(exc_info.value).lower()

    def test_attachment_validation_empty_content_type(self) -> None:
        """Attachment rejects empty content_type."""
        with pytest.raises(ValueError) as exc_info:
            Attachment(
                filename="test.txt",
                content_type="",
                content=b"test",
            )
        assert "content_type" in str(exc_info.value).lower()

    def test_attachment_egress_safe_default(self) -> None:
        """Attachment egress_safe defaults to False."""
        att = Attachment(
            filename="test.txt",
            content_type="text/plain",
            content=b"test",
        )
        assert att.egress_safe is False

    def test_attachment_egress_safe_true(self) -> None:
        """Attachment can be marked egress_safe."""
        att = Attachment(
            filename="test.txt",
            content_type="text/plain",
            content=b"test",
            egress_safe=True,
        )
        assert att.egress_safe is True


class TestRetryingBackend:
    """Test RetryingBackend retry and dead-letter logic."""

    def test_retrying_backend_external_egress_from_inner(self) -> None:
        """RetryingBackend inherits external_egress from inner."""
        inner = CollectingBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.1,
            backoff_multiplier=2,
            backoff_max_seconds=1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy)
        assert backend.external_egress is False

    def test_retrying_backend_external_egress_from_dead_letter(self) -> None:
        """RetryingBackend OR's external_egress with dead_letter."""

        class ExternalBackend:
            @property
            def external_egress(self) -> bool:
                return True

            def send(self, event):
                from mixin_notifications import DeliveryResult

                return DeliveryResult(
                    delivered=True,
                    backend_name="ExternalBackend",
                    detail="ok",
                    retryable=False,
                )

        inner = CollectingBackend()
        dead_letter = ExternalBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.1,
            backoff_multiplier=2,
            backoff_max_seconds=1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dead_letter)
        assert backend.external_egress is True

    def test_retrying_backend_success_on_first_attempt(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend returns success immediately if inner succeeds."""
        inner = CollectingBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.1,
            backoff_multiplier=2,
            backoff_max_seconds=1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy)

        result = backend.send(test_event)

        assert result.delivered is True
        assert len(inner.events) == 1

    def test_retrying_backend_retry_on_retryable_result(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend retries when inner returns retryable=True."""

        attempt_count = 0

        class FailThenSuccessBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                nonlocal attempt_count
                attempt_count += 1
                from mixin_notifications import DeliveryResult

                if attempt_count < 3:
                    return DeliveryResult(
                        delivered=False,
                        backend_name="FailThenSuccessBackend",
                        detail="temporary failure",
                        retryable=True,
                    )
                return DeliveryResult(
                    delivered=True,
                    backend_name="FailThenSuccessBackend",
                    detail="success",
                    retryable=False,
                )

        inner = FailThenSuccessBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy)

        result = backend.send(test_event)

        assert result.delivered is True
        assert attempt_count == 3

    def test_retrying_backend_nonretryable_returns_immediately(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend returns immediately on retryable=False."""

        attempt_count = 0

        class ImmediateFailBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                nonlocal attempt_count
                attempt_count += 1
                from mixin_notifications import DeliveryResult

                return DeliveryResult(
                    delivered=False,
                    backend_name="ImmediateFailBackend",
                    detail="permanent failure",
                    retryable=False,
                )

        inner = ImmediateFailBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.1,
            backoff_multiplier=2,
            backoff_max_seconds=1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy)

        result = backend.send(test_event)

        assert result.delivered is False
        assert attempt_count == 1

    def test_retrying_backend_exhaustion_no_dead_letter(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend returns failure after exhaustion with no dead_letter."""

        class AlwaysFailBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                from mixin_notifications import DeliveryResult

                return DeliveryResult(
                    delivered=False,
                    backend_name="AlwaysFailBackend",
                    detail="always fails",
                    retryable=True,
                )

        inner = AlwaysFailBackend()
        policy = RetryPolicy(
            max_attempts=2,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy)

        result = backend.send(test_event)

        assert result.delivered is False
        assert "exhausted retries" in result.detail

    def test_retrying_backend_dead_letter_on_exhaustion(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend hands off to dead_letter on exhaustion."""

        class AlwaysFailBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                from mixin_notifications import DeliveryResult

                return DeliveryResult(
                    delivered=False,
                    backend_name="AlwaysFailBackend",
                    detail="always fails",
                    retryable=True,
                )

        inner = AlwaysFailBackend()
        dead_letter = CollectingBackend()
        policy = RetryPolicy(
            max_attempts=2,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dead_letter)

        result = backend.send(test_event)

        assert result.delivered is True
        assert len(dead_letter.events) == 1
        assert "dead_letter" in result.backend_name

    def test_retrying_backend_dead_letter_exception(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend handles dead-letter exceptions with warning."""

        class AlwaysFailBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                from mixin_notifications import DeliveryResult

                return DeliveryResult(
                    delivered=False,
                    backend_name="AlwaysFailBackend",
                    detail="always fails",
                    retryable=True,
                )

        class FailingDeadLetter:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                raise RuntimeError("Dead-letter backend failed")

        inner = AlwaysFailBackend()
        dead_letter = FailingDeadLetter()
        policy = RetryPolicy(
            max_attempts=1,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dead_letter)

        result = backend.send(test_event)

        assert result.delivered is False
        assert "dead_letter failed" in result.detail

    def test_retrying_backend_inner_exception_dead_letter_success(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend uses dead-letter on exception from inner."""

        class ExceptionRaisingBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                raise RuntimeError("Inner backend exception")

        inner = ExceptionRaisingBackend()
        dead_letter = CollectingBackend()
        policy = RetryPolicy(
            max_attempts=1,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dead_letter)

        result = backend.send(test_event)

        assert result.delivered is True
        assert len(dead_letter.events) == 1
        assert "non-retryable exception" in result.detail

    def test_retrying_backend_inner_exception_dead_letter_exception(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend handles exceptions during exception exhaustion fallback."""

        class ExceptionRaisingBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                raise RuntimeError("Inner backend exception")

        class FailingDeadLetter:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                raise RuntimeError("Dead-letter also failed")

        inner = ExceptionRaisingBackend()
        dead_letter = FailingDeadLetter()
        policy = RetryPolicy(
            max_attempts=1,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dead_letter)

        result = backend.send(test_event)

        assert result.delivered is False
        assert "dead_letter failed" in result.detail

    def test_retrying_backend_inner_exception_no_dead_letter(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend returns failure on inner exception without dead-letter."""

        class ExceptionRaisingBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                raise RuntimeError("Inner backend exception")

        inner = ExceptionRaisingBackend()
        policy = RetryPolicy(
            max_attempts=1,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
        )
        backend = RetryingBackend(inner=inner, policy=policy)

        result = backend.send(test_event)

        assert result.delivered is False
        assert "non-retryable exception" in result.detail

    def test_retrying_backend_raised_exception_with_retry_on_policy(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend retries raised exceptions matching policy.retry_on."""
        attempt_count = 0

        class ConnectionErrorBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                nonlocal attempt_count
                attempt_count += 1
                raise ConnectionError("Network failed")

        inner = ConnectionErrorBackend()
        dlq = CollectingBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
            retry_on=(ConnectionError,),
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dlq)

        result = backend.send(test_event)

        # REGRESSION: Must attempt exactly max_attempts times before dead-letter
        assert attempt_count == 3, f"Expected 3 attempts, got {attempt_count}"
        assert result.delivered is True  # DLQ accepted
        assert len(dlq.events) == 1

    def test_retrying_backend_raised_exception_with_should_retry_predicate(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend retries raised exceptions matching policy.should_retry."""
        attempt_count = 0

        class TemporaryErrorBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                nonlocal attempt_count
                attempt_count += 1
                raise ValueError("Temporary value error")

        inner = TemporaryErrorBackend()
        dlq = CollectingBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
            should_retry=lambda error: isinstance(error, ValueError),
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dlq)

        result = backend.send(test_event)

        # REGRESSION: Must attempt exactly max_attempts times before dead-letter
        assert attempt_count == 3, f"Expected 3 attempts, got {attempt_count}"
        assert result.delivered is True  # DLQ accepted
        assert len(dlq.events) == 1

    def test_retrying_backend_raised_exception_non_retryable(
        self, test_event: NotificationEvent
    ) -> None:
        """RetryingBackend does not retry raised exceptions policy deems non-retryable."""
        attempt_count = 0

        class PermanentErrorBackend:
            @property
            def external_egress(self) -> bool:
                return False

            def send(self, event):
                nonlocal attempt_count
                attempt_count += 1
                raise PermissionError("Access denied")

        inner = PermanentErrorBackend()
        dlq = CollectingBackend()
        policy = RetryPolicy(
            max_attempts=3,
            backoff_base_seconds=0.01,
            backoff_multiplier=1,
            backoff_max_seconds=0.1,
            jitter=False,
            retry_on=(ConnectionError,),  # Does NOT include PermissionError
        )
        backend = RetryingBackend(inner=inner, policy=policy, dead_letter=dlq)

        result = backend.send(test_event)

        # REGRESSION: Non-retryable exceptions should attempt exactly once
        assert attempt_count == 1, f"Expected 1 attempt, got {attempt_count}"
        assert result.delivered is True  # DLQ accepted
        assert (
            "non-retryable exception" in result.detail
            or "non-retryable" in result.detail
        )


class TestSNSBackend:
    """Test SNSBackend."""

    def test_sns_backend_metadata_without_topic_arn(
        self, test_event: NotificationEvent
    ) -> None:
        """SNSBackend ignores metadata that doesn't include topic_arn."""

        class MockSNS:
            def __init__(self):
                self.published_args = {}

            def publish(self, **kwargs):
                self.published_args.update(kwargs)
                return {"MessageId": "test-msg-id"}

        mock_client = MockSNS()
        backend = SNSBackend(
            sns_client=mock_client,
            default_topic_arn="arn:aws:sns:us-east-1:123456789012:default",
        )

        event_with_other_metadata = NotificationEvent(
            category="test",
            severity=Severity.INFO,
            title="Test Event",
            body="Test body",
            fingerprint="test-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
            metadata=(("other_key", "other_value"),),
        )

        result = backend.send(event_with_other_metadata)

        assert result.delivered is True
        assert (
            mock_client.published_args["TopicArn"]
            == "arn:aws:sns:us-east-1:123456789012:default"
        )

    def test_sns_backend_external_egress(self) -> None:
        """SNSBackend has external_egress=True."""
        mock_client = type("MockSNS", (), {})()
        backend = SNSBackend(
            sns_client=mock_client,
            default_topic_arn="arn:aws:sns:us-east-1:123456789012:test",
        )
        assert backend.external_egress is True

    def test_sns_backend_uses_default_topic(
        self, test_event: NotificationEvent
    ) -> None:
        """SNSBackend publishes to default topic when not overridden."""

        class MockSNS:
            def __init__(self):
                self.published_args = {}

            def publish(self, **kwargs):
                self.published_args.update(kwargs)
                return {"MessageId": "test-msg-id"}

        mock_client = MockSNS()
        backend = SNSBackend(
            sns_client=mock_client,
            default_topic_arn="arn:aws:sns:us-east-1:123456789012:test",
        )

        result = backend.send(test_event)

        assert result.delivered is True
        assert "test-msg-id" in result.detail
        assert (
            mock_client.published_args["TopicArn"]
            == "arn:aws:sns:us-east-1:123456789012:test"
        )

    def test_sns_backend_metadata_topic_override(
        self, test_event: NotificationEvent
    ) -> None:
        """SNSBackend uses metadata topic_arn override."""

        class MockSNS:
            def __init__(self):
                self.published_args = {}

            def publish(self, **kwargs):
                self.published_args.update(kwargs)
                return {"MessageId": "test-msg-id"}

        mock_client = MockSNS()
        backend = SNSBackend(
            sns_client=mock_client,
            default_topic_arn="arn:aws:sns:us-east-1:123456789012:default",
        )

        event_with_topic = NotificationEvent(
            category="test",
            severity=Severity.INFO,
            title="Test Event",
            body="Test body",
            fingerprint="test-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
            metadata=(("topic_arn", "arn:aws:sns:us-east-1:123456789012:override"),),
        )

        result = backend.send(event_with_topic)

        assert result.delivered is True
        assert (
            mock_client.published_args["TopicArn"]
            == "arn:aws:sns:us-east-1:123456789012:override"
        )

    def test_sns_backend_retryable_error_code(
        self, test_event: NotificationEvent
    ) -> None:
        """SNSBackend marks Throttling as retryable."""

        class MockException(Exception):
            def __init__(self):
                self.response = {"Error": {"Code": "Throttling"}}

        class MockSNS:
            def publish(self, **kwargs):
                raise MockException()

        mock_client = MockSNS()
        backend = SNSBackend(
            sns_client=mock_client,
            default_topic_arn="arn:aws:sns:us-east-1:123456789012:test",
        )

        result = backend.send(test_event)

        assert result.delivered is False
        assert result.retryable is True

    def test_sns_backend_non_retryable_error_code(
        self, test_event: NotificationEvent
    ) -> None:
        """SNSBackend marks InvalidParameter as non-retryable."""

        class MockException(Exception):
            def __init__(self):
                self.response = {"Error": {"Code": "InvalidParameter"}}

        def mock_publish(**kwargs):
            raise MockException()

        mock_client = type("MockSNS", (), {"publish": mock_publish})()
        backend = SNSBackend(
            sns_client=mock_client,
            default_topic_arn="arn:aws:sns:us-east-1:123456789012:test",
        )

        result = backend.send(test_event)

        assert result.delivered is False
        assert result.retryable is False


class TestSESBackend:
    """Test SESBackend."""

    def test_ses_backend_external_egress(self) -> None:
        """SESBackend has external_egress=True."""
        mock_client = type("MockSES", (), {})()
        backend = SESBackend(
            ses_client=mock_client,
            to_addresses=("test@example.com",),
            from_address="sender@example.com",
        )
        assert backend.external_egress is True

    def test_ses_backend_send_without_attachments(
        self, test_event: NotificationEvent
    ) -> None:
        """SESBackend sends email without attachments."""

        class MockSES:
            def __init__(self):
                self.sent_emails = []

            def send_raw_email(self, **kwargs):
                self.sent_emails.append(kwargs)
                return {"MessageId": "test-msg-id"}

        mock_client = MockSES()
        backend = SESBackend(
            ses_client=mock_client,
            to_addresses=("test@example.com",),
            from_address="sender@example.com",
        )

        result = backend.send(test_event)

        assert result.delivered is True
        assert "test-msg-id" in result.detail
        assert len(mock_client.sent_emails) == 1

    def test_ses_backend_send_with_attachments(
        self, test_event: NotificationEvent
    ) -> None:
        """SESBackend includes attachments in email."""

        class MockSES:
            def __init__(self):
                self.sent_emails = []

            def send_raw_email(self, **kwargs):
                self.sent_emails.append(kwargs)
                return {"MessageId": "test-msg-id"}

        mock_client = MockSES()
        backend = SESBackend(
            ses_client=mock_client,
            to_addresses=("test@example.com",),
            from_address="sender@example.com",
        )

        event_with_attachment = NotificationEvent(
            category="test",
            severity=Severity.INFO,
            title="Test Event",
            body="Test body",
            fingerprint="test-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
            attachments=(
                Attachment(
                    filename="test.txt",
                    content_type="text/plain",
                    content=b"test content",
                    egress_safe=True,
                ),
            ),
        )

        result = backend.send(event_with_attachment)

        assert result.delivered is True
        assert len(mock_client.sent_emails) == 1

    def test_ses_backend_retryable_error(self, test_event: NotificationEvent) -> None:
        """SESBackend marks ServiceUnavailable as retryable."""

        class MockException(Exception):
            def __init__(self):
                self.response = {"Error": {"Code": "ServiceUnavailable"}}

        class MockSES:
            def send_raw_email(self, **kwargs):
                raise MockException()

        mock_client = MockSES()
        backend = SESBackend(
            ses_client=mock_client,
            to_addresses=("test@example.com",),
            from_address="sender@example.com",
        )

        result = backend.send(test_event)

        assert result.delivered is False
        assert result.retryable is True
