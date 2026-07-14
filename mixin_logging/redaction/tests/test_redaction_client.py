"""Tests for RedactionClient and RedactionFilter."""

import logging

from mixin_logging.redaction import RedactionClient, RedactionFilter
from mixin_logging.redaction.constants import redaction as const


class TestRedactionClient:
    """Test RedactionClient attachment and filter behavior."""

    def test_attach_default_to_logger(self, redaction_logger: logging.Logger) -> None:
        """Attach default redaction filter to a logger."""
        RedactionClient.attach_default(redaction_logger)
        assert len(redaction_logger.filters) > 0
        assert isinstance(redaction_logger.filters[0], RedactionFilter)

    def test_filter_masks_api_key_field(self, redaction_logger: logging.Logger) -> None:
        """Filter masks api_key field."""
        records = []

        class CaptureHandler(logging.Handler):
            """Handler that captures records."""

            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        capture = CaptureHandler()
        redaction_logger.addHandler(capture)
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info(
            "Request",
            extra={"api_key": "secret_key_12345"},
        )

        assert len(records) == 1
        record = records[0]
        assert record.__dict__.get("api_key") == const.MASK_TOKEN

    def test_filter_preserves_nonsensitive_fields(
        self, redaction_logger: logging.Logger
    ) -> None:
        """Filter preserves fields without sensitive names."""
        records = []

        class CaptureHandler(logging.Handler):
            """Handler that captures records."""

            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        capture = CaptureHandler()
        redaction_logger.addHandler(capture)
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info(
            "User action",
            extra={"user_id": "12345", "action": "login"},
        )

        assert len(records) == 1
        record = records[0]
        assert record.__dict__.get("user_id") == "12345"
        assert record.__dict__.get("action") == "login"

    def test_filter_masks_password_field(
        self, redaction_logger: logging.Logger
    ) -> None:
        """Filter masks password field."""
        records = []

        class CaptureHandler(logging.Handler):
            """Handler that captures records."""

            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        capture = CaptureHandler()
        redaction_logger.addHandler(capture)
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info(
            "Auth",
            extra={"password": "user_secret_password"},
        )

        assert len(records) == 1
        record = records[0]
        assert record.__dict__.get("password") == const.MASK_TOKEN

    def test_filter_returns_true(self, redaction_logger: logging.Logger) -> None:
        """Filter always returns True to allow emission."""
        RedactionClient.attach_default(redaction_logger)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )

        result = redaction_logger.filters[0].filter(record)  # type: ignore[union-attr]
        assert result is True

    def test_filter_handles_non_string_fields(
        self, redaction_logger: logging.Logger
    ) -> None:
        """Filter handles numeric and other non-string fields."""
        records = []

        class CaptureHandler(logging.Handler):
            """Handler that captures records."""

            def emit(self, record: logging.LogRecord) -> None:
                records.append(record)

        capture = CaptureHandler()
        redaction_logger.addHandler(capture)
        RedactionClient.attach_default(redaction_logger)

        redaction_logger.info(
            "Metric",
            extra={"count": 42, "duration_ms": 1500},
        )

        assert len(records) == 1
        record = records[0]
        assert record.__dict__.get("count") == 42
        assert record.__dict__.get("duration_ms") == 1500

    def test_filter_skips_private_attributes(
        self, redaction_logger: logging.Logger
    ) -> None:
        """Filter skips attributes starting with underscore."""
        RedactionClient.attach_default(redaction_logger)
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        record._private = "sensitive_data"  # type: ignore[attr-defined]

        result = redaction_logger.filters[0].filter(record)  # type: ignore[union-attr]
        assert result is True
        assert record._private == "sensitive_data"  # type: ignore[attr-defined]


class TestRedactionFilter:
    """Test RedactionFilter directly."""

    def test_filter_object_creation(self, redaction_filter: RedactionFilter) -> None:
        """Create a RedactionFilter instance."""
        assert redaction_filter is not None
        assert len(redaction_filter.sensitive_patterns) > 0

    def test_filter_modifies_record_in_place(
        self, redaction_filter: RedactionFilter
    ) -> None:
        """Filter modifies LogRecord in place."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.api_key = "secret"  # type: ignore[attr-defined]

        original_id = id(record)
        result = redaction_filter.filter(record)

        assert result is True
        assert id(record) == original_id
        assert record.api_key == const.MASK_TOKEN  # type: ignore[attr-defined]

    def test_redaction_constant_value(self) -> None:
        """Redaction token has expected value."""
        assert const.MASK_TOKEN == "***REDACTED***"

    def test_case_insensitive_pattern_matching(
        self, redaction_filter: RedactionFilter
    ) -> None:
        """Pattern matching is case-insensitive."""
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="",
            lineno=0,
            msg="test",
            args=(),
            exc_info=None,
        )
        record.API_KEY = "secret"  # type: ignore[attr-defined]

        redaction_filter.filter(record)
        assert record.API_KEY == const.MASK_TOKEN  # type: ignore[attr-defined]

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
