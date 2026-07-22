"""Tests for AmbientLogger with auto-injected correlation_id."""

from __future__ import annotations

import logging

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.ambient.ambient_client import AmbientLogger


class _RecordCapturingHandler(logging.Handler):
    """Test handler that captures log records."""

    def __init__(self) -> None:
        """Initialize with empty records list."""
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Capture the record."""
        self.records.append(record)


class TestAmbientLoggerCorrelationInjection:
    """Tests for correlation_id auto-injection."""

    def test_log_debug_injects_correlation_id(self) -> None:
        """log_debug() auto-injects correlation_id from ContextVar."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.debug")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        ambient = AmbientLogger(_logger=logger)
        set_correlation_id("flow-123")
        ambient.log_debug("test event")

        assert len(handler.records) == 1
        assert handler.records[0].correlation_id == "flow-123"

    def test_log_info_injects_correlation_id(self) -> None:
        """log_info() auto-injects correlation_id from ContextVar."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.info")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        ambient = AmbientLogger(_logger=logger)
        set_correlation_id("flow-456")
        ambient.log_info("test event")

        assert len(handler.records) == 1
        assert handler.records[0].correlation_id == "flow-456"

    def test_log_warning_injects_correlation_id(self) -> None:
        """log_warning() auto-injects correlation_id from ContextVar."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.warning")
        logger.addHandler(handler)
        logger.setLevel(logging.WARNING)

        ambient = AmbientLogger(_logger=logger)
        set_correlation_id("flow-789")
        ambient.log_warning("test event")

        assert len(handler.records) == 1
        assert handler.records[0].correlation_id == "flow-789"

    def test_log_error_injects_correlation_id(self) -> None:
        """log_error() auto-injects correlation_id from ContextVar."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.error")
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)

        ambient = AmbientLogger(_logger=logger)
        set_correlation_id("flow-abc")
        ambient.log_error("test event")

        assert len(handler.records) == 1
        assert handler.records[0].correlation_id == "flow-abc"

    def test_log_exception_injects_correlation_id(self) -> None:
        """log_exception() auto-injects correlation_id from ContextVar."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.exception")
        logger.addHandler(handler)
        logger.setLevel(logging.ERROR)

        ambient = AmbientLogger(_logger=logger)
        set_correlation_id("flow-xyz")

        try:
            raise ValueError("test error")
        except ValueError:
            ambient.log_exception("exception event")

        assert len(handler.records) == 1
        assert handler.records[0].correlation_id == "flow-xyz"
        assert handler.records[0].exc_info is not None

    def test_unset_correlation_id_defaults_to_dash(self) -> None:
        """When correlation_id is unset, defaults to '-'."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.unset")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        clear_correlation_id()
        ambient = AmbientLogger(_logger=logger)
        ambient.log_debug("test event")

        assert len(handler.records) == 1
        assert handler.records[0].correlation_id == "-"


class TestAmbientLoggerFieldsPassthrough:
    """Tests for custom fields pass-through."""

    def test_additional_fields_passed_to_logger(self) -> None:
        """log_* methods pass through additional fields."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.fields")
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        ambient = AmbientLogger(_logger=logger)
        set_correlation_id("flow-123")
        ambient.log_info("test event", user_id="user-1", action="login")

        assert len(handler.records) == 1
        assert handler.records[0].correlation_id == "flow-123"
        assert handler.records[0].user_id == "user-1"
        assert handler.records[0].action == "login"

    def test_fields_work_with_all_levels(self) -> None:
        """Fields pass through at all log levels."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.all.levels")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        ambient = AmbientLogger(_logger=logger)

        ambient.log_debug("debug event", level="debug")
        ambient.log_info("info event", level="info")
        ambient.log_warning("warning event", level="warning")
        ambient.log_error("error event", level="error")

        assert len(handler.records) == 4
        assert handler.records[0].level == "debug"
        assert handler.records[1].level == "info"
        assert handler.records[2].level == "warning"
        assert handler.records[3].level == "error"


class TestAmbientLoggerLevels:
    """Tests for correct log levels."""

    def test_log_levels_are_correct(self) -> None:
        """Each method emits at the correct level."""
        handler = _RecordCapturingHandler()
        logger = logging.getLogger("test.ambient.levels")
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        ambient = AmbientLogger(_logger=logger)
        set_correlation_id("test")

        ambient.log_debug("debug")
        ambient.log_info("info")
        ambient.log_warning("warning")
        ambient.log_error("error")

        assert len(handler.records) == 4
        assert handler.records[0].levelno == logging.DEBUG
        assert handler.records[1].levelno == logging.INFO
        assert handler.records[2].levelno == logging.WARNING
        assert handler.records[3].levelno == logging.ERROR
