# Correlation Context. Container Diagram

> **Location:** `docs/apps/context/diagrams.md`
> **Status:** Canonical. Visual reference for the two-file correlation subsystem layout, field provenance, method signatures, and consumer integration points.
> **Updated:** 2026-06-04.

## Correlation Subsystem Structure

> **File path:** `mixin_logging/context/correlation/`

```
mixin_logging/context/correlation/correlation_objects.py
================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationContext                      ← request-scoped correlation ID value object
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id : str | None                  (None when unset; carried across async/task boundaries via ContextVar)
  │
  └─ [prp] is_set -> bool                         ← True if correlation_id is not None


mixin_logging/context/correlation/correlation_client.py
================================================
  Imports: from __future__ import annotations
           from contextvars import ContextVar
           from dataclasses import dataclass
           from mixin_logging.context.constants import correlation as const
           from mixin_logging.context.correlation import correlation_objects as objs

──────────────────────────────────────────────────────────────────────────
[FROZEN]  ContextVarClient                        ← owns the correlation ContextVar
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_ctx : ContextVar[objs.CorrelationContext]
  │
  ├─ [mth] current_id(self) -> str | None         ← return correlation_ctx.get().correlation_id
  ├─ [mth] set_id(self, value: str) -> None       ← correlation_ctx.set(CorrelationContext(value))
  └─ [mth] clear(self) -> None                    ← correlation_ctx.set(CorrelationContext(None))

  Module singleton + public aliases:
    _client = ContextVarClient(
        ContextVar(const.CORRELATION_CONTEXT_VAR_NAME, default=CorrelationContext(None)))
    get_correlation_id   = _client.current_id
    set_correlation_id   = _client.set_id
    clear_correlation_id = _client.clear

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/context/constants/correlation.py
──────────────────────────────────────────────────────────────────────────
  CORRELATION_ID_KEY            = "correlation_id"
  UNSET_CORRELATION_ID          = "-"
  CORRELATION_CONTEXT_VAR_NAME  = "correlation_ctx"
```

## Consumer Integration Points

### LoggingMixin Integration

```
┌──────────────────────────────────────────────────────────────────┐
│  LoggingMixin._log_extra (mixin method)                          │
│  ──────────────────────────────────────────────────────────────  │
│                                                                   │
│  def _log_extra(self, extra: dict[str, Any]) -> dict[str, Any]:
│      result = {"correlation_id": _client.current_id() or "-"}   │
│      if extra:                                                    │
│          result.update(extra)                                     │
│      return result                                                │
│                                                                   │
│  → Takes caller's extra dict, always sets correlation_id         │
│    (defaulting to "-" when unset), then merges caller's extra    │
│    into result                                                    │
└──────────────────────────────────────────────────────────────────┘
```

### Task Entry/Exit Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│  Async Task / Job Handler (e.g., Celery task, background job)  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Entry:                                                         │
│    correlation_id = extract_from_header_or_event()             │
│    _client.set_id(correlation_id)  # SET context               │
│                                                                  │
│  Execution:                                                     │
│    service_method()  # Inherits correlation_id via ContextVar │
│    logger.info(...)  # Auto-includes via LoggingMixin          │
│                                                                  │
│  Exit:                                                          │
│    _client.clear()  # RESET context                            │
│                                                                  │
│  → Ensures clean context isolation between tasks               │
└─────────────────────────────────────────────────────────────────┘
```

### HTTP Middleware Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│  Django/FastAPI/Lambda Middleware                               │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  Request Entry:                                                 │
│    cid = request.headers.get("X-Correlation-ID") or uuid4()    │
│    _client.set_id(cid)  # SET context                          │
│    response = handler(request)                                 │
│    _client.clear()  # RESET context                            │
│    return response                                              │
│                                                                  │
│  → All downstream handlers auto-inherit correlation_id         │
└─────────────────────────────────────────────────────────────────┘
```

## Field Provenance & Sensitivity

| Field | Type | Origin | Sensitivity |
|-------|------|--------|-------------|
| `correlation_id` | `str \| None` | Request header / UUID generation / explicit call | **Tracing only**, not PII; aggregable across logs for distributed trace reconstruction |

## Async Safety Semantics

The `ContextVar` backed by `ContextVarClient` ensures:

- **Child task isolation:** Each asyncio task / thread inherits the parent's `CorrelationContext` at spawn time.
- **Per-task state:** Changes in a child task do NOT affect parent or sibling contexts.
- **Auto-cleanup:** `ContextVar` resets when a task exits; no manual cleanup needed.

```
Parent Task: set_id("parent-123")
  ├─ Child A: inherits "parent-123", can read current_id()
  ├─ Child B: inherits "parent-123", can read current_id()
  └─ All children's logs include "parent-123" correlation_id
```

## See Also

- **Usage Guide:** `docs/apps/context/correlation.md` (the full reference with framework adapters and examples)
- **Architecture:** `docs/architecture/architecture.md`
