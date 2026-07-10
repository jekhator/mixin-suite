# logging-mixin. Stdlib Logging Adapter

> **Location:** `logging-mixin/docs/apps/adapters/stdlib.md`
> **Status:** Implemented. Output-sink correlation-ID stamping via `logging.Filter`.
> **Code location:** `mixin_logging/adapters/stdlib/` (`stdlib_client.py`); constants in `mixin_logging/adapters/constants/stdlib.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Output Sink Adapter pattern).
> **Sibling docs:** `docs/apps/adapters/celery.md`, `docs/apps/context/correlation.md`.

## Purpose

Stamp the current correlation ID onto every log record emitted by the Python standard library `logging` module, so that logs from application code, third-party libraries, and any other stdlib-logging-based source automatically include the correlation ID field for tracing and debugging across the full log stream.

## Category

Output Sink Adapter, distinct from inbound ingress adapters (ASGI/WSGI/Cloud handlers) and outbound propagation adapters (httpx/requests/botocore/celery). This adapter operates at the logging formatter level, reading the ContextVar on every `LogRecord` emission.

## Behavior

- `CorrelationLogFilter` is a subclass of the standard library's `logging.Filter`.
- `add_correlation_filter(logger)` attaches a new filter instance to the given logger (to be called at application startup, usually in the logging configuration section).
- On each log event, the `filter()` method is invoked by the logging system. It reads the current correlation ID from the ContextVar via `get_correlation_id()`. If the ContextVar is unset, the method falls back to the unset sentinel `"-"` so every LogRecord carries the field.
- The filter always returns `True`, allowing the record to propagate normally through the logging pipeline.
- The stamped value is attached as an attribute on the LogRecord with the name `correlation_id`, which a Formatter can then read via the standard Python logging format string placeholder `%(correlation_id)s`.

## Design Distinction

This adapter is **pure-behavior, no value-object**. Unlike HTTP, celery, and botocore adapters which extract and validate a correlation string from wire-crossing boundaries, the stdlib filter reads internal ContextVar state (no external data) and runs on every log emission (a hot path). No `CorrectionLogValue` dataclass is needed; instead, the filter directly reads and stamps. Zero external dependencies beyond the standard library `logging` module.

## Filter Surface

`CorrelationLogFilter` (public interface):

- `filter(record: logging.LogRecord) -> bool`. Instance method invoked on every LogRecord. Sets `record.correlation_id` to the current ContextVar value (or the `"-"` sentinel if unset); always returns `True`.
- `add_correlation_filter(logger: logging.Logger) -> CorrelationLogFilter`. Classmethod that creates and attaches a new filter instance to the given logger; returns the attached filter for further inspection if needed.

## Constants

`mixin_logging/adapters/constants/stdlib.py`:

- `CORRELATION_RECORD_ATTR = "correlation_id"` (LogRecord attribute name; matches the Formatter placeholder)
- `UNSET_CORRELATION_ID = "-"` (sentinel stamped when ContextVar is empty)

## Compatibility

Python 3.9+ (uses standard library `logging` module; no external package extras). The filter works with any logger configured via standard logging configuration (dict config, fileConfig, direct `logger.addFilter()` call).

## Example Usage

```python
import logging
from mixin_logging.adapters.stdlib.stdlib_client import CorrelationLogFilter

logger = logging.getLogger(__name__)

CorrelationLogFilter.add_correlation_filter(logger)

handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s - %(name)s - [%(correlation_id)s] - %(levelname)s - %(message)s"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

logger.info("Request processed")
```

Or in a logging configuration dictionary:

```python
import logging.config

logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - [%(correlation_id)s] - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard"
        }
    },
    "root": {
        "level": "INFO",
        "handlers": ["console"]
    }
})

logger = logging.getLogger(__name__)
CorrelationLogFilter.add_correlation_filter(logger)
```

## Lifecycle

```
┌──────────────────────────────────────┐
│ Application Startup                  │
│ ┌──────────────────────────────────┐ │
│ │ logging.config.dictConfig() or   │ │
│ │ manual handler/formatter setup    │ │
│ └──────────────┬───────────────────┘ │
│                │                      │
│                ↓                      │
│ ┌──────────────────────────────────┐ │
│ │ CorrelationLogFilter.            │ │
│ │ add_correlation_filter(logger)   │ │
│ │ [filter attached to logger]      │ │
│ └──────────────────────────────────┘ │
└──────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│ Request Arrives                      │
│ ├─ ASGI/WSGI middleware inbound      │
│ └─ _client.set_id(correlation_id)    │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│ Application Code Emits Log           │
│ logger.info("User signed up")        │
│                                      │
│ ↓ logging system routes record       │
│   through registered filters         │
│                                      │
│ ↓ CorrelationLogFilter.filter() runs │
│   • read _client.current_id()        │
│   • record.correlation_id = value    │
│   • return True                      │
│                                      │
│ ↓ Formatter renders:                 │
│   %(correlation_id)s → "req-abc123"  │
│                                      │
│ ↓ Handler emits to sink (stream,     │
│   file, CloudWatch, etc.)            │
│                                      │
│ Final log line:                      │
│ 2026-05-31 14:23:45 - [req-abc123] - │
│ User signed up                       │
└──────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│ Request Completes                    │
│ ├─ Middleware exit                   │
│ └─ _client.clear()                   │
│    [ContextVar cleared for next req] │
└──────────────────────────────────────┘
```

## See Also

- **Adapters overview / Celery:** `docs/apps/adapters/celery.md`
- **Diagram:** `docs/apps/adapters/diagrams.md` (Output Sink Adapter)
- **Correlation Context:** `docs/apps/context/correlation.md`
