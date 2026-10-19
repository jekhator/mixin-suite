"""Tests for FlushOnWarningHandler (correlation-aware flush-on-warning buffer)."""

from __future__ import annotations

import logging
from collections.abc import Callable

import pytest

from mixin_logging import set_correlation_id
from mixin_logging.adapters.constants import stdlib as const
from mixin_logging.adapters.stdlib.flush_handler_client import FlushOnWarningHandler
from mixin_logging.adapters.stdlib.flush_handler_objects import FlushOnWarningConfig
from mixin_logging.common.constants import tests as test_const
from mixin_logging.tests.helpers import FakeClock, RecordCollector


class TestFlushOnWarningConfigValidation:
    """Tests for FlushOnWarningConfig validation."""

    def test_config_requires_target_handler(self) -> None:
        """Config raises ValueError if target_handler is None."""
        with pytest.raises(ValueError, match=const.ERR_TARGET_HANDLER_REQUIRED):
            FlushOnWarningConfig(target_handler=None)  # type: ignore

    def test_config_requires_flush_level_gte_warning(
        self, record_target: RecordCollector
    ) -> None:
        """Config raises ValueError if flush_level < WARNING."""
        with pytest.raises(ValueError, match=const.ERR_FLUSH_LEVEL_INVALID):
            FlushOnWarningConfig(target_handler=record_target, flush_level=logging.INFO)

    def test_config_requires_positive_ttl(self, record_target: RecordCollector) -> None:
        """Config raises ValueError if ttl_seconds <= 0."""
        with pytest.raises(ValueError, match=const.ERR_TTL_POSITIVE):
            FlushOnWarningConfig(target_handler=record_target, ttl_seconds=0)

    def test_config_requires_positive_capacity(
        self, record_target: RecordCollector
    ) -> None:
        """Config raises ValueError if capacity <= 0."""
        with pytest.raises(ValueError, match=const.ERR_CAPACITY_POSITIVE):
            FlushOnWarningConfig(target_handler=record_target, capacity=0)

    def test_config_requires_positive_max_correlations(
        self, record_target: RecordCollector
    ) -> None:
        """Config raises ValueError if max_correlations <= 0."""
        with pytest.raises(ValueError, match=const.ERR_MAX_CORRELATIONS_POSITIVE):
            FlushOnWarningConfig(target_handler=record_target, max_correlations=0)

    def test_config_accepts_valid_values(self, record_target: RecordCollector) -> None:
        """Config accepts valid values."""
        config = FlushOnWarningConfig(
            target_handler=record_target,
            flush_level=logging.WARNING,
            ttl_seconds=100,
            capacity=500,
            max_correlations=50,
        )
        assert config.target_handler is record_target
        assert config.flush_level == logging.WARNING
        assert config.ttl_seconds == 100
        assert config.capacity == 500
        assert config.max_correlations == 50


