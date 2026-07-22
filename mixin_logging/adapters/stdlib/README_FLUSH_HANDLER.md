# FlushOnWarningHandler: Correlation-Aware Buffering with Flush-on-WARNING

A pure-stdlib `logging.Handler` that buffers records per correlation ID and flushes buffered trails when a WARNING+ record arrives for that correlation.

## Why?

When debugging multi-step workflows (Celery tasks, batch processors, multi-minute flows), successful operations produce verbose DEBUG/INFO logs that clutter the output. Failures generate WARNING/ERROR records. This handler buffers the verbose trail per correlation and only materializes it when a failure occurs - combining the clarity of minimal logging with the debuggability of full context on error.

## How?

**Buffering** (below `flush_level`, default WARNING):
```
logger.debug("step 1")  → buffered (invisible)
logger.info("step 2")   → buffered (invisible)
logger.debug("step 3")  → buffered (invisible)
```

**Flushing** (on WARNING+ for that correlation):
```
logger.warning("failed") → drain buffer (debug, info, debug emitted to output)
                        → emit warning to output
                        → clear buffer for this correlation
```

**Other correlations untouched**:
- Correlation A's WARNING does NOT flush Correlation B's buffer (key difference vs stdlib `MemoryHandler`).
- Each correlation has independent buffering and TTL.

## Installation

Included in `mixin-logging` >= 0.3.0.

```python
from mixin_logging.adapters.stdlib import FlushOnWarningHandler, FlushOnWarningConfig
```

## Usage

### Basic Setup

```python
import logging
from mixin_logging.adapters.stdlib import (
    FlushOnWarningConfig,
    FlushOnWarningHandler,
    CorrelationLogFilter,
)
from mixin_logging import set_correlation_id

# Target handler (where records eventually go)
file_handler = logging.FileHandler("app.log")
file_formatter = logging.Formatter(
    "%(asctime)s - [%(correlation_id)s] - %(levelname)s - %(message)s"
)
file_handler.setFormatter(file_formatter)

# Wrap with flush-on-warning buffer
config = FlushOnWarningConfig(
    target_handler=file_handler,
    flush_level=logging.WARNING,  # flush on WARNING+
    ttl_seconds=300,              # evict old buffers after 5 min
    capacity=1000,                # max records per correlation
    max_correlations=100,         # max concurrent buffers
)
buffer_handler = FlushOnWarningHandler(config)

# Attach to logger
logger = logging.getLogger(__name__)
logger.addHandler(buffer_handler)

# Add correlation filter to stamp correlation_id on records
CorrelationLogFilter.add_correlation_filter(logger)

logger.setLevel(logging.DEBUG)

# Use in application
set_correlation_id("task-123")
logger.debug("Processing started")
logger.info("Step 1 complete")
logger.warning("Retry needed")  # ← Triggers flush and output
```

### Config Parameters

- **`target_handler`** (required): The `logging.Handler` to emit records to (file, stream, CloudWatch, etc.).
- **`flush_level`** (default `logging.WARNING`): Minimum severity to trigger a flush. Must be >= `logging.WARNING`.
- **`ttl_seconds`** (default `300`): Buffer eviction age in seconds (lazy, no background threads).
- **`capacity`** (default `1000`): Max records buffered per correlation (enforced via `deque(maxlen)`; oldest dropped on overflow).
- **`max_correlations`** (default `100`): Max concurrent buffers; oldest correlation evicted when exceeded.

All config is immutable (frozen dataclass) and validated on construction.

## Verified Example

A flow with two correlations: Request-A emits a warning (triggers flush), Request-B buffers silently until its own warning arrives.

### Code

