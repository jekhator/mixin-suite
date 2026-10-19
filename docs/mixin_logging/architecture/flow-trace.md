# mixin_logging Flow Trace

This trace follows the 0.7.0 code paths for the class-bound and ambient loggers. The sources are `mixin_logging/mixin/mixin.py`, `mixin_logging/ambient/ambient_client.py` and `mixin_logging/context/correlation/correlation_client.py`.

## Components

```
set_correlation_id(id) / get_correlation_id() / clear_correlation_id()
  correlation_client.py   stores the ID in a ContextVar (one per context)

LoggingMixin (mixin/mixin.py)            __slots__ = (), no instance state
  _logger            logging.getLogger(<module>).getChild(<ClassName>)
  _log_extra(extra)  {correlation_id: current or UNSET} merged with the caller's fields
  log_debug / log_info / log_warning / log_error / log_exception(event, **fields)

Ambient functions (module level)          log_debug / log_info / log_warning / log_error / log_exception
  AmbientLogger (dataclass, needs a logger)  same methods; fixed logger, no class context

CorrelationLogFilter (adapters/stdlib)   copies the current ID onto each LogRecord
```

## Class-bound logging: self.log_info(event, **fields)

1. The method calls `self._logger`, which resolves `logging.getLogger(type(self).__module__).getChild(type(self).__name__)`.
2. `_log_extra(fields)` reads the ContextVar. If no ID was set, the unset marker (`UNSET_CORRELATION_ID`) is used.
3. The record is emitted at the matching level with `extra=` set to that mapping.

Each class gets its own logger name, so handler and level configuration can be applied per class or per module.

## Ambient logging: log_info(event, **fields)

1. The module-level function reads the ContextVar through `get_correlation_id()`.
2. The record goes to the fixed `mixin_logging.ambient` logger, with the same extra-field mapping.

Use this path for code that is not in a class. Use `LoggingMixin` when the class context should appear in the logger name.

## Correlation ID propagation

1. `set_correlation_id(id)` sets the ContextVar for the current thread or task.
2. Every later log call in that context picks it up, without passing it in.
3. Each log record gets `correlation_id` through `CorrelationLogFilter` (stdlib adapter), which a format string can print.

## Run output

The example below was executed with `uv run --all-extras python` on Python 3.14 against the 0.7.0 tree.

```python
import logging

from mixin_logging import LoggingMixin, log_info, log_warning, set_correlation_id
from mixin_logging.adapters.stdlib.stdlib_client import CorrelationLogFilter

logging.basicConfig(level=logging.INFO, format="%(name)s %(levelname)s %(message)s correlation_id=%(correlation_id)s")
logging.getLogger().addFilter(CorrelationLogFilter())


class DocumentService(LoggingMixin):
    def process(self, doc_id: str) -> str:
        self.log_info("process.started", doc_id=doc_id)
        self.log_warning("process.slow", doc_id=doc_id, seconds=3)
        return "processed"


set_correlation_id("req-42")
DocumentService().process("doc-1")
log_info("batch.done", count=2)
log_warning("batch.retry", count=1)
```

Output (stderr from logging, shown in order):

```
__main__.DocumentService INFO process.started correlation_id=req-42
__main__.DocumentService WARNING process.slow correlation_id=req-42
mixin_logging.ambient INFO batch.done correlation_id=req-42
mixin_logging.ambient WARNING batch.retry correlation_id=req-42
```

## Invariants

- A missing correlation ID is replaced by the unset marker rather than raising.
- The ID is per context: two tasks with different IDs do not see each other's values.
- Field kwargs are passed as `extra`; masking is not applied here (see mixin_sensitivity and the redaction filter).
