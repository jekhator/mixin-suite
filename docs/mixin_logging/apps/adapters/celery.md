# logging-mixin. Celery Adapter

> **Location:** `logging-mixin/docs/apps/adapters/celery.md`
> **Status:** Implemented. Task-boundary correlation-ID propagation via celery signals.
> **Code location:** `mixin_logging/adapters/celery/` (`celery_objects.py` + `celery_client.py`); constants in `mixin_logging/adapters/constants/celery.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Celery Task Propagation Lifecycle).
> **Sibling docs:** `docs/apps/adapters/botocore.md`, `docs/apps/context/correlation.md`.

## Purpose

Propagate the current correlation ID across the celery producer (task publisher) / consumer (worker) boundary so a single inbound request that spawns celery tasks can be traced through every task execution and back into CloudWatch logs and audit trails.

## Category

Task-Boundary Propagation, distinct from HTTP-propagation adapters (ASGI/WSGI/httpx/requests). Uses celery signals rather than middleware or event-hook registration.

## Behavior

- `CorrelationSignals.connect()` registers three signal handlers on the celery signal bus (weak=False to survive garbage collection):
  - `before_task_publish` → `inject_on_publish`: write the current correlation ID into task message headers (producer side).
  - `task_prerun` → `restore_on_prerun`: restore the correlation ID from task headers into context (worker side).
  - `task_postrun` → `clear_on_postrun`: clear context after task completes (worker side).
- On task publish, `inject_on_publish` reads the current correlation ID from the `ContextVar` via `CeleryCorrelation.from_context()`. If it is unset or unsafe the handler is a no-op; otherwise it sets the correlation ID into the `headers` dict (a mutable mapping provided by celery's publish signal).
- On task prerun, `restore_on_prerun` extracts the correlation ID from `task.request.headers` (the headers that were published with the task), validates it, and calls `set_correlation_id()` to make it available to the task body.
- On task postrun, `clear_on_postrun` unconditionally clears the context to prevent task-to-task leakage.

## Value Object

`CeleryCorrelation` (frozen, slots) captures the `correlation_id` bound for task-message headers:

- `from_context()`. read the ContextVar; returns `None` if unset or unsafe (no raise).
- `header_pair`. returns `(CORRELATION_ID_HEADER, correlation_id)`.
- `__post_init__` + `_is_safe`. reject empty values, values over 128 chars, and values containing CR / LF / null.

## Signal Handler Surface

`CorrelationSignals` (frozen, slots) provides the stateless signal-hook interface:

- `connect()`. register all three handlers on the celery signal bus (to be called once at app/worker initialization).
- `inject_on_publish(headers, **kwargs)`. classmethod invoked by celery's `before_task_publish` signal; injects the correlation ID into the outgoing task headers.
- `restore_on_prerun(task, **kwargs)`. classmethod invoked by celery's `task_prerun` signal; restores the correlation ID from task headers into the current context.
- `clear_on_postrun(**kwargs)`. classmethod invoked by celery's `task_postrun` signal; clears the context unconditionally.

## Constants

`mixin_logging/adapters/constants/celery.py`:

- `CORRELATION_ID_HEADER = "X-Correlation-ID"` (matches inbound ASGI/WSGI for round-trip consistency)
- `CORRELATION_ID_MAX_LENGTH = 128`
- `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})`
- `ERR_CORRELATION_ID_UNSAFE`

## Compatibility

celery 5.x / 6.x (any broker: Redis, RabbitMQ, etc.). No package extra is required on install (extra: `[celery]` gates the adapter's import), and any caller already has celery as a dependency if they use this adapter.

## Example Usage

```python
from celery import Celery
from mixin_logging.adapters.celery.celery_client import CorrelationSignals

app = Celery("myapp")
app.conf.broker_url = "redis://localhost:6379/0"

CorrelationSignals.connect()

@app.task
def process_order(order_id):
    svc = OrderService()
    svc.process(order_id)
    # Logs automatically include correlation_id via LoggingMixin

if __name__ == "__main__":
    app.worker_main()
```

## Lifecycle

```
┌─────────────────────────────────┐
│ HTTP Request (ASGI/WSGI)        │
│ _client.set_id("req-abc123")    │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ Application: task.delay()       │
│ before_task_publish signal      │
│ ↓ inject_on_publish             │
│ headers["X-Correlation-ID"]     │
│ = "req-abc123"                  │
└────────────┬────────────────────┘
             │
             ↓
        (Task in broker)
             │
             ↓
┌─────────────────────────────────┐
│ Celery Worker: task dequeued    │
│ task_prerun signal              │
│ ↓ restore_on_prerun             │
│ _client.set_id("req-abc123")    │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ Task Body: @app.task def ...    │
│ LoggingMixin logs:              │
│ correlation_id="req-abc123"     │
└────────────┬────────────────────┘
             │
             ↓
┌─────────────────────────────────┐
│ Task Complete                   │
│ task_postrun signal             │
│ ↓ clear_on_postrun              │
│ _client.clear()                 │
└─────────────────────────────────┘
```

## See Also

- **Adapters overview / Botocore:** `docs/apps/adapters/botocore.md`
- **Diagram:** `docs/apps/adapters/diagrams.md` (Celery Task Propagation Lifecycle)
- **Correlation Context:** `docs/apps/context/correlation.md`
