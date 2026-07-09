# logging-mixin. Correlation Context

> **Location:** `logging-mixin/docs/apps/context/correlation.md`
> **Status:** Living reference. Updated 2026-06-04.
> **Code:** `mixin_logging/context/correlation/` (two-file layout: `correlation_objects.py` + `correlation_client.py`)
> **Sibling docs:** `docs/architecture/architecture.md`, `docs/apps/decorators/logged.md`, `docs/apps/context/diagrams.md`.

## Two-File Layout: Value Object + Ops Holder

The correlation subsystem is split across two files for clean separation of concerns:

1. **`correlation_objects.py`**, `CorrelationContext` frozen dataclass (the value object).
2. **`correlation_client.py`**, `ContextVarClient` frozen dataclass + `_client` singleton (the ops holder).

This structure ensures the value object (`CorrelationContext`) has no dependencies on Python's `ContextVar` machinery, while the client encapsulates all context-var lifecycle operations.

## `CorrelationContext`. Frozen Dataclass for Distributed Tracing

Carries a `correlation_id` across async task boundaries for request/job tracing. Implemented as a **frozen dataclass** aligned with `dto-strict` standards; accessed via `ContextVarClient` singleton for framework-neutral context-var management.

### Definition

**File: `mixin_logging/context/correlation/correlation_objects.py`**

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class CorrelationContext:
    """Correlation context carried across async boundaries for distributed tracing."""
    correlation_id: str | None

    @property
    def is_set(self) -> bool:
        """Return True when a correlation id is present."""
        return self.correlation_id is not None
```

**File: `mixin_logging/context/correlation/correlation_client.py`**

```python
from contextvars import ContextVar
from dataclasses import dataclass

from . import correlation_objects as objs

@dataclass(frozen=True, slots=True)
class ContextVarClient:
    """Owns the correlation ContextVar and its current/set/clear operations."""
    
    correlation_ctx: ContextVar[objs.CorrelationContext]

    def current_id(self) -> str | None:
        """Return the current correlation id, or None if unset."""
        return self.correlation_ctx.get().correlation_id

    def set_id(self, value: str) -> None:
        """Set the correlation id for the current context (tasks, jobs, cross-service)."""
        self.correlation_ctx.set(objs.CorrelationContext(value))

    def clear(self) -> None:
        """Reset the correlation context to unset."""
        self.correlation_ctx.set(objs.CorrelationContext(None))


_client: ContextVarClient = ContextVarClient(
    ContextVar("correlation_ctx", default=objs.CorrelationContext(None))
)
```

### Public API & Re-exports

Both `CorrelationContext` and `ContextVarClient` are imported in the top-level public API:

```python
# mixin_logging/__init__.py (curated public API)
from .correlation.correlation_client import ContextVarClient, _client
from .correlation.correlation_objects import CorrelationContext

__all__ = [..., "ContextVarClient", "CorrelationContext", "_client", ...]
```

The internal subpackage `__init__.py` is now empty (docstring only), with no re-exports. Public integrators import from the top level:

```python
from mixin_logging import CorrelationContext, ContextVarClient, _client
```

### Access Layer

The public API is provided by module-level functions (or methods on `_client`):

```python
from mixin_logging import set_correlation_id, get_correlation_id, clear_correlation_id

def get_correlation_id() -> str | None:
    """Return the current correlation id, or None if unset."""
    # Wraps _client.current_id()

def set_correlation_id(value: str) -> None:
    """Set the correlation id for the current context (tasks, jobs, cross-service)."""
    # Wraps _client.set_id(value)

def clear_correlation_id() -> None:
    """Reset the correlation context to unset."""
    # Wraps _client.clear()
```

### Usage

#### In Application Code

```python
from mixin_logging import set_correlation_id, get_correlation_id
import uuid

# At request entry (e.g., HTTP middleware):
correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
set_correlation_id(correlation_id)

