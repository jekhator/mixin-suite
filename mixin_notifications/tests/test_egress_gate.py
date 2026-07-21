"""Tests for Dispatcher egress gate (sensitivity masking)."""

from __future__ import annotations

from mixin_notifications import Dispatcher, NotificationEvent, Severity


class TestEgressGate:
    """Test egress gate functionality."""

    def test_internal_backend_receives_unmasked_content(
        self,
        capturing_internal_backend,
    ) -> None:
        """Internal backends receive original content."""
        event = NotificationEvent(
            category="user",
            severity=Severity.INFO,
            title="User Registration",
            body="User john.doe@example.com registered successfully",
            fingerprint="user-reg-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        dispatcher = Dispatcher(backends=(capturing_internal_backend,))
        dispatcher.notify(event)

        assert len(capturing_internal_backend.events) == 1
        received = capturing_internal_backend.events[0]
        assert "john.doe@example.com" in received.body

    def test_external_backend_receives_masked_content(
        self,
        capturing_external_backend,
    ) -> None:
        """External backends receive redacted content."""
        event = NotificationEvent(
            category="user",
            severity=Severity.INFO,
            title="User Registration",
            body="User john.doe@example.com registered successfully",
            fingerprint="user-reg-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        dispatcher = Dispatcher(backends=(capturing_external_backend,))
        dispatcher.notify(event)

        assert len(capturing_external_backend.events) == 1
        received = capturing_external_backend.events[0]
        assert "[content redacted for external delivery]" == received.body

    def test_mixed_backends_each_receive_appropriate_content(
        self,
        capturing_internal_backend,
        capturing_external_backend,
    ) -> None:
        """Internal receives unmasked, external receives redacted."""
        event = NotificationEvent(
            category="user",
            severity=Severity.INFO,
            title="User Data",
            body="SSN: 123-45-6789 and email: user@example.com",
            fingerprint="user-data-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        dispatcher = Dispatcher(
            backends=(capturing_internal_backend, capturing_external_backend)
        )
        dispatcher.notify(event)

        internal_event = capturing_internal_backend.events[0]
        external_event = capturing_external_backend.events[0]

        assert "123-45-6789" in internal_event.body
        assert "user@example.com" in internal_event.body
        assert "[content redacted for external delivery]" == external_event.body

    def test_external_backend_metadata_reduced_to_counts(
        self,
        capturing_external_backend,
    ) -> None:
        """External backends receive metadata as counts only."""
        event = NotificationEvent(
            category="data",
            severity=Severity.WARNING,
            title="Data Event",
            body="Contains sensitive info",
            fingerprint="data-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
            metadata=(("field1", "secret-value-1"), ("field2", "secret-value-2")),
        )

        dispatcher = Dispatcher(backends=(capturing_external_backend,))
        dispatcher.notify(event)

        received = capturing_external_backend.events[0]
        assert len(received.metadata) == 1
        key, value = received.metadata[0]
        assert key == "sensitive_count_metadata"
        assert value == "2"