class TestFlushOnWarningHandlerBuffering:
    """Tests for basic buffering and flushing behavior."""

    def test_debug_records_below_flush_level_buffered(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """DEBUG records below WARNING are buffered, not emitted."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target)
        )
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)

        handler.emit(make_record("debug message"))

        assert len(record_target.records) == 0

    def test_warning_triggers_buffer_drain(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """WARNING record triggers drain of buffered records for that correlation."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target)
        )
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        debug_record = make_record("debug message")
        handler.emit(debug_record)
        assert len(record_target.records) == 0

        warning_record = make_record("warning message", logging.WARNING)
        handler.emit(warning_record)

        assert len(record_target.records) == 2
        assert record_target.records[0] is debug_record
        assert record_target.records[1] is warning_record

    def test_warning_drains_oldest_first(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Flushed records are emitted oldest first."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target)
        )
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        for index in range(3):
            handler.emit(make_record(f"message {index}"))

        handler.emit(make_record("warning", logging.WARNING))

        assert [record.getMessage() for record in record_target.records] == [
            "message 0",
            "message 1",
            "message 2",
            "warning",
        ]

    def test_other_correlations_not_affected_by_flush(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Interleaved correlations: only the failing correlation's buffer flushes.

        Flow A and flow B are interleaved. When A warns, only A's trail flushes;
        B's buffer stays intact for a later warning of its own.
        """
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target)
        )

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        handler.emit(make_record("A step 1"))
        handler.emit(make_record("A step 2"))

        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        handler.emit(make_record("B step 1"))

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        handler.emit(make_record("A failed", logging.WARNING))

        assert [record.getMessage() for record in record_target.records] == [
            "A step 1",
            "A step 2",
            "A failed",
        ]
        assert len(handler._buffers[test_const.CORRELATION_ID_TRACE]) == 1

        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        handler.emit(make_record("B timeout", logging.WARNING))

        assert [record.getMessage() for record in record_target.records][3:] == [
            "B step 1",
            "B timeout",
        ]


class TestFlushOnWarningHandlerTTL:
    """Tests for TTL (time-to-live) eviction."""

    def test_ttl_evicts_expired_buffers(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
        fake_clock: FakeClock,
    ) -> None:
        """Buffers older than ttl_seconds are evicted on next emit."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target, ttl_seconds=10)
        )

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        handler.emit(make_record("message"))
        assert test_const.CORRELATION_ID_VALID_ID_123 in handler._buffers

        fake_clock.advance(11)
        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        handler.emit(make_record("message 2"))

        assert test_const.CORRELATION_ID_VALID_ID_123 not in handler._buffers
        assert test_const.CORRELATION_ID_TRACE in handler._buffers

    def test_recreated_correlation_keeps_records_after_ttl_eviction(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
        fake_clock: FakeClock,
    ) -> None:
        """A correlation re-created after TTL eviction keeps its records through a capacity eviction."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(
                target_handler=record_target, ttl_seconds=10, max_correlations=2
            )
        )

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        handler.emit(make_record("A first"))

        fake_clock.advance(11)
        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        handler.emit(make_record("B first"))

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        handler.emit(make_record("A second"))

        set_correlation_id(test_const.CORRELATION_ID_ABC_123)
        handler.emit(make_record("C first"))

        assert list(handler._buffers) == [
            test_const.CORRELATION_ID_VALID_ID_123,
            test_const.CORRELATION_ID_ABC_123,
        ]
        assert [
            record.getMessage()
            for record in handler._buffers[test_const.CORRELATION_ID_VALID_ID_123]
        ] == ["A second"]

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        handler.emit(make_record("A failed", logging.WARNING))

        assert [record.getMessage() for record in record_target.records] == [
            "A second",
            "A failed",
        ]


class TestFlushOnWarningHandlerCapacity:
    """Tests for capacity constraints."""

    def test_capacity_cap_per_correlation(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Buffers keep only the newest `capacity` records for a correlation."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target, capacity=3)
        )
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)

        for index in range(5):
            handler.emit(make_record(f"message {index}"))

        assert [
            record.getMessage()
            for record in handler._buffers[test_const.CORRELATION_ID_VALID_ID_123]
        ] == [
            "message 2",
            "message 3",
            "message 4",
        ]

    def test_max_correlations_cap_global(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Handler evicts the oldest correlation when max_correlations is exceeded."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target, max_correlations=2)
        )

        for corr_id in (
            test_const.CORRELATION_ID_VALID_ID_123,
            test_const.CORRELATION_ID_TRACE,
            test_const.CORRELATION_ID_ABC_123,
        ):
            set_correlation_id(corr_id)
            handler.emit(make_record("message"))

        assert list(handler._buffers) == [
            test_const.CORRELATION_ID_TRACE,
            test_const.CORRELATION_ID_ABC_123,
        ]


class TestFlushOnWarningHandlerNullCorrelation:
    """Tests for records emitted with no correlation ID set."""

    def test_records_without_correlation_buffered_under_null_key(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Records with no correlation ID are buffered under NULL_CORRELATION_ID."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target)
        )

        handler.emit(make_record("message"))

        assert list(handler._buffers) == [const.NULL_CORRELATION_ID]
        assert test_const.CORRELATION_ID_VALID_ID_123 not in handler._buffers


class TestFlushOnWarningHandlerEmit:
    """Tests for emitting warning records without a buffer."""

    def test_warning_without_buffer_emits_immediately(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """A WARNING record with nothing buffered is passed straight to the target."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target)
        )
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)

        handler.emit(make_record("warning", logging.WARNING))

        assert [record.getMessage() for record in record_target.records] == ["warning"]


class TestFlushOnWarningHandlerEvictOldest:
    """Tests for oldest-correlation eviction at the max_correlations boundary."""

    def test_evict_oldest_keeps_max_correlations(
        self,
        record_target: RecordCollector,
        make_record: Callable[..., logging.LogRecord],
    ) -> None:
        """Eviction keeps the buffer count at max_correlations."""
        handler = FlushOnWarningHandler(
            FlushOnWarningConfig(target_handler=record_target, max_correlations=1)
        )

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        handler.emit(make_record("message"))
        assert test_const.CORRELATION_ID_VALID_ID_123 in handler._buffers

        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        handler.emit(make_record("message 2"))

        assert list(handler._buffers) == [test_const.CORRELATION_ID_TRACE]