# In downstream service methods:
svc = MyService()  # MyService inherits LoggingMixin
result = svc.process()  # Will auto-include correlation_id in log events

# At request exit (cleanup):
clear_correlation_id()
```

#### With Async Tasks

`CorrelationContext` is stored in a `ContextVar`, which is **automatically inherited by child async tasks**:

```python
import asyncio
from mixin_logging import set_correlation_id, get_correlation_id

async def main():
    set_correlation_id("req-001")
    
    # Both tasks inherit the parent's correlation_id:
    await asyncio.gather(
        background_job_1(),  # sees "req-001"
        background_job_2()   # sees "req-001"
    )

async def background_job_1():
    cid = get_correlation_id()  # Returns "req-001"
    # ... log events with same correlation_id
```

### Integrations

See `docs/apps/adapters/README.md` for the complete adapter suite. Common inbound integrations:

#### WSGI (Django, Flask, Pyramid)

Provided by `mixin_logging.adapters.wsgi.CorrelationIdMiddleware`:

```python
MIDDLEWARE = [
    # ... other middleware
    "mixin_logging.adapters.wsgi.CorrelationIdMiddleware",
]
```

Extracts `X-Correlation-ID` header; generates UUID if missing.

#### ASGI (FastAPI, Starlette, Quart)

Provided by `mixin_logging.adapters.asgi.CorrelationIdMiddleware`:

```python
from fastapi import FastAPI
from mixin_logging.adapters.asgi import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)
```

#### AWS Lambda (Serverless)

Provided by `mixin_logging.adapters.cloud.CloudSetup`:

```python
from mixin_logging.adapters.cloud import CloudSetup

def lambda_handler(event, context):
    CloudSetup.setup_correlation_id(event, context)
    svc = MyService()
    return svc.process(event)
```

### Design Notes

#### `is_set` Property

`CorrelationContext.is_set` is a convenience property for checking whether a correlation_id is present:

```python
ctx = CorrelationContext(None)
assert not ctx.is_set  # True (is_set returns False)

ctx = CorrelationContext("req-001")
assert ctx.is_set  # True
```

This replaces the previous pattern of checking against an empty string sentinel (`""`). Now `None` is the native "unset" value, aligned with Python's type system and `Optional` semantics.

#### Async Safety

The `ContextVar` ensures each asyncio task (or thread, per `threading.local` semantics) gets its own isolated `correlation_id`:

```python
async def task_a():
    set_correlation_id("task-a")
    await asyncio.sleep(1)
    # Still sees "task-a", not "task-b"

async def task_b():
    set_correlation_id("task-b")
    await asyncio.sleep(1)
    # Still sees "task-b", not "task-a"

await asyncio.gather(task_a(), task_b())
```

No manual cleanup needed if the task is properly scoped; `ContextVar` inherits to child tasks and resets when a task exits.

#### Immutability

`CorrelationContext` is frozen (`@dataclass(frozen=True, slots=True)`), a new instance must be created to change the correlation_id:

```python
set_correlation_id("new-id")  # Internally: _correlation_ctx.set(CorrelationContext("new-id"))
```

This prevents accidental mutation and integrates cleanly with audit trails (all context state is deterministic and immutable by construction).

### When to Use

- **Request-scoped tracing:** HTTP endpoints, webhooks, Lambda invocations.
- **Job/queue processing:** Background tasks, SQS/SNS handlers, Celery tasks.
- **Cross-service calls:** Propagate `X-Correlation-ID` header upstream/downstream for end-to-end visibility.
- **Audit trails:** Each log event automatically includes the correlation_id (injected by `LoggingMixin`).

### What It Does NOT Do

- **No auto-propagation to HTTP clients**, framework adapters handle header injection (see integrations above).
- **No storage/persistence**, purely in-memory; for persistence, use the correlation_id in audit-trail records.
- **No automatic header extraction**, framework adapters (Django middleware, FastAPI, Lambda) handle extraction; application code just calls `set_correlation_id()`.
