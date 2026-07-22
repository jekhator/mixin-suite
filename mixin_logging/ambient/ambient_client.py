"""Ambient contextvar logger: module-level logging with auto-injected correlation_id."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from mixin_logging.context.correlation.correlation_client import get_correlation_id


@dataclass(frozen=True, slots=True)
class AmbientLogger:
    """Logs events with auto-injected correlation_id from ContextVar.

    Trade-off: logs to a fixed module logger (mixin_logging.ambient), not per-class.
    Use LoggingMixin for per-class logging; use AmbientLogger for shared/module-level context.
    """

    _logger: logging.Logger

    def log_debug(self, event: str, **fields: Any) -> None:
        """Emit DEBUG event with auto-injected correlation_id."""
        extra = {"correlation_id": get_correlation_id() or "-"}
        extra.update(fields)
        self._logger.debug(event, extra=extra)

    def log_info(self, event: str, **fields: Any) -> None:
        """Emit INFO event with auto-injected correlation_id."""
        extra = {"correlation_id": get_correlation_id() or "-"}
        extra.update(fields)
        self._logger.info(event, extra=extra)

    def log_warning(self, event: str, **fields: Any) -> None:
        """Emit WARNING event with auto-injected correlation_id."""
        extra = {"correlation_id": get_correlation_id() or "-"}
        extra.update(fields)
        self._logger.warning(event, extra=extra)

    def log_error(self, event: str, **fields: Any) -> None:
        """Emit ERROR event with auto-injected correlation_id."""
        extra = {"correlation_id": get_correlation_id() or "-"}
        extra.update(fields)
        self._logger.error(event, extra=extra)

    def log_exception(self, event: str, **fields: Any) -> None:
        """Emit ERROR event with exception info and auto-injected correlation_id."""
        extra = {"correlation_id": get_correlation_id() or "-"}
        extra.update(fields)
        self._logger.exception(event, extra=extra)


_ambient = AmbientLogger(_logger=logging.getLogger("mixin_logging.ambient"))

log_debug = _ambient.log_debug
log_info = _ambient.log_info
log_warning = _ambient.log_warning
log_error = _ambient.log_error
log_exception = _ambient.log_exception
