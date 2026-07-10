"""@logged decorator: LoggedContainer + LoggedClient factory."""

from mixin_logging.decorators.logged.logged_client import (
    LoggedClient,
    logged,
)
from mixin_logging.decorators.logged.logged_objects import (
    LoggedContainer,
)

__all__ = [
    "LoggedClient",
    "LoggedContainer",
    "logged",
]
