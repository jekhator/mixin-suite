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

    def test_external_backend_title_derived_from_category_severity(
        self,
        capturing_external_backend,
    ) -> None:
        """External backends receive derived title from category+severity, not original."""
        event = NotificationEvent(
            category="payment",
            severity=Severity.CRITICAL,
            title="Secret payment gateway down - internal issue code PCI-2847",
            body="Database connection failed",
            fingerprint="payment-gw-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        dispatcher = Dispatcher(backends=(capturing_external_backend,))
        dispatcher.notify(event)

        received = capturing_external_backend.events[0]
        assert received.title == "payment: CRITICAL notification"
        assert "Secret payment gateway down" not in received.title
        assert "PCI-2847" not in received.title

    def test_internal_backend_title_unchanged(
        self,
        capturing_internal_backend,
    ) -> None:
        """Internal backends receive original title unchanged."""
        event = NotificationEvent(
            category="payment",
            severity=Severity.CRITICAL,
            title="Secret payment gateway down - internal issue code PCI-2847",
            body="Database connection failed",
            fingerprint="payment-gw-001",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id=None,
        )

        dispatcher = Dispatcher(backends=(capturing_internal_backend,))
        dispatcher.notify(event)

        received = capturing_internal_backend.events[0]
        assert (
            received.title
            == "Secret payment gateway down - internal issue code PCI-2847"
        )

    def test_egress_category_fingerprint_correlation_id_unchanged(
        self,
        capturing_external_backend,
    ) -> None:
        """Egress gate does not mask category, fingerprint, or correlation_id."""
        event = NotificationEvent(
            category="budget_audit",
            severity=Severity.WARNING,
            title="Sensitive title content",
            body="Sensitive body",
            fingerprint="budget-anomaly-2847",
            occurred_at="2026-07-21T10:00:00+00:00",
            correlation_id="trace-12345",
        )

        dispatcher = Dispatcher(backends=(capturing_external_backend,))
        dispatcher.notify(event)

        received = capturing_external_backend.events[0]
        assert received.category == "budget_audit"
        assert received.fingerprint == "budget-anomaly-2847"
        assert received.correlation_id == "trace-12345"
        assert received.occurred_at == "2026-07-21T10:00:00+00:00"
