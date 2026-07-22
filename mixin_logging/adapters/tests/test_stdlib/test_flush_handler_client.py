"""Tests for FlushOnWarningHandler (correlation-aware flush-on-warning buffer)."""

from __future__ import annotations

import logging
import time

import pytest

from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_logging.adapters.constants import stdlib as const
from mixin_logging.adapters.stdlib.flush_handler_client import (
    NULL_CORRELATION_ID,
    FlushOnWarningHandler,
)
from mixin_logging.adapters.stdlib.flush_handler_objects import (
    FlushOnWarningConfig,
)
from mixin_logging.common.constants import tests as test_const


class _RecordCapturingHandler(logging.Handler):
    """Test handler that captures emitted records."""

    def __init__(self) -> None:
        """Initialize with empty records list."""
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        """Append record to captured list."""
        self.records.append(record)


class _MockTime:
    """Mock time provider for testing TTL eviction."""

    def __init__(self, initial: float = 0.0) -> None:
        """Initialize with initial time value."""
        self.current = initial

    def time(self) -> float:
        """Return current mock time."""
        return self.current

    def advance(self, delta: float) -> None:
        """Advance mock time by delta."""
        self.current += delta


class TestFlushOnWarningConfigValidation:
    """Tests for FlushOnWarningConfig validation."""

    def test_config_requires_target_handler(self) -> None:
        """Config raises ValueError if target_handler is None."""
        with pytest.raises(ValueError, match="target_handler must not be None"):
            FlushOnWarningConfig(target_handler=None)  # type: ignore

    def test_config_requires_flush_level_gte_warning(self) -> None:
        """Config raises ValueError if flush_level < WARNING."""
        target = _RecordCapturingHandler()
        with pytest.raises(ValueError, match="flush_level must be >= logging.WARNING"):
            FlushOnWarningConfig(
                target_handler=target,
                flush_level=logging.INFO,
            )

    def test_config_requires_positive_ttl(self) -> None:
        """Config raises ValueError if ttl_seconds <= 0."""
        target = _RecordCapturingHandler()
        with pytest.raises(ValueError, match="ttl_seconds must be > 0"):
            FlushOnWarningConfig(
                target_handler=target,
                ttl_seconds=0,
            )

    def test_config_requires_positive_capacity(self) -> None:
        """Config raises ValueError if capacity <= 0."""
        target = _RecordCapturingHandler()
        with pytest.raises(ValueError, match="capacity must be > 0"):
            FlushOnWarningConfig(
                target_handler=target,
                capacity=0,
            )

    def test_config_requires_positive_max_correlations(self) -> None:
        """Config raises ValueError if max_correlations <= 0."""
        target = _RecordCapturingHandler()
        with pytest.raises(ValueError, match="max_correlations must be > 0"):
            FlushOnWarningConfig(
                target_handler=target,
                max_correlations=0,
            )

    def test_config_accepts_valid_values(self) -> None:
        """Config accepts valid values."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(
            target_handler=target,
            flush_level=logging.WARNING,
            ttl_seconds=100,
            capacity=500,
            max_correlations=50,
        )
        assert config.target_handler is target
        assert config.flush_level == logging.WARNING
        assert config.ttl_seconds == 100
        assert config.capacity == 500
        assert config.max_correlations == 50


class TestFlushOnWarningHandlerBuffering:
    """Tests for basic buffering and flushing behavior."""

    def test_debug_records_below_flush_level_buffered(self) -> None:
        """DEBUG records below WARNING are buffered, not emitted."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(target_handler=target)
        handler = FlushOnWarningHandler(config)

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="debug message",
            args=(),
            exc_info=None,
        )
        record.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
        handler.emit(record)

        assert len(target.records) == 0

    def test_warning_triggers_buffer_drain(self) -> None:
        """WARNING record triggers drain of buffered records for that correlation."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(target_handler=target)
        handler = FlushOnWarningHandler(config)

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)

        # Emit DEBUG record (buffered)
        debug_record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="debug message",
            args=(),
            exc_info=None,
        )
        debug_record.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
        handler.emit(debug_record)

        assert len(target.records) == 0

        # Emit WARNING record
        warning_record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=43,
            msg="warning message",
            args=(),
            exc_info=None,
        )
        warning_record.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
        handler.emit(warning_record)

        assert len(target.records) == 2
        assert target.records[0] is debug_record
        assert target.records[1] is warning_record

    def test_warning_drains_oldest_first(self) -> None:
        """Flushed records are emitted oldest first."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(target_handler=target)
        handler = FlushOnWarningHandler(config)

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)

        records = []
        for i in range(3):
            record = logging.LogRecord(
                name="test",
                level=logging.DEBUG,
                pathname="test.py",
                lineno=42 + i,
                msg=f"message {i}",
                args=(),
                exc_info=None,
            )
            record.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
            records.append(record)
            handler.emit(record)

        warning_record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=50,
            msg="warning",
            args=(),
            exc_info=None,
        )
        warning_record.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
        handler.emit(warning_record)

        assert len(target.records) == 4
        assert [r.msg for r in target.records] == [
            "message 0",
            "message 1",
            "message 2",
            "warning",
        ]

    def test_other_correlations_not_affected_by_flush(self) -> None:
        """Flushing one correlation does not affect another's buffer."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(target_handler=target)
        handler = FlushOnWarningHandler(config)

        # Emit DEBUG for correlation 1
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        debug_1 = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="debug 1",
            args=(),
            exc_info=None,
        )
        debug_1.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
        handler.emit(debug_1)

        # Emit DEBUG for correlation 2
        set_correlation_id(test_const.CORRELATION_ID_TRACE)
        debug_2 = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=43,
            msg="debug 2",
            args=(),
            exc_info=None,
        )
        debug_2.correlation_id = test_const.CORRELATION_ID_TRACE
        handler.emit(debug_2)

        assert len(target.records) == 0

        # Flush correlation 1
        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        warning = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=44,
            msg="warning",
            args=(),
            exc_info=None,
        )
        warning.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
        handler.emit(warning)

        # Only correlation 1's buffer should be flushed
        assert len(target.records) == 2
        assert target.records[0] is debug_1
        assert target.records[1] is warning

        # Correlation 2's buffer should still exist
        assert test_const.CORRELATION_ID_TRACE in handler._buffers
        assert len(handler._buffers[test_const.CORRELATION_ID_TRACE]) == 1


class TestFlushOnWarningHandlerTTL:
    """Tests for TTL (time-to-live) eviction."""

    def test_ttl_evicts_expired_buffers(self) -> None:
        """Buffers older than ttl_seconds are evicted on next emit."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(
            target_handler=target,
            ttl_seconds=10,
        )
        handler = FlushOnWarningHandler(config)

        # Mock time advancement
        original_time = time.time
        mock_time = _MockTime()
        time.time = mock_time.time  # type: ignore

        try:
            # Emit record at time 0
            set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
            record_1 = logging.LogRecord(
                name="test",
                level=logging.DEBUG,
                pathname="test.py",
                lineno=42,
                msg="message",
                args=(),
                exc_info=None,
            )
            record_1.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
            handler.emit(record_1)

            assert test_const.CORRELATION_ID_VALID_ID_123 in handler._buffers

            # Advance time past TTL
            mock_time.advance(11)

            # Emit another record to trigger eviction
            set_correlation_id(test_const.CORRELATION_ID_TRACE)
            record_2 = logging.LogRecord(
                name="test",
                level=logging.DEBUG,
                pathname="test.py",
                lineno=43,
                msg="message 2",
                args=(),
                exc_info=None,
            )
            record_2.correlation_id = test_const.CORRELATION_ID_TRACE
            handler.emit(record_2)

            # Original correlation should be evicted
            assert test_const.CORRELATION_ID_VALID_ID_123 not in handler._buffers
            assert test_const.CORRELATION_ID_TRACE in handler._buffers

        finally:
            time.time = original_time


