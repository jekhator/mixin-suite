"""logging-mixin: class-bound structured logging with correlation-ID context."""

from mixin_logging.adapters.stdlib import (
    FlushOnWarningConfig,
    FlushOnWarningHandler,
)
from mixin_logging.ambient.ambient_client import AmbientLogger
from mixin_logging.common.constants.public_api import PUBLIC_API
from mixin_logging.config._version import __version__
from mixin_logging.context.correlation.correlation_client import (
    ContextVarClient,
    clear_correlation_id,
    get_correlation_id,
    set_correlation_id,
)
from mixin_logging.context.correlation.correlation_objects import (
    CorrelationContext,
)
from mixin_logging.decorators.logged.logged_client import (
    LoggedClient,
    logged,
)
from mixin_logging.decorators.logged.logged_objects import (
    LoggedContainer,
)
from mixin_logging.mixin.mixin import LoggingMixin

__all__ = [
    "AmbientLogger",
    "ContextVarClient",
    "CorrelationContext",
    "FlushOnWarningConfig",
    "FlushOnWarningHandler",
    "LoggedClient",
    "LoggedContainer",
    "LoggingMixin",
    "PUBLIC_API",
    "__version__",
    "clear_correlation_id",
    "get_correlation_id",
    "logged",
    "set_correlation_id",
]