```python
import logging
from mixin_logging.adapters.stdlib import (
    FlushOnWarningConfig,
    FlushOnWarningHandler,
    CorrelationLogFilter,
)
from mixin_logging import set_correlation_id, clear_correlation_id

console_handler = logging.StreamHandler()
console_formatter = logging.Formatter(
    "%(name)s - %(levelname)s - [%(correlation_id)s] - %(message)s"
)
console_handler.setFormatter(console_formatter)

config = FlushOnWarningConfig(
    target_handler=console_handler,
    flush_level=logging.WARNING,
)
flush_handler = FlushOnWarningHandler(config)

logger = logging.getLogger("demo")
logger.addHandler(flush_handler)
logger.addFilter(CorrelationLogFilter())
logger.setLevel(logging.DEBUG)

# Scenario 1: Request-A processes then fails
set_correlation_id("request-A")
logger.debug("Starting request processing")
logger.info("Database query completed")
logger.debug("Validation passed")
logger.warning("Retry required - connection timeout")

# Scenario 2: Request-B processes without warning (buffered, no output yet)
set_correlation_id("request-B")
logger.debug("Starting request processing")
logger.info("Database query completed")
logger.debug("Validation passed")
logger.info("Request completed successfully")

# Scenario 3: Request-B timeout (now triggers flush)
set_correlation_id("request-B")
logger.warning("Timeout: request took too long")

clear_correlation_id()
```

### Output

```
--- Scenario 1: Request-A (processes, then WARNING triggers flush) ---
demo - DEBUG - [request-A] - Starting request processing
demo - INFO - [request-A] - Database query completed
demo - DEBUG - [request-A] - Validation passed
demo - WARNING - [request-A] - Retry required - connection timeout

--- Scenario 2: Request-B (processes without WARNING) ---

--- Scenario 3: Request-B timeout (WARNING triggers flush of buffered records) ---
demo - DEBUG - [request-B] - Starting request processing
demo - INFO - [request-B] - Database query completed
demo - DEBUG - [request-B] - Validation passed
demo - INFO - [request-B] - Request completed successfully
demo - WARNING - [request-B] - Timeout: request took too long
```

**Observations:**

1. **Scenario 1:** Request-A's DEBUG, INFO, DEBUG records are emitted immediately when the WARNING arrives (oldest first), followed by the warning itself.
2. **Scenario 2:** Request-B's records remain buffered (no output) because no WARNING occurred for Request-B during this phase.
3. **Scenario 3:** Request-B's buffered DEBUG, INFO, DEBUG, INFO records all flush when its WARNING arrives, preserving the order.

**Key difference from stdlib `MemoryHandler`:** Request-A's warning does NOT affect Request-B's buffer - each correlation is isolated.

## Design Notes

- **Per-correlation buffering:** Only the failing correlation's trail materializes; successful operations leave no log output.
- **No background threads:** TTL eviction is lazy (triggered on next emit), using `time.time()` comparisons.
- **Capacity-capped:** Both per-correlation (`deque(maxlen)`) and globally (`max_correlations`); evicts oldest on overflow.
- **Thread-safe:** Uses stdlib `Handler` acquire/release lock discipline (no extra locks needed).
- **Null correlation handling:** Records with no correlation ID (unset ContextVar) are buffered separately under a designated bucket.

## Comparison to Alternatives

### vs. stdlib `MemoryHandler`

| Feature | MemoryHandler | FlushOnWarningHandler |
|---------|---------------|-----------------------|
| Buffer scope | Global | Per-correlation |
| Flush target | Single global capacity | Distributed per correlation |
| TTL eviction | No | Yes (lazy, configurable) |
| Correlation awareness | No | Yes (via ContextVar) |

### vs. Structured Logging (JSON/Key-value)

Both are complementary:
- Structured logging: enriches every record with consistent fields (easier aggregation and filtering in centralized log platforms).
- Flush-on-warning buffer: selectively suppresses verbose trails on success, materializing only on failure.

Use both together: flush-on-warning handler + CorrelationLogFilter (adds correlation_id field) + structured formatter.

## Thread Safety

The handler respects the standard `logging.Handler` lock discipline via `self.acquire()` and `self.release()` (inherited from the base class). All internal data structures (`_buffers`, `_timestamps`, `_correlation_order`) are accessed only within the `emit()` method, which is serialized by the handler's lock. No separate thread-safety measures required.

## See Also

- **CorrelationLogFilter:** `mixin_logging/adapters/stdlib/stdlib_client.py` - Stamps correlation_id onto every record.
- **Correlation Context:** `mixin_logging/context/correlation/` - ContextVar machinery for managing correlation IDs.
- **Audit/Review:** `docs/mixin_logging/audits/` - Security and design audits.
- **Full documentation:** `docs/mixin_logging/apps/adapters/flush-handler.md`.
