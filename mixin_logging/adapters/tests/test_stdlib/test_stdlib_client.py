"""Tests for CorrelationLogFilter (stdlib logging.Filter that stamps correlation_id onto LogRecords)."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import stdlib as const
from mixin_logging.adapters.stdlib import stdlib_client
from mixin_logging.common.constants import tests as test_const
from mixin_logging.tests.helpers import RecordCollector


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
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """filter() stamps record.correlation_id from context when set."""
        set_correlation_id(correlation_id)
        correlation_filter = stdlib_client.CorrelationLogFilter()
        record = make_record("test message", logging.INFO)
        result = correlation_filter.filter(record)
        assert result is True
        assert getattr(record, const.CORRELATION_RECORD_ATTR) == correlation_id

    def test_filter_without_set_correlation_stamps_unset_sentinel(
        self,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """filter() stamps record with UNSET_CORRELATION_ID sentinel when context is unset."""
        correlation_filter = stdlib_client.CorrelationLogFilter()
        record = make_record("test message", logging.INFO)
        result = correlation_filter.filter(record)
        assert result is True
        assert (
            getattr(record, const.CORRELATION_RECORD_ATTR) == const.UNSET_CORRELATION_ID
        )

    def test_filter_returns_true_always(
        self,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """filter() always returns True (passes record through)."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        correlation_filter = stdlib_client.CorrelationLogFilter()
        result = correlation_filter.filter(make_record("test message", logging.WARNING))
        assert result is True


class TestCorrelationLogFilterAddCorrelationFilter:
    """Tests for CorrelationLogFilter.add_correlation_filter() class method."""

    def test_add_correlation_filter_returns_filter_instance(
        self,
        scratch_logger_factory: Callable[[str], logging.Logger],
    ) -> None:
        """add_correlation_filter() returns a CorrelationLogFilter instance."""
        logger = scratch_logger_factory("single")
        correlation_filter = stdlib_client.CorrelationLogFilter.add_correlation_filter(
            logger
        )
        assert isinstance(correlation_filter, stdlib_client.CorrelationLogFilter)

    def test_add_correlation_filter_attaches_filter_to_logger(
        self,
        scratch_logger_factory: Callable[[str], logging.Logger],
    ) -> None:
        """add_correlation_filter() attaches the filter to the logger.filters."""
        logger = scratch_logger_factory("attach")
        correlation_filter = stdlib_client.CorrelationLogFilter.add_correlation_filter(
            logger
        )
        assert correlation_filter in logger.filters

    def test_add_correlation_filter_multiple_calls_add_multiple_filters(
        self,
        scratch_logger_factory: Callable[[str], logging.Logger],
    ) -> None:
        """add_correlation_filter() can be called multiple times adding multiple filters."""
        logger = scratch_logger_factory("multiple")
        filter_one = stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        filter_two = stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        assert filter_one in logger.filters
        assert filter_two in logger.filters
        assert len(logger.filters) == 2


class TestCorrelationLogFilterRealLoggingIntegration:
    """Integration tests driving stdlib logging machinery end-to-end."""

    def test_real_logging_with_set_correlation_captures_id(
        self,
        scratch_logger_factory: Callable[[str], logging.Logger],
    ) -> None:
        """Real logger with CorrelationLogFilter captures correlation_id in emitted record."""
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        logger = scratch_logger_factory("set")
        collector = RecordCollector()
        logger.addHandler(collector)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        logger.info("test message")
        assert len(collector.records) == 1
        assert (
            getattr(collector.records[0], const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_VALID_ID_123
        )

    def test_real_logging_without_correlation_captures_unset_sentinel(
        self,
        scratch_logger_factory: Callable[[str], logging.Logger],
    ) -> None:
        """Real logger with CorrelationLogFilter captures unset sentinel when context is empty."""
        logger = scratch_logger_factory("unset")
        collector = RecordCollector()
        logger.addHandler(collector)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        logger.info("test message")
        assert len(collector.records) == 1
        assert (
            getattr(collector.records[0], const.CORRELATION_RECORD_ATTR)
            == const.UNSET_CORRELATION_ID
        )

    def test_real_logging_correlation_changes_between_emissions(
        self,
        scratch_logger_factory: Callable[[str], logging.Logger],
    ) -> None:
        """Real logger emits records with different correlation_ids as context changes."""
        logger = scratch_logger_factory("changes")
        collector = RecordCollector()
        logger.addHandler(collector)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger)
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        logger.info("first message")
        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        logger.info("second message")
        assert len(collector.records) == 2
        assert (
            getattr(collector.records[0], const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_VALID_ID_123
        )
        assert (
            getattr(collector.records[1], const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_TRACE
        )

    def test_real_logging_isolation_between_test_loggers(
        self,
        scratch_logger_factory: Callable[[str], logging.Logger],
    ) -> None:
        """Real loggers are isolated; filter attachment on one does not affect another."""
        logger_one = scratch_logger_factory("one")
        logger_two = scratch_logger_factory("two")
        collector_one = RecordCollector()
        collector_two = RecordCollector()
        logger_one.addHandler(collector_one)
        logger_two.addHandler(collector_two)
        stdlib_client.CorrelationLogFilter.add_correlation_filter(logger_one)
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        logger_one.info("message from logger_one")
        logger_two.info("message from logger_two")
        assert len(collector_one.records) == 1
        assert len(collector_two.records) == 1
        assert (
            getattr(collector_one.records[0], const.CORRELATION_RECORD_ATTR)
            == test_const.CORRELATION_ID_VALID_ID_123
        )
        assert not hasattr(collector_two.records[0], const.CORRELATION_RECORD_ATTR)
