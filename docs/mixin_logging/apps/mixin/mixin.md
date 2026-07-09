# logging-mixin. LoggingMixin Class

> **Location:** `logging-mixin/docs/apps/mixin/mixin.md`
> **Status:** Built and ready for use
> **Code:** `mixin_logging/mixin/mixin.py`
> **Sibling docs:** `docs/apps/context/correlation.md`, `docs/apps/decorators/logged.md`.

## Overview

`LoggingMixin` is the foundational base class for services that need per-class structured logging with automatic correlation ID injection. Instance methods inherit a logger and convenience methods to emit structured events with zero per-instance overhead (`__slots__ = ()`).

## Interface

```python
from logging import Logger
from mixin_logging import LoggingMixin

class LoggingMixin:
    """Mixin providing structured logging + correlation ID injection for service classes."""
    
    __slots__ = ()
    """Empty slots; preserves slotted-dataclass subclasses' memory efficiency."""
    
    @property
    def _logger(self) -> Logger:
        """Per-class logger named `<module>.<ClassName>` (e.g., `myapp.services.OrderService`)."""
    
    def _log_extra(self, extra: dict[str, Any]) -> dict[str, Any]:
        """Build the log `extra` dict: includes correlation_id + caller's explicit kwargs. Masking is caller's responsibility (not composed here)."""
    
    def log_debug(self, event: str, **extra: Any) -> None:
        """Emit a DEBUG-level event with auto-injected correlation_id + class context."""
    
    def log_info(self, event: str, **extra: Any) -> None:
        """Emit an INFO-level event with auto-injected correlation_id + class context."""
    
    def log_warning(self, event: str, **extra: Any) -> None:
        """Emit a WARNING-level event with auto-injected correlation_id + class context."""
    
    def log_error(self, event: str, **extra: Any) -> None:
        """Emit an ERROR-level event with auto-injected correlation_id + class context."""
    
    def log_exception(self, event: str, **extra: Any) -> None:
        """Emit an ERROR-level event with traceback (call inside an except block)."""
```

## Usage

```python
from dataclasses import dataclass
from mixin_logging import LoggingMixin

@dataclass(frozen=True, slots=True)
class OrderService(LoggingMixin):
    """Service class combining LoggingMixin with frozen slotted dataclass."""
    
    db_url: str
    
    def process_order(self, order_id: str, amount: float) -> dict:
        """Process an order and emit structured logs with correlation_id."""
        self.log_info("order.received", order_id=order_id, amount=amount)
        
        try:
            result = self._store_order(order_id, amount)
            self.log_info("order.stored", result=result)
        except Exception:
            self.log_exception("order.store_failed", order_id=order_id)
            raise
        
        return result
    
    def _store_order(self, order_id: str, amount: float) -> dict:
        # Service logic here
        return {"order_id": order_id, "status": "confirmed"}

# Usage:
from mixin_logging import set_correlation_id

set_correlation_id("req-12345")
svc = OrderService(db_url="postgresql://...")
result = svc.process_order("ORD-123", 99.99)

# Logs emitted (all include correlation_id="req-12345"):
# - order.received (event, order_id, amount, correlation_id)
# - order.stored (event, result, correlation_id)
# Or on exception:
# - order.store_failed (event, order_id, correlation_id, + exception traceback)
```

## How Correlation ID Injection Works

Every log event automatically includes the current `correlation_id` from the correlation module (see `docs/apps/context/correlation.md`):

1. **Set correlation ID at request entry** (e.g., in middleware, handler, or async task):
   ```python
   from mixin_logging import set_correlation_id
   set_correlation_id("req-12345")
   ```

2. **Service methods automatically pick it up**:
   ```python
   svc = OrderService(db_url="...")
   svc.process_order("ORD-123", 99.99)
   # All logs from svc.log_* include correlation_id="req-12345" in the extra dict
   ```

3. **`_log_extra()` is called per-event** (not cached), so it always reflects the current correlation ID, supporting multi-step workflows that update correlation ID mid-request.

**Fallback:** If no correlation ID is set, `_log_extra` injects `correlation_id="-"`.

## Masking. Caller's Responsibility

`LoggingMixin` does **not** compose with or mask sensitive fields, masking is **decoupled by design** and is the caller's responsibility.

If your service class has sensitive data (e.g., SSN, API keys), the caller must explicitly pass masked data to `log_*` methods:

```python
from dataclasses import dataclass
from mixin_logging import LoggingMixin
from pii_aware_mixin import phi_aware

@dataclass(frozen=True, slots=True)
@phi_aware
class OrderService(LoggingMixin):
    customer_ssn: str
    
    def mask_for_logging(self) -> dict[str, Any]:
        """Return sensitive fields masked for logs."""
        return {"customer_ssn": "***-**-****"}
    
    def process_customer(self, cust_id: str) -> dict:
        # Caller explicitly passes masked data:
        self.log_info("customer.processing", **self.mask_for_logging(), cust_id=cust_id)
        # ... processing logic ...
        return {"status": "ok"}
```

This separation preserves `LoggingMixin`'s framework-neutral scope and avoids hidden masking contracts.

## Instance-Only Behavior

`LoggingMixin` methods are available only on **instances**, not on class or static methods:

```python
class OrderService(LoggingMixin):
    def process_order(self, order_id: str) -> dict:
        self.log_info("processing")  # OK
        return {}
    
    @classmethod
    def from_config(cls, config: dict):
        # cls.log_info(...) would fail :  LoggingMixin methods are instance-bound
        return cls()
    
    @staticmethod
    def validate_order(order_id: str) -> bool:
        # No access to self.log_info here
        return True
```

For cross-class logging in class/static contexts, use the stdlib logging module directly.

## When to Use

- Every service/repository/handler class that performs side effects (DB writes, API calls, async tasks).
- Public methods that warrant start/error visibility (pair with `@logged` decorator).
- Multi-step workflows where correlation ID tracing is valuable for debugging.

## What It Does NOT Do

- **No automatic exception catching**, for exception handling, pair with `@logged` or explicit try/except.
- **No performance metrics**, duration/timing are a separate concern (observability-engineer's domain).
- **No automatic masking**, `LoggingMixin` does not inspect or mask sensitive data; callers must explicitly pass masked values via `**extra` (e.g., `self.log_info("event", **self.mask_for_logging())`).
- **No pii-aware composition**, fully decoupled from `pii-aware-mixin`; logging-mixin has no knowledge of PII or masking concerns.
