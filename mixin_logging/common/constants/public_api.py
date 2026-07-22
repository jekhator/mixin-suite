"""Public API export names for the logging-mixin top-level package.

Names exported from mixin_logging.__init__: ContextVarClient, LoggedClient,
LoggingMixin, correlation-id helpers. PUBLIC_API itself is exported and
self-included in this frozenset.
"""

from typing import Final

PUBLIC_API: Final = frozenset(
    {
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
        "log_debug",
        "log_error",
        "log_exception",
        "log_info",
        "log_warning",
        "logged",
        "set_correlation_id",
    },
)
