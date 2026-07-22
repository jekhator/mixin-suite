"""FlushOnWarningHandler: correlation-aware buffer flushing on WARNING+ records."""

from __future__ import annotations

import logging
import time
from collections import deque
from typing import Final

from mixin_logging import get_correlation_id
from mixin_logging.adapters.constants import stdlib as const
from mixin_logging.adapters.stdlib.flush_handler_objects import (
    FlushOnWarningConfig,
)

# Null correlation ID for records with no correlation_id set
NULL_CORRELATION_ID: Final = "-buffered-"


class FlushOnWarningHandler(logging.Handler):
    """Buffer records per correlation_id; flush on WARNING+ to target handler."""

    __slots__ = (
        "_config",
        "_buffers",
        "_timestamps",
        "_correlation_order",
    )

    def __init__(self, config: FlushOnWarningConfig) -> None:
        """Initialize handler with config; set up per-correlation buffers."""
        super().__init__()
        self._config = config
        self.setLevel(logging.DEBUG)
        self._buffers: dict[str, deque[logging.LogRecord]] = {}
        self._timestamps: dict[str, float] = {}
        self._correlation_order: deque[str] = deque()

    def emit(self, record: logging.LogRecord) -> None:
        """Buffer records below flush_level; drain on WARNING+; evict stale entries."""
        correlation_id = self._get_correlation_id(record)
        current_time = time.time()

        self._evict_expired_buffers(current_time)

        if record.levelno >= self._config.flush_level:
            self._flush_correlation(correlation_id)
            self._config.target_handler.emit(record)
        else:
            self._buffer_record(record, correlation_id, current_time)
            self._evict_oldest_correlation_if_exceeded()

    def _get_correlation_id(self, record: logging.LogRecord) -> str:
        """Resolve correlation_id from record or context; return null sentinel if unset."""
        recorded_id = getattr(
            record,
            const.CORRELATION_RECORD_ATTR,
            const.UNSET_CORRELATION_ID,
        )
        if recorded_id == const.UNSET_CORRELATION_ID:
            return NULL_CORRELATION_ID
        return recorded_id or NULL_CORRELATION_ID

    def _evict_expired_buffers(self, current_time: float) -> None:
        """Remove buffers older than ttl_seconds."""
        to_remove = []
        for corr_id, timestamp in self._timestamps.items():
            if current_time - timestamp > self._config.ttl_seconds:
                to_remove.append(corr_id)

        for corr_id in to_remove:
            self._evict_correlation(corr_id)

    def _evict_oldest_correlation_if_exceeded(self) -> None:
        """Evict oldest correlation if max_correlations exceeded."""
        while len(self._buffers) > self._config.max_correlations:
            if self._correlation_order:
                oldest = self._correlation_order.popleft()
                self._evict_correlation(oldest)

    def _evict_correlation(self, correlation_id: str) -> None:
        """Remove all buffered records for a correlation (TTL or capacity eviction)."""
        self._buffers.pop(correlation_id, None)
        self._timestamps.pop(correlation_id, None)

    def _buffer_record(
        self,
        record: logging.LogRecord,
        correlation_id: str,
        current_time: float,
    ) -> None:
        """Append record to per-correlation buffer; enforce capacity constraint."""
        if correlation_id not in self._buffers:
            self._buffers[correlation_id] = deque(
                maxlen=self._config.capacity
            )
            self._timestamps[correlation_id] = current_time
            self._correlation_order.append(correlation_id)

        self._buffers[correlation_id].append(record)

    def _flush_correlation(self, correlation_id: str) -> None:
        """Emit all buffered records for a correlation to target, oldest first."""
        if correlation_id in self._buffers:
            for buffered_record in self._buffers[correlation_id]:
                self._config.target_handler.emit(buffered_record)
            self._evict_correlation(correlation_id)
