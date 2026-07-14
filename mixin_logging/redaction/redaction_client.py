"""RedactionClient: attach redaction filter to loggers."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from mixin_logging.redaction.redaction_objects import RedactionFilter


@dataclass(frozen=True, slots=True)
class RedactionClient:
    """Client to attach redaction filters to loggers."""

    @classmethod
    def attach_default(cls, logger: logging.Logger) -> None:
        """Attach redaction filter with default patterns to a logger.

        Args:
            logger: Logger to attach the filter to.
        """
        redaction_filter = RedactionFilter.with_defaults()
        logger.addFilter(redaction_filter)
