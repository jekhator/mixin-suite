"""Tests for _RecordCollector: in-memory log handler for capture-and-assert fixtures."""

from __future__ import annotations

import logging

from mixin_logging.common.constants import tests as test_const
from mixin_logging.tests.helpers import _RecordCollector


class TestRecordCollectorInit:
    """Verify handler initializes with empty record list."""

    def test_init_creates_empty_records_list(self) -> None:
        """A fresh collector starts with no records."""
        collector = _RecordCollector()
        assert collector.records == []  # noqa: S101

    def test_init_inherits_handler_interface(self) -> None:
        """Collector is a logging.Handler subclass."""
        collector = _RecordCollector()
        assert isinstance(collector, logging.Handler)  # noqa: S101


class TestRecordCollectorEmit:
    """Verify emit appends records and preserves fields."""

    def test_emit_appends_single_record(self) -> None:
        """Emitting one record results in a one-element records list."""
        collector = _RecordCollector()
        record = logging.LogRecord(
            name=test_const.LOGGER_NAME_TEST,
            level=logging.INFO,
            pathname=__file__,
            lineno=1,
            msg=test_const.RECORD_MSG_HELLO,
            args=(),
            exc_info=None,
        )
        collector.emit(record)
        assert len(collector.records) == 1  # noqa: S101
        assert collector.records[0] is record  # noqa: S101

    def test_emit_accumulates_multiple_records(self) -> None:
        """Multiple emits accumulate in order."""
        collector = _RecordCollector()
        records = [
            logging.LogRecord(
                name=test_const.LOGGER_NAME_TEST,
                level=logging.INFO,
                pathname=__file__,
                lineno=i,
                msg=f"{test_const.RECORD_MSG_PREFIX}{i}",
                args=(),
                exc_info=None,
            )
            for i in range(3)
        ]
        for record in records:
            collector.emit(record)
        assert collector.records == records  # noqa: S101

    def test_emit_preserves_record_fields(self) -> None:
        """Captured record retains original level, message, and module."""
        collector = _RecordCollector()
        record = logging.LogRecord(
            name=test_const.LOGGER_NAME_CUSTOM,
            level=logging.WARNING,
            pathname=__file__,
            lineno=test_const.RECORD_LINE_NO_42,
            msg=test_const.RECORD_MSG_WARNING_TEXT,
            args=(),
            exc_info=None,
        )
        collector.emit(record)
        assert collector.records[0].name == test_const.LOGGER_NAME_CUSTOM  # noqa: S101
        assert collector.records[0].levelname == test_const.LOG_LEVEL_WARNING  # noqa: S101
        assert collector.records[0].msg == test_const.RECORD_MSG_WARNING_TEXT  # noqa: S101
        assert collector.records[0].lineno == test_const.RECORD_LINE_NO_42  # noqa: S101


class TestRecordCollectorWithLogger:
    """Verify collector works when attached to a real logger."""

    def test_attached_handler_captures_logger_emissions(self) -> None:
        """Logger.info() routed through the collector ends up in records."""
        collector = _RecordCollector()
        logger = logging.getLogger(test_const.LOGGER_NAME_RECORD_COLLECTOR_ATTACHED)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(collector)
        try:
            logger.info(test_const.RECORD_MSG_CAPTURED)
        finally:
            logger.removeHandler(collector)
        assert len(collector.records) == 1  # noqa: S101
        assert collector.records[0].msg == test_const.RECORD_MSG_CAPTURED  # noqa: S101
        assert collector.records[0].levelname == test_const.LOG_LEVEL_INFO  # noqa: S101
