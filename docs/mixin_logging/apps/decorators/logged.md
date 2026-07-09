# logging-mixin, @logged Decorator

> **Location:** `logging-mixin/docs/apps/decorators/logged.md`
> **Status:** Living reference. Updated 2026-06-04.
> **Code:** `mixin_logging/decorators/logged/` (two-file layout: `logged_objects.py` + `logged_client.py`)
> **Diagrams:** `docs/apps/decorators/diagrams.md`
> **Sibling docs:** `docs/architecture/architecture.md`, `docs/apps/context/correlation.md`.

## `@logged(event)`. Class-Based Decorator

Wraps a `LoggingMixin` instance method to emit structured log events at start and error boundaries. Implemented as a **frozen dataclass** (not a function), preserving method signatures via `ParamSpec`/`Concatenate`.

### Definition

`@logged(event)` is a factory-based decorator. Internally, it's an alias to `LoggedClient.for_event`, which constructs a frozen dataclass holding a `LoggedContainer` (the event name and its derived suffixes). See "Internal Structure" below for the full architecture.

**Call-site usage** (what you write):

```python
from mixin_logging import logged, LoggingMixin

class OrderService(LoggingMixin):
    @logged("process_order")
    def process_order(self, order_id: str, amount: float) -> dict:
        """Process an order and return confirmation."""
        return {"order_id": order_id, "status": "confirmed"}
```

**What happens internally**: `logged("process_order")` → `LoggedClient.for_event("process_order")` → `LoggedClient(container=LoggedContainer("process_order"))` → `__call__` wraps the method with start/error logging.

### Usage Examples

#### Method-Level Decoration

```python
from mixin_logging import LoggingMixin, logged

class OrderService(LoggingMixin):
    @logged("process_order")
    def process_order(self, order_id: str, amount: float) -> dict:
        """Process an order and return confirmation."""
        # ... service logic
        return {"order_id": order_id, "status": "confirmed"}

# When called:
svc = OrderService()
result = svc.process_order("ORD-123", 99.99)

# Logs emitted:
# 1. process_order.start
# 2. process_order.error (if exception raised; includes error_type and code if present)
```

#### Class-Level Decoration (v0.6.0+)

Apply `@logged` to a class to auto-log all public methods:

```python
from mixin_logging import LoggingMixin, logged

@logged("order")
class OrderService(LoggingMixin):
    def process(self, order_id: str, amount: float) -> dict:
        """Process an order."""
        return {"order_id": order_id, "status": "confirmed"}

    def refund(self, order_id: str) -> dict:
        """Refund an order."""
        return {"order_id": order_id, "status": "refunded"}

# When called:
svc = OrderService()
result = svc.process("ORD-123", 99.99)
result = svc.refund("ORD-123")

# Logs emitted:
# 1. order.process.start (on process() entry)
# 2. order.process.error (if exception raised)
# 3. order.refund.start (on refund() entry)
# 4. order.refund.error (if exception raised)
```

**Class-level fan-out rules:**
- Applied to all public methods in `cls.__dict__` only (not inherited)
- Skips: private methods (`_*`), dunders (`__*`), properties, nested classes, classmethods, staticmethods
- Explicit method-level `@logged` overrides class-level fan-out
- Each method receives `<event>.<method_name>.start` / `.error` logging

### Zero-Boilerplate Logging with `@logged`

`@logged("event.name")` on a `LoggingMixin` method emits `<event>.start` (INFO) on entry and `<event>.error` (ERROR, with `error_type` + `error_code`) on any exception, then re-raises :  replacing the manual try/except + log_error envelope.

**With @logged**:

```python
@phi_aware
@dataclass(frozen=True, slots=True)
class StripeClient(LoggingMixin):
    api_key: str = field(metadata={"phi": True})

    @logged("stripe.create_intent")
    def create_intent(self, req: objs.CreateIntentRequest) -> objs.SetupIntentResult:
        intent = self._get_stripe().SetupIntent.create(customer=req.customer_id)
        return objs.SetupIntentResult.from_stripe_object(intent)
```

**Same method written manually (what @logged saves you)**:

