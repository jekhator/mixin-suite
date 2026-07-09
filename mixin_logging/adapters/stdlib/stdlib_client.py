"""CorrelationLogFilter: stdlib logging.Filter that stamps correlation_id onto LogRecords."""

from __future__ import annotations

import logging

from mixin_logging import get_correlation_id
from mixin_logging.adapters.constants import stdlib as const


class CorrelationLogFilter(logging.Filter):
    """Logging filter that stamps the current correlation_id onto every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        """Set record.correlation_id from context (or the unset sentinel); always return True."""
        setattr(
            record,
            const.CORRELATION_RECORD_ATTR,
            get_correlation_id() or const.UNSET_CORRELATION_ID,
        )
        return True

    @classmethod
    def add_correlation_filter(cls, logger: logging.Logger) -> CorrelationLogFilter:
        """Attach a CorrelationLogFilter to the given logger; return the attached filter."""
        correlation_filter = cls()
        logger.addFilter(correlation_filter)
        return correlation_filter
