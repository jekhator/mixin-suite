"""logging-mixin: class-bound structured logging with correlation-ID context."""

from mixin_logging.adapters.stdlib import (
    FlushOnWarningConfig,
    FlushOnWarningHandler,
)
from mixin_logging.ambient.ambient_client import (
    AmbientLogger,
    log_debug,
    log_error,
    log_exception,
    log_info,
    log_warning,
)
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
from mixin_logging.mixin.mixin import LoggingMixin

__all__ = [
    "AmbientLogger",
    "ContextVarClient",
    "CorrelationContext",
    "FlushOnWarningConfig",
    "FlushOnWarningHandler",
    "LoggingMixin",
    "PUBLIC_API",
    "__version__",
    "clear_correlation_id",
    "get_correlation_id",
    "log_debug",
    "log_error",
    "log_exception",
    "log_info",
    "log_warning",
    "set_correlation_id",
]
