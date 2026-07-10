"""LoggingMixin: class-bound structured logging with auto-injected correlation IDs."""

from __future__ import annotations

import logging
from typing import Any

from mixin_logging.context.constants import correlation as const
from mixin_logging.context.correlation.correlation_client import _client


class LoggingMixin:
    """Class-bound logger auto-injecting correlation_id + per-class context."""

    __slots__ = ()

    @property
    def _logger(self) -> logging.Logger:
        """Per-class logger named <module>.<ClassName>."""
        return logging.getLogger(self.__class__.__module__).getChild(
            self.__class__.__name__,
        )

    def _log_extra(self, extra: dict[str, Any]) -> dict[str, Any]:
        """Build the log extra: correlation_id + the caller's explicit kwargs."""
        result: dict[str, Any] = {
            const.CORRELATION_ID_KEY: _client.current_id()
            or const.UNSET_CORRELATION_ID,
        }
        if extra:
            result.update(extra)
        return result

    def log_debug(self, event: str, **extra: Any) -> None:
        """Log at DEBUG with auto-injected correlation + class context."""
        self._logger.debug(event, extra=self._log_extra(extra))

    def log_info(self, event: str, **extra: Any) -> None:
        """Log at INFO with auto-injected correlation + class context."""
        self._logger.info(event, extra=self._log_extra(extra))

    def log_warning(self, event: str, **extra: Any) -> None:
        """Log at WARNING with auto-injected correlation + class context."""
        self._logger.warning(event, extra=self._log_extra(extra))

    def log_error(self, event: str, **extra: Any) -> None:
        """Log at ERROR with auto-injected correlation + class context."""
        self._logger.error(event, extra=self._log_extra(extra))

    def log_exception(self, event: str, **extra: Any) -> None:
        """Log at ERROR with traceback (use inside an except block)."""
        self._logger.exception(event, extra=self._log_extra(extra))
