"""Tests for CorrelationLogFilter (stdlib logging.Filter that stamps correlation_id onto LogRecords)."""

from __future__ import annotations

import logging
from typing import Any

import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import stdlib as const
from mixin_logging.adapters.stdlib import stdlib_client
from mixin_logging.common.constants import tests as test_const


class TestCorrelationLogFilterFilter:
    """Tests for CorrelationLogFilter.filter() method."""

    @pytest.mark.parametrize(
        "correlation_id",
        [
            test_const.CORRELATION_ID_VALID_ID_123,
            test_const.CORRELATION_ID_TRACE,
            test_const.CORRELATION_ID_ABC_123,
        ],
    )
    def test_filter_with_set_correlation_stamps_record_attribute(
        self,
        correlation_id: str,
    ) -> None:
        """filter() stamps record.correlation_id from context when set."""
        set_correlation_id(correlation_id)
        correlation_filter = stdlib_client.CorrelationLogFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )
        result = correlation_filter.filter(record)
        assert result is True
        assert getattr(record, const.CORRELATION_RECORD_ATTR) == correlation_id

    def test_filter_without_set_correlation_stamps_unset_sentinel(self) -> None:
        """filter() stamps record with UNSET_CORRELATION_ID sentinel when context is unset."""
        correlation_filter = stdlib_client.CorrelationLogFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )
        result = correlation_filter.filter(record)
        assert result is True
        assert (
            getattr(record, const.CORRELATION_RECORD_ATTR) == const.UNSET_CORRELATION_ID
        )

    def test_filter_returns_true_always(self) -> None:
        """filter() always returns True (passes record through)."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        correlation_filter = stdlib_client.CorrelationLogFilter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="test message",
            args=(),
            exc_info=None,
        )
        result = correlation_filter.filter(record)
        assert result is True


class TestCorrelationLogFilterAddCorrelationFilter:
    """Tests for CorrelationLogFilter.add_correlation_filter() class method."""

    def test_add_correlation_filter_returns_filter_instance(self) -> None:
        """add_correlation_filter() returns a CorrelationLogFilter instance."""
        logger = logging.getLogger("test_add_filter")
        correlation_filter = stdlib_client.CorrelationLogFilter.add_correlation_filter(
            logger
        )
        assert isinstance(correlation_filter, stdlib_client.CorrelationLogFilter)

    def test_add_correlation_filter_attaches_filter_to_logger(self) -> None:
        """add_correlation_filter() attaches the filter to the logger.filters."""
        logger = logging.getLogger("test_attach_filter")
        logger.filters.clear()
        correlation_filter = stdlib_client.CorrelationLogFilter.add_correlation_filter(
            logger
        )
        assert correlation_filter in logger.filters

    def test_add_correlation_filter_multiple_calls_add_multiple_filters(self) -> None:
        """add_correlation_filter() can be called multiple times adding multiple filters."""
        logger = logging.getLogger("test_multiple_filters")
        logger.filters.clear()
        filter_one = stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        filter_two = stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        assert filter_one in logger.filters
        assert filter_two in logger.filters
        assert len(logger.filters) == 2


class TestCorrelationLogFilterRealLoggingIntegration:
    """Integration tests driving stdlib logging machinery end-to-end."""

    def test_real_logging_with_set_correlation_captures_id(self) -> None:
        """Real logger with CorrelationLogFilter captures correlation_id in emitted record."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        logger_name = "test_real_logging_set_correlation"
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.filters.clear()
        logger.setLevel(logging.INFO)
        captured_records: list[logging.LogRecord] = []

        class RecordCapturingHandler(logging.Handler):
            """Custom handler that captures LogRecords for inspection."""

            def emit(self, record: logging.LogRecord) -> None:
                """Capture the record."""
                captured_records.append(record)

        handler = RecordCapturingHandler()
        logger.addHandler(handler)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        logger.info("test message")
        assert len(captured_records) == 1
        record = captured_records[0]
        assert (
            getattr(record, const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_VALID_ID_123
        )

    def test_real_logging_without_correlation_captures_unset_sentinel(self) -> None:
        """Real logger with CorrelationLogFilter captures unset sentinel when context is empty."""
        logger_name = "test_real_logging_unset_correlation"
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.filters.clear()
        logger.setLevel(logging.INFO)
        captured_records: list[logging.LogRecord] = []

        class RecordCapturingHandler(logging.Handler):
            """Custom handler that captures LogRecords for inspection."""

            def emit(self, record: logging.LogRecord) -> None:
                """Capture the record."""
                captured_records.append(record)

        handler = RecordCapturingHandler()
        logger.addHandler(handler)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        logger.info("test message")
        assert len(captured_records) == 1
        record = captured_records[0]
        assert (
            getattr(record, const.CORRELATION_RECORD_ATTR) == const.UNSET_CORRELATION_ID
        )

    def test_real_logging_correlation_changes_between_emissions(self) -> None:
        """Real logger emits records with different correlation_ids as context changes."""
        logger_name = "test_real_logging_correlation_changes"
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.filters.clear()
        logger.setLevel(logging.INFO)
        captured_records: list[logging.LogRecord] = []

        class RecordCapturingHandler(logging.Handler):
            """Custom handler that captures LogRecords for inspection."""

            def emit(self, record: logging.LogRecord) -> None:
                """Capture the record."""
                captured_records.append(record)

        handler = RecordCapturingHandler()
        logger.addHandler(handler)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        logger.info("first message")
        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        logger.info("second message")
        assert len(captured_records) == 2
        assert (
            getattr(captured_records[0], const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_VALID_ID_123
        )
        assert (
            getattr(captured_records[1], const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_TRACE
        )

    def test_real_logging_isolation_between_test_loggers(self) -> None:
        """Real loggers are isolated; filter attachment on one does not affect another."""
        logger_one_name = "test_isolation_logger_one"
        logger_two_name = "test_isolation_logger_two"
        logger_one = logging.getLogger(logger_one_name)
        logger_two = logging.getLogger(logger_two_name)
        logger_one.handlers.clear()
        logger_one.filters.clear()
        logger_two.handlers.clear()
        logger_two.filters.clear()
        logger_one.setLevel(logging.INFO)
        logger_two.setLevel(logging.INFO)
        captured_one: list[logging.LogRecord] = []
        captured_two: list[logging.LogRecord] = []

        class RecordCapturingHandler(logging.Handler):
            """Custom handler that captures LogRecords for inspection."""

            def __init__(self, target_list: list[Any]) -> None:
                """Initialize with target list."""
                super().__init__()
                self.target_list = target_list

            def emit(self, record: logging.LogRecord) -> None:
                """Capture the record."""
                self.target_list.append(record)

        handler_one = RecordCapturingHandler(captured_one)
        handler_two = RecordCapturingHandler(captured_two)
        logger_one.addHandler(handler_one)
        logger_two.addHandler(handler_two)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger_one)
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        logger_one.info("message from logger_one")
        logger_two.info("message from logger_two")
        assert len(captured_one) == 1
        assert len(captured_two) == 1
        assert (
            getattr(captured_one[0], const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_VALID_ID_123
        )
        assert not hasattr(captured_two[0], const.CORRELATION_RECORD_ATTR)
