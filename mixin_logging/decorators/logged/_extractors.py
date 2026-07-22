"""Payload extraction helpers for @logged decorator wrapper."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol

from mixin_logging.decorators.constants import decorators as const

if TYPE_CHECKING:
    from collections.abc import Callable


class Loggable(Protocol):
    """Object with a warning method (Logger or LoggingMixin.log_warning)."""

    def warning(self, msg: str, **kwargs: Any) -> None:
        """Log a warning."""


def extract_request(
    logger: Loggable,
    extractor: Callable[..., dict[str, object]] | None,
    *args: Any,
    **kwargs: Any,
) -> dict[str, object]:
    """Extract request payload from args; log warning on failure, return empty."""
    if extractor is None:
        return {}

    try:
        extracted = extractor(*args, **kwargs)
        return extracted if isinstance(extracted, dict) else {}
    except Exception as err:
        logger.warning("extraction.failure", extra={const.LOG_FIELD_ERROR_TYPE: type(err).__name__})
        return {}


def extract_result(
    logger: Loggable,
    extractor: Callable[[Any], dict[str, object]] | None,
    result: Any,
) -> dict[str, object]:
    """Extract result payload; log warning on failure, return empty."""
    if extractor is None:
        return {}

    try:
        extracted = extractor(result)
        return extracted if isinstance(extracted, dict) else {}
    except Exception as err:
        logger.warning("extraction.failure", extra={const.LOG_FIELD_ERROR_TYPE: type(err).__name__})
        return {}
