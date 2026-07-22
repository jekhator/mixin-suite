# logging-mixin. Flush-on-Warning Handler

> **Location:** `logging-mixin/docs/apps/adapters/flush-handler.md`
> **Status:** Implemented. Correlation-aware buffering with flush-on-WARNING behavior.
> **Code location:** `mixin_logging/adapters/stdlib/` (`flush_handler_client.py`, `flush_handler_objects.py`); constants in `flush_handler_objects.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Flush-on-Warning Handler pattern).
> **Sibling docs:** `docs/apps/adapters/stdlib.md`, `docs/apps/context/correlation.md`.

## Purpose

Buffer log records below WARNING level on a per-correlation basis, and automatically flush (emit to a target handler) all buffered records for a correlation when a WARNING or higher severity record arrives for that same correlation. This ensures that when a flow fails, its full context trail becomes visible without bloating logs for successful operations.

## Category

Handler Wrapper (buffers and transforms records per correlation; sits in the logging pipeline alongside stdlib handlers). Distinct from Filter adapters (which stamp attributes) and Propagation adapters (which cross boundaries).

## Behavior

- `FlushOnWarningHandler` is a subclass of the standard library's `logging.Handler`.
- Buffers `DEBUG`, `INFO`, and `NOTSET` records (below `WARNING` level, configurable via `flush_level` parameter).
- When a record with level >= `flush_level` (default `WARNING`) arrives for a correlation, the handler emits all buffered records for that correlation to the `target_handler` (oldest first), then clears that correlation's buffer.
- Records with level >= `flush_level` are always emitted immediately to the target handler (after any flushed trail).
- Buffers are evicted on two triggers:
  - **TTL (Time-To-Live):** Buffers older than `ttl_seconds` (default 300 seconds) are lazily evicted on the next record emission, without requiring background threads or completion signals.
  - **Capacity:** Each correlation is capped at `capacity` records (default 1000, via `deque(maxlen)`); a global cap of `max_correlations` (default 100) evicts the oldest correlation by insertion order when exceeded.
- Records with no correlation ID (unset in the ContextVar, or stamped with the unset sentinel) are buffered under a designated null-correlation bucket to prevent mixing with correlated records.
- Thread-safe via the stdlib `Handler` acquire/release lock discipline.

## Config Surface

`FlushOnWarningConfig` (frozen dataclass):

- `target_handler` (required): The `logging.Handler` to which buffered and flushed records are emitted.
- `flush_level` (default `logging.WARNING`): Minimum severity to trigger a flush; must be >= `logging.WARNING`.
- `ttl_seconds` (default `300`): Number of seconds after which a buffer is evicted if no flush has occurred (must be > 0).
- `capacity` (default `1000`): Maximum records buffered per correlation, enforced via `deque(maxlen)`.
- `max_correlations` (default `100`): Maximum number of concurrent correlation buffers; oldest (by insertion) is evicted when exceeded.

`FlushOnWarningHandler` (logging.Handler):

- `__init__(config: FlushOnWarningConfig)` - Initialize with config.
- `emit(record: logging.LogRecord)` - Core handler entry point; buffers, flushes, or evicts as needed.

## Constants

`mixin_logging/adapters/stdlib/flush_handler_objects.py`:

- `DEFAULT_FLUSH_LEVEL = logging.WARNING`
- `DEFAULT_TTL_SECONDS = 300`
- `DEFAULT_CAPACITY = 1000`
- `DEFAULT_MAX_CORRELATIONS = 100`
- Error message constants: `ERR_TARGET_HANDLER_REQUIRED`, `ERR_FLUSH_LEVEL_INVALID`, etc.

## Design Distinction

This handler **buffers per correlation, not globally** (unlike stdlib's `MemoryHandler`, which maintains a single global buffer). Only the failing correlation's trail materializes; successful operations leave no buffered records. No background threads; TTL eviction is lazy (triggered on emit). Configuration is immutable (frozen dataclass) to prevent mid-flight changes.

## Compatibility

Python 3.11+ (uses frozen-slots dataclass with `ContextVar` correlation tracking). Works with any logger configured via standard logging configuration; designed to sit in the handler chain between the logger and final output sinks (files, streams, CloudWatch, etc.).

## Example Usage

```python
import logging
from mixin_logging.adapters.stdlib import FlushOnWarningConfig, FlushOnWarningHandler
from mixin_logging import set_correlation_id

# Configure target handler (e.g., console output)
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter(
    "%(asctime)s - %(name)s - [%(correlation_id)s] - %(levelname)s - %(message)s"
)
console_handler.setFormatter(console_formatter)

# Wrap it with flush-on-warning
config = FlushOnWarningConfig(
    target_handler=console_handler,
    flush_level=logging.WARNING,
    ttl_seconds=300,
    capacity=1000,
    max_correlations=100,
)
flush_handler = FlushOnWarningHandler(config)