```python
def create_intent(self, req: objs.CreateIntentRequest) -> objs.SetupIntentResult:
    self.log_info("stripe.create_intent.start")
    try:
        intent = self._get_stripe().SetupIntent.create(customer=req.customer_id)
        return objs.SetupIntentResult.from_stripe_object(intent)
    except Exception as error:
        self.log_error(
            "stripe.create_intent.error",
            error_type=type(error).__name__,
            error_code=getattr(error, "code", None),
        )
        raise
```

**Three important notes:**

1. **Args are not auto-logged** :  the envelope logs the event name only (safe default; no raw args/payload in logs). If you need safe IDs in extras, use a manual `self.log_info(...)` for that line.
2. **Composes with `@phi_aware`** :  masking of `metadata={"phi": True}` fields is orthogonal and independent of `@logged`.
3. **Requires LoggingMixin** :  the decorator calls `instance.log_info/log_error`, so the class must be a `LoggingMixin` subclass.

### Behavior

| Event | When | Emitted via | Includes |
|-------|------|------------|----------|
| `<event>.start` | Method entry | `log_info` | None (event name only) |
| `<event>.error` | Exception caught | `log_error` | `error_type` (class name), `code` (if present on exception) |

After `<event>.error` is logged, the exception is **re-raised unchanged**, `@logged` does NOT wrap or transform the exception. For exception transformation (converting to domain errors), use `domain-errors`' `@translate` decorator in the stack (see "Stacking" below).

### Signature Preservation

The decorator uses `ParamSpec` and `Concatenate` to preserve method signatures:

```python
from typing import Concatenate, ParamSpec, TypeVar

Params = ParamSpec("Params")
Result = TypeVar("Result")
Service = TypeVar("Service", bound=LoggingMixin)

def __call__(self, method: Callable[Concatenate[Service, Params], Result]) -> Callable[Concatenate[Service, Params], Result]:
    # ... preserves (self, *args, **kwargs) as `Concatenate[Service, Params]`
```

This means type checkers (mypy, pyright) see the original method's signature, not an erased `Any`. Parameters and return types are fully introspectable.

### Stacking with `@translate`

When using both `@logged` and `domain-errors`' `@translate` on the same method:

- **Order: `@logged` outer, `@translate` inner**
- `@translate` wraps the method first (inner), so exceptions are transformed before reaching `@logged`'s error handler.
- `@logged` logs the (possibly transformed) exception, then allows `@translate` to return a wrapped error response.

Future integration of exception-translation decorators will follow this pattern: inner decorators transform, outer decorators log the result.

### When to Use

- Every public method on a `LoggingMixin` service class that warrants start/error visibility.
- Methods that cross async boundaries (jobs, webhooks, multi-step operations).
- Does NOT suppress exceptions, for exception handling, pair with `@translate` or explicit try/except.

## Internal Structure (Value Object + Client Pattern)

The `@logged` decorator has been refactored to a **two-file, value-object-plus-client architecture** for clarity and maintainability. This section documents the internal structure so integrators understand the data flow and can extend or inspect the implementation.

### Two-File Layout

**File 1: `logged_objects.py`, `LoggedContainer` (Value Object)**

Holds the base event name and derives the start/error event suffixes.

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class LoggedContainer:
    """Log-event names derived from one decorated operation's base event."""
    event: str
    
    def __post_init__(self) -> None:
        if not self.event:
            raise ValueError("LoggedContainer.event must be non-empty")
    
    @property
    def start(self) -> str:
        """Return the start-event name `<event>.start`."""
        return f"{self.event}{const.EVENT_SUFFIX_START}"
    
    @property
    def error(self) -> str:
        """Return the error-event name `<event>.error`."""
        return f"{self.event}{const.EVENT_SUFFIX_ERROR}"
```

**Key characteristics:**
- Frozen dataclass (`@dataclass(frozen=True, slots=True)`), immutable value object.
- Rejects empty events via `__post_init__` validation.
- Derives event names via properties (`.start`, `.error`) using constants from `mixin_logging.constants.decorators`.

**File 2: `logged_client.py`, `LoggedClient` (Decorator Implementation)**

Wraps a `LoggedContainer` and implements the `__call__` interface to decorate methods.

```python
from dataclasses import dataclass
from typing import Concatenate, ParamSpec, TypeVar

