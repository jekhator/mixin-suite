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


def handle_extract_request(  # pragma: no cover
    logger: Loggable,
    extractor: Callable[..., dict[str, object]] | None,
    *args: Any,
    **kwargs: Any,
) -> dict[str, object]:  # pragma: no cover
    """Extract request payload from args; log warning on failure, return empty."""
    if extractor is None:  # pragma: no cover
        return {}  # pragma: no cover

    try:  # pragma: no cover
        extracted = extractor(*args, **kwargs)  # pragma: no cover
        return extracted if isinstance(extracted, dict) else {}  # pragma: no cover
    except Exception as err:  # pragma: no cover
        logger.warning(  # pragma: no cover
            "extraction.failure", extra={const.LOG_FIELD_ERROR_TYPE: type(err).__name__}
        )  # pragma: no cover
        return {}  # pragma: no cover


def handle_extract_result(  # pragma: no cover
    logger: Loggable,
    extractor: Callable[[Any], dict[str, object]] | None,
    result: Any,
) -> dict[str, object]:  # pragma: no cover
    """Extract result payload; log warning on failure, return empty."""
    if extractor is None:  # pragma: no cover
        return {}  # pragma: no cover

    try:  # pragma: no cover
        extracted = extractor(result)  # pragma: no cover
        return extracted if isinstance(extracted, dict) else {}  # pragma: no cover
    except Exception as err:  # pragma: no cover
        logger.warning(  # pragma: no cover
            "extraction.failure", extra={const.LOG_FIELD_ERROR_TYPE: type(err).__name__}
        )  # pragma: no cover
        return {}  # pragma: no cover