# Attach to logger
logger = logging.getLogger(__name__)
logger.addHandler(flush_handler)
logger.setLevel(logging.DEBUG)

# Use in application
set_correlation_id("request-123")
logger.debug("Processing started")
logger.info("Step 1 complete")
logger.warning("Warning: retry attempt 1")  # ← triggers flush: debug + info + this warning all emitted
logger.debug("Post-warning debug")           # ← buffered again (new buffer)

set_correlation_id("request-456")
logger.debug("Other request started")
logger.info("Other request step 1")          # ← buffered, NOT flushed (different correlation)
```

## Lifecycle

```
┌──────────────────────────────────────┐
│ Application Startup                  │
│ ┌──────────────────────────────────┐ │
│ │ console_handler = StreamHandler()│ │
│ │ config = FlushOnWarningConfig()  │ │
│ │ flush_handler = FlushOnWarning   │ │
│ │   Handler(config)                │ │
│ │ logger.addHandler(flush_handler) │ │
│ └──────────────────────────────────┘ │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│ Request Arrives                      │
│ set_correlation_id("req-abc123")     │
└──────────────┬───────────────────────┘
               │
               ↓
┌──────────────────────────────────────┐
│ DEBUG Record Emitted                 │
│ logger.debug("Processing started")   │
│                                      │
│ ↓ FlushOnWarningHandler.emit()       │
│   • Get correlation_id from record   │
│   • Level < WARNING? ─→ BUFFER       │
│   • Store in buffers["req-abc123"]   │
│   • Target handler NOT called        │
│                                      │
│ Result: No output to console yet     │
└──────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│ INFO Record Emitted                  │
│ logger.info("Step 1 complete")       │
│                                      │
│ ↓ FlushOnWarningHandler.emit()       │
│   • Level < WARNING? ─→ BUFFER       │
│   • Append to buffers["req-abc123"]  │
│   • Target handler NOT called        │
│                                      │
│ Result: No output to console yet     │
└──────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│ WARNING Record Emitted               │
│ logger.warning("Retry attempt 1")    │
│                                      │
│ ↓ FlushOnWarningHandler.emit()       │
│   • Level >= WARNING? ─→ FLUSH       │
│   • Drain buffers["req-abc123"]      │
│   • For each buffered record:        │
│     └─ target_handler.emit(record)   │
│       [DEBUG and INFO to console]    │
│   • Clear buffers["req-abc123"]      │
│   • Emit WARNING to target_handler   │
│       [WARNING to console]           │
│   • Delete buffered records          │
│                                      │
│ Output to console:                   │
│ DEBUG... [req-abc123] Processing...  │
│ INFO.... [req-abc123] Step 1...      │
│ WARNING. [req-abc123] Retry...       │
└──────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│ DEBUG After Flush                    │
│ logger.debug("Post-warning debug")   │
│                                      │
│ ↓ FlushOnWarningHandler.emit()       │
│   • Level < WARNING? ─→ BUFFER (new) │
│   • buffers["req-abc123"] created    │
│     (previous buffer was cleared)    │
│   • Target handler NOT called        │
│                                      │
│ Result: No output to console         │
└──────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│ TTL Eviction (Example)               │
│ 300+ seconds pass, no new records    │
│ for "req-xyz789" arrive              │
│                                      │
│ ↓ Next record emitted (any corr.)    │
│   • FlushOnWarningHandler.emit()     │
│   • _evict_expired_buffers() runs    │
│   • Scan _timestamps for old entries │
│   • "req-xyz789" > 300s old? ─→ DROP │
│   • buffers["req-xyz789"] deleted    │
│   • Buffered records lost (no flush) │
│                                      │
│ Result: Silently evicted             │
└──────────────────────────────────────┘
             │
             ↓
┌──────────────────────────────────────┐
│ Request Completes                    │
│ clear_correlation_id()               │
└──────────────────────────────────────┘
```

## Comparison to stdlib.MemoryHandler

| Feature | MemoryHandler (stdlib) | FlushOnWarningHandler (mixin_logging) |
|---------|------------------------|---------------------------------------|
| Buffer scope | Global (all records) | Per-correlation (isolated trails) |
| Flush trigger | Single threshold + capacity | WARNING+ per correlation |
| TTL eviction | No | Yes (default 300s, lazy) |
| Global cap | capacity only | max_correlations + capacity |
| Thread-safety | Via Handler lock | Via Handler lock |
| Correlation awareness | No | Yes (context-aware per ContextVar) |

## See Also

- **Adapters overview:** `docs/apps/adapters/README.md`
- **stdlib Filter:** `docs/apps/adapters/stdlib.md`
- **Diagram:** `docs/apps/adapters/diagrams.md` (Flush-on-Warning Handler)
- **Correlation Context:** `docs/apps/context/correlation.md`
