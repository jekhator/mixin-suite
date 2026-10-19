"""Tests for RedactionClient and RedactionFilter."""

from __future__ import annotations

import logging
from collections.abc import Callable

from mixin_logging.redaction import RedactionClient, RedactionFilter
from mixin_logging.redaction.constants import redaction as const
from mixin_logging.tests.helpers import RecordCollector


class TestRedactionClient:
    """Test RedactionClient attachment and filter behavior."""

    def test_attach_default_to_logger(self, redaction_logger: logging.Logger) -> None:
        """Attach default redaction filter to a logger."""
        RedactionClient.attach_default(redaction_logger)
        assert len(redaction_logger.filters) == 1
        assert isinstance(redaction_logger.filters[0], RedactionFilter)

    def test_filter_masks_api_key_field(
        self,
        redaction_logger: logging.Logger,
        redaction_collector: RecordCollector,
    ) -> None:
        """Filter masks api_key field."""
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info("Request", extra={"api_key": "secret_key_12345"})

        assert len(redaction_collector.records) == 1
        record = redaction_collector.records[0]
        assert record.__dict__.get("api_key") == const.MASK_TOKEN

    def test_filter_preserves_nonsensitive_fields(
        self,
        redaction_logger: logging.Logger,
        redaction_collector: RecordCollector,
    ) -> None:
        """Filter preserves fields without sensitive names."""
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info(
            "User action", extra={"user_id": "12345", "action": "login"}
        )

        assert len(redaction_collector.records) == 1
        record = redaction_collector.records[0]
        assert record.__dict__.get("user_id") == "12345"
        assert record.__dict__.get("action") == "login"

    def test_filter_masks_password_field(
        self,
        redaction_logger: logging.Logger,
        redaction_collector: RecordCollector,
    ) -> None:
        """Filter masks password field."""
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info("Auth", extra={"password": "user_secret_password"})

        assert len(redaction_collector.records) == 1
        assert (
            redaction_collector.records[0].__dict__.get("password") == const.MASK_TOKEN
        )

    def test_filter_returns_true(
        self,
        redaction_filter: RedactionFilter,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Filter always returns True to allow emission."""
        assert redaction_filter.filter(make_record()) is True

    def test_filter_handles_non_string_fields(
        self,
        redaction_logger: logging.Logger,
        redaction_collector: RecordCollector,
    ) -> None:
        """Filter handles numeric and other non-string fields."""
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info("Metric", extra={"count": 42, "duration_ms": 1500})

        assert len(redaction_collector.records) == 1
        record = redaction_collector.records[0]
        assert record.__dict__.get("count") == 42
        assert record.__dict__.get("duration_ms") == 1500

    def test_filter_skips_private_attributes(
        self,
        redaction_filter: RedactionFilter,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Filter skips attributes starting with underscore."""
        record = make_record()
        setattr(record, "_private", "sensitive_data")  # noqa: B010

        assert redaction_filter.filter(record) is True
        assert getattr(record, "_private") == "sensitive_data"  # noqa: B009


class TestRedactionFilter:
    """Test RedactionFilter directly."""

    def test_filter_object_creation(self, redaction_filter: RedactionFilter) -> None:
        """Create a RedactionFilter instance."""
        assert redaction_filter is not None
        assert len(redaction_filter.sensitive_patterns) > 0

    def test_filter_modifies_record_in_place(
        self,
        redaction_filter: RedactionFilter,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Filter modifies LogRecord in place."""
        record = make_record()
        setattr(record, "api_key", "secret")  # noqa: B010

        original_id = id(record)
        result = redaction_filter.filter(record)

        assert result is True
        assert id(record) == original_id
        assert getattr(record, "api_key") == const.MASK_TOKEN  # noqa: B009

    def test_redaction_constant_value(self) -> None:
        """Redaction token has expected value."""
        assert const.MASK_TOKEN == "***REDACTED***"

    def test_case_insensitive_pattern_matching(
        self,
        redaction_filter: RedactionFilter,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Pattern matching is case-insensitive."""
        record = make_record()
        setattr(record, "API_KEY", "secret")  # noqa: B010

        redaction_filter.filter(record)

        assert getattr(record, "API_KEY") == const.MASK_TOKEN  # noqa: B009

    def test_default_patterns(self) -> None:
        """Default patterns include common sensitive fields."""
        filter_obj = RedactionFilter.with_defaults()
        assert "password" in filter_obj.sensitive_patterns
        assert "secret" in filter_obj.sensitive_patterns
        assert "api_key" in filter_obj.sensitive_patterns
        assert "token" in filter_obj.sensitive_patterns

    def test_is_sensitive_field_name_multiple_patterns(
        self, redaction_filter: RedactionFilter
    ) -> None:
        """Check field names against multiple patterns."""
        assert redaction_filter._is_sensitive_field_name("api_key") is True
        assert redaction_filter._is_sensitive_field_name("user_secret") is True
        assert redaction_filter._is_sensitive_field_name("auth_token") is True
        assert redaction_filter._is_sensitive_field_name("user_id") is False
        assert redaction_filter._is_sensitive_field_name("request_id") is False
