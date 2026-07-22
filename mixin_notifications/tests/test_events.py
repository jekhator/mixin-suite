"""Tests for NotificationEvent and factory."""

from __future__ import annotations

import pytest

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_notifications import NotificationEvent, NotificationEventClient, Severity


class TestNotificationEvent:
    """Test NotificationEvent creation and validation."""

    def test_create_valid_event(self) -> None:
        """Valid event creation succeeds."""
        event = NotificationEvent(
            category="auth",
            severity=Severity.WARNING,
            title="Login Failed",
            body="User provided invalid credentials",
            fingerprint="login-failed-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id="corr-123",
        )
        assert event.category == "auth"
        assert event.severity == Severity.WARNING
        assert event.title == "Login Failed"

    def test_empty_category_raises(self) -> None:
        """Empty category raises ValueError."""
        with pytest.raises(ValueError, match="category must be non-empty"):
            NotificationEvent(
                category="",
                severity=Severity.INFO,
                title="Test",
                body="Body",
                fingerprint="fp",
                occurred_at="2026-07-21T10:00:00+00:00",
                correlation_id=None,
            )

    def test_empty_title_raises(self) -> None:
        """Empty title raises ValueError."""
        with pytest.raises(ValueError, match="title must be non-empty"):
            NotificationEvent(
                category="test",
                severity=Severity.INFO,
                title="",
                body="Body",
                fingerprint="fp",
                occurred_at="2026-07-21T10:00:00+00:00",
                correlation_id=None,
            )

    def test_empty_fingerprint_raises(self) -> None:
        """Empty fingerprint raises ValueError."""
        with pytest.raises(ValueError, match="fingerprint must be non-empty"):
            NotificationEvent(
                category="test",
                severity=Severity.INFO,
                title="Title",
                body="Body",
                fingerprint="",
                occurred_at="2026-07-21T10:00:00+00:00",
                correlation_id=None,
            )

    def test_event_is_frozen(self) -> None:
        """NotificationEvent is frozen."""
        event = NotificationEvent(
            category="test",
            severity=Severity.INFO,
            title="Title",
            body="Body",
            fingerprint="fp",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )
        with pytest.raises(Exception):
            event.category = "other"  # type: ignore

    def test_metadata_tuples(self) -> None:
        """Metadata is stored as tuple of tuples."""
        event = NotificationEvent(
            category="test",
            severity=Severity.INFO,
            title="Title",
            body="Body",
            fingerprint="fp",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
            metadata=(("user_id", "123"), ("action", "create")),
        )
        assert event.metadata == (("user_id", "123"), ("action", "create"))


class TestNotificationEventFactory:
    """Test NotificationEventClient factory method."""

    def test_factory_creates_event(self) -> None:
        """Factory creates valid event."""
        clear_correlation_id()
        set_correlation_id("test-corr-id")

        event = NotificationEventClient.create(
            category="auth",
            severity="WARNING",
            title="Login Failed",
            body="Invalid credentials",
            fingerprint="login-001",
        )

        assert event.category == "auth"
        assert event.severity == Severity.WARNING
        assert event.title == "Login Failed"
        assert event.correlation_id == "test-corr-id"
        assert event.occurred_at is not None

        clear_correlation_id()

    def test_factory_with_severity_enum(self) -> None:
        """Factory accepts Severity enum."""
        event = NotificationEventClient.create(
            category="test",
            severity=Severity.CRITICAL,
            title="Critical Issue",
            body="Something broke",
            fingerprint="critical-001",
        )
        assert event.severity == Severity.CRITICAL

    def test_factory_captures_correlation_id(self) -> None:
        """Factory auto-captures correlation_id from context."""
        clear_correlation_id()
        set_correlation_id("my-corr-123")

        event = NotificationEventClient.create(
            category="test",
            severity="INFO",
            title="Test",
            body="Body",
            fingerprint="fp",
        )

        assert event.correlation_id == "my-corr-123"

        clear_correlation_id()

    def test_factory_no_correlation_id(self) -> None:
        """Factory handles no correlation_id in context."""
        clear_correlation_id()

        event = NotificationEventClient.create(
            category="test",
            severity="INFO",
            title="Test",
            body="Body",
            fingerprint="fp",
        )

        assert event.correlation_id is None

    def test_factory_with_metadata(self) -> None:
        """Factory accepts metadata."""
        event = NotificationEventClient.create(
            category="test",
            severity="INFO",
            title="Test",
            body="Body",
            fingerprint="fp",
            metadata=(("key", "value"),),
        )
        assert event.metadata == (("key", "value"),)
