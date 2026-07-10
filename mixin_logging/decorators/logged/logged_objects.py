"""LoggedContainer: log-event names derived from a decorated operation's base event."""

from __future__ import annotations

from dataclasses import dataclass

from mixin_logging.decorators.constants import decorators as const


@dataclass(frozen=True, slots=True)
class LoggedContainer:
    """Log-event names derived from one decorated operation's base event."""

    event: str

    def __post_init__(self) -> None:
        """Validate event is non-empty."""
        if not self.event:
            raise ValueError(const.ERROR_MSG_EVENT_EMPTY)

    @property
    def start(self) -> str:
        """Derive start-event name <event>.start."""
        return f"{self.event}{const.EVENT_SUFFIX_START}"

    @property
    def error(self) -> str:
        """Derive error-event name <event>.error."""
        return f"{self.event}{const.EVENT_SUFFIX_ERROR}"