class TestFlushOnWarningHandlerCapacity:
    """Tests for capacity constraints."""

    def test_capacity_cap_per_correlation(self) -> None:
        """Buffers respect per-correlation capacity limit."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(
            target_handler=target,
            capacity=3,
        )
        handler = FlushOnWarningHandler(config)

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)

        # Emit 5 DEBUG records; only 3 should be buffered
        for i in range(5):
            record = logging.LogRecord(
                name="test",
                level=logging.DEBUG,
                pathname="test.py",
                lineno=42 + i,
                msg=f"message {i}",
                args=(),
                exc_info=None,
            )
            record.correlation_id = test_const.CORRELATION_ID_VALID_ID_123
            handler.emit(record)

        # Only last 3 records retained (deque drops oldest when maxlen exceeded)
        assert len(handler._buffers[test_const.CORRELATION_ID_VALID_ID_123]) == 3

    def test_max_correlations_cap_global(self) -> None:
        """Handler evicts oldest correlation when max_correlations exceeded."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(
            target_handler=target,
            max_correlations=2,
        )
        handler = FlushOnWarningHandler(config)

        # Buffer records for 3 correlations
        correlations = [
            test_const.CORRELATION_ID_VALID_ID_123,
            test_const.CORRELATION_ID_TRACE,
            test_const.CORRELATION_ID_ABC_123,
        ]

        for corr_id in correlations:
            set_correlation_id(corr_id)
            record = logging.LogRecord(
                name="test",
                level=logging.DEBUG,
                pathname="test.py",
                lineno=42,
                msg="message",
                args=(),
                exc_info=None,
            )
            record.correlation_id = corr_id
            handler.emit(record)

        # Only 2 correlations should remain (oldest evicted)
        assert len(handler._buffers) == 2
        assert test_const.CORRELATION_ID_VALID_ID_123 not in handler._buffers
        assert test_const.CORRELATION_ID_TRACE in handler._buffers
        assert test_const.CORRELATION_ID_ABC_123 in handler._buffers


class TestFlushOnWarningHandlerNullCorrelation:
    """Tests for records with no correlation_id."""

    def test_records_without_correlation_buffered_separately(self) -> None:
        """Records with no correlation_id are buffered under NULL_CORRELATION_ID."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(target_handler=target)
        handler = FlushOnWarningHandler(config)

        clear_correlation_id()

        record = logging.LogRecord(
            name="test",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=42,
            msg="message",
            args=(),
            exc_info=None,
        )
        record.correlation_id = const.UNSET_CORRELATION_ID
        handler.emit(record)

        assert NULL_CORRELATION_ID in handler._buffers
        assert test_const.CORRELATION_ID_VALID_ID_123 not in handler._buffers


class TestFlushOnWarningHandlerThreadSafety:
    """Tests for thread-safety via Handler lock discipline."""

    def test_handler_acquires_lock_on_emit(self) -> None:
        """Handler.emit() respects stdlib lock discipline."""
        target = _RecordCapturingHandler()
        config = FlushOnWarningConfig(target_handler=target)
        handler = FlushOnWarningHandler(config)

        set_correlation_id(test_const.CORRELATION_ID_VALID_ID_123)
        record = logging.LogRecord(
            name="test",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="warning",
            args=(),
            exc_info=None,
        )
        record.correlation_id = test_const.CORRELATION_ID_VALID_ID_123

        handler.emit(record)
        assert len(target.records) == 1