@dataclass(frozen=True, slots=True)
class LoggedClient:
    """Decorate a LoggingMixin method to emit <event>.start / <event>.error, then re-raise."""
    
    container: objs.LoggedContainer
    
    @classmethod
    def for_event(cls, event: str) -> LoggedClient:
        """Factory from a base event name."""
        return cls(objs.LoggedContainer(event))
    
    def __call__(
        self, method: Callable[Concatenate[Service, Params], Result]
    ) -> Callable[Concatenate[Service, Params], Result]:
        """Wrap a LoggingMixin method with the start/error logging envelope."""
        @functools.wraps(method)
        def wrapper(instance: Service, *args: Params.args, **kwargs: Params.kwargs) -> Result:
            instance.log_info(self.container.start)
            try:
                return method(instance, *args, **kwargs)
            except Exception as error:
                instance.log_error(
                    self.container.error,
                    error_type=type(error).__name__,
                    code=getattr(error, "code", None),
                )
                raise
        return wrapper
```

**Key characteristics:**
- Frozen dataclass holding a `LoggedContainer`.
- Factory classmethod `for_event(event)`, constructs a `LoggedClient` from a bare event name.
- `__call__` is the decorator: emits `<event>.start` at method entry, catches exceptions to emit `<event>.error`, then re-raises unchanged.
- Signature preservation via `ParamSpec`/`Concatenate`, type checkers see the original method signature.

### Public Entry Point

```python
logged = LoggedClient.for_event
```

The public logged export is a convenience alias to the factory classmethod. This allows the familiar `@logged("event_name")` call-site syntax:

```python
from mixin_logging import logged, LoggingMixin

class OrderService(LoggingMixin):
    @logged("process_order")  # Calls LoggedClient.for_event("process_order").__call__(method)
    def process_order(self, order_id: str) -> dict:
        return {"status": "ok"}
```

### Internal Data Flow

```
Call site: @logged("my.event")
    ↓
logged = LoggedClient.for_event
    ↓
LoggedClient(container=LoggedContainer("my.event"))
    ↓
__call__(method) → wrapper function
    ↓
On invocation:
  · log_info(container.start)  → "my.event.start"
  · method(...)
  · On exception: log_error(container.error, ...) → "my.event.error"
  · Re-raise unchanged
```

### Event Suffix Constants

Event suffixes are defined in `mixin_logging/decorators/constants/decorators.py`:

```python
EVENT_SUFFIX_START: Final = ".start"
EVENT_SUFFIX_ERROR: Final = ".error"
```

These are accessed by `LoggedContainer` as:

```python
from mixin_logging.decorators.constants import decorators as const

@property
def start(self) -> str:
    return f"{self.event}{const.EVENT_SUFFIX_START}"
```

This centralized approach ensures suffix consistency across all `@logged`-decorated methods and permits future changes to event-naming conventions in one location.

### Import and Re-Export Pattern

All three components (`LoggedContainer`, `LoggedClient`, `logged`) are imported in the top-level public API:

```python
# mixin_logging/__init__.py (curated public API)
from .apps.decorators.logged.logged_client import LoggedClient, logged
from .apps.decorators.logged.logged_objects import LoggedContainer

__all__ = [..., "LoggedClient", "LoggedContainer", "logged", ...]
```

The internal subpackage `__init__.py` files are now empty (docstring only), with no re-exports. Public integrators import from the top level:

```python
from mixin_logging import logged, LoggingMixin

@logged("my.event")
def my_method(self) -> None:
    pass
```

Or, for advanced use (inspecting the container):

```python
from mixin_logging import LoggedClient, LoggedContainer

client = LoggedClient.for_event("my.event")
print(client.container.start)   # "my.event.start"
print(client.container.error)   # "my.event.error"
```

### What It Does NOT Do

- **No exception wrapping**, re-raises unchanged (exception transformation is `@translate`'s job).
- **No result logging**, only start and error events; success leaves no log trail (by design: success is implicit silence).
- **No performance metrics**, duration/timing are a separate concern (observability-engineer's future domain).
- **No automatic argument/masking**, callers are responsible for passing masked values explicitly (e.g., `**self.mask_for_logging()` in `log_info` calls).
