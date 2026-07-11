# logging-mixin. Architecture

> **Location:** `logging-mixin/docs/architecture/architecture.md`
> **Status:** Living reference, updated 2026-06-04. Core and all 8 adapters implemented.
> **Package:** `logging-mixin` (Apache-2.0, py≥3.11), framework-neutral structured-logging mixin.
> **Detailed reference:** See architecture sections below for adapters, context, decorators, and mixin.

## Purpose

Class-bound structured logging for Python services: a per-class logger plus an auto-injected correlation ID for distributed tracing. The core is **framework-neutral** (stdlib logging + `contextvars` only); web frameworks plug in via optional adapters.

## Package Layout

```
mixin_logging/
├── __init__.py                 # Curated public API, imports from defining files
├── py.typed                    # PEP 561 marker for type-checker discovery (empty file)
├── conftest.py                 # Root-level pytest configuration
├── adapters/
│   ├── __init__.py             # Public exports for all adapters
│   ├── asgi/
│   │   ├── __init__.py
│   │   ├── asgi_objects.py
│   │   └── asgi_client.py
│   ├── wsgi/
│   │   ├── __init__.py
│   │   ├── wsgi_objects.py
│   │   └── wsgi_client.py
│   ├── httpx/
│   │   ├── __init__.py
│   │   ├── httpx_objects.py
│   │   └── httpx_client.py
│   ├── requests/
│   │   ├── __init__.py
│   │   ├── requests_objects.py
│   │   └── requests_client.py
│   ├── botocore/
│   │   ├── __init__.py
│   │   ├── botocore_objects.py
│   │   └── botocore_client.py
│   ├── celery/
│   │   ├── __init__.py
│   │   ├── celery_objects.py
│   │   └── celery_client.py
│   ├── cloud/
│   │   ├── __init__.py
│   │   ├── cloud_objects.py
│   │   └── cloud_client.py
│   ├── stdlib/
│   │   ├── __init__.py
│   │   └── stdlib_client.py
│   ├── constants/
│   │   ├── __init__.py
│   │   ├── asgi.py
│   │   ├── wsgi.py
│   │   ├── httpx.py
│   │   ├── requests.py
│   │   ├── botocore.py
│   │   ├── celery.py
│   │   ├── cloud.py
│   │   └── stdlib.py
│   └── tests/
│       ├── test_asgi/{conftest.py, test_asgi_objects.py, test_asgi_client.py}
│       ├── test_wsgi/{conftest.py, test_wsgi_objects.py, test_wsgi_client.py}
│       ├── test_httpx/{conftest.py, test_httpx_objects.py, test_httpx_client.py}
│       ├── test_requests/{conftest.py, test_requests_objects.py, test_requests_client.py}
│       ├── test_botocore/{conftest.py, test_botocore_objects.py, test_botocore_client.py}
│       ├── test_celery/{conftest.py, test_celery_objects.py, test_celery_client.py}
│       ├── test_cloud/{conftest.py, test_cloud_objects.py, test_cloud_client.py}
│       └── test_stdlib/{conftest.py, test_stdlib_client.py}
├── context/
│   ├── __init__.py             # Public exports for context
│   ├── correlation/
│   │   ├── __init__.py
│   │   ├── correlation_objects.py
│   │   └── correlation_client.py
│   ├── constants/
│   │   ├── __init__.py
│   │   └── correlation.py
│   └── tests/
│       └── test_correlation/{conftest.py, test_correlation_objects.py, test_correlation_client.py}
├── decorators/
│   ├── __init__.py             # Public exports for decorators
│   ├── logged/
│   │   ├── __init__.py
│   │   ├── logged_objects.py
│   │   └── logged_client.py
│   ├── constants/
│   │   ├── __init__.py
│   │   └── decorators.py
│   └── tests/
│       └── test_logged/{conftest.py, test_logged_objects.py, test_logged_client.py}
├── mixin/
│   ├── __init__.py             # Public exports for mixin
│   ├── mixin.py
│   └── tests/
│       └── test_mixin/{conftest.py, test_mixin.py}
├── common/
│   ├── __init__.py
│   ├── record_collector/
│   │   └── record_collector.py
│   ├── constants/
│   │   ├── __init__.py
│   │   └── tests.py
│   └── tests/{conftest.py, test_record_collector.py}
├── constants/
│   ├── __init__.py
│   └── public_api.py
└── config/
    ├── __init__.py
    └── _version.py
```

> **Version sourcing:** `config/_version.py` holds the canonical `__version__ string` (currently `"0.3.0"`). The top-level `__init__.py` re-exports it; `pyproject.toml` configures the build to read the same file via `[tool.hatch.version] path = "mixin_logging/config/_version.py"`, ensuring a single source of truth.
>
> **Type marker:** `py.typed` (PEP 561) signals to downstream type-checkers that the package includes inline type hints. Present for mypy, pyright, and other static analyzers.
>
> **Adapters (0.3.0+):** All 8 adapters fully implemented. Framework-integration layer provides inbound (ASGI, WSGI, Cloud), outbound (HTTPX, Requests, Botocore), cross-boundary (Celery), and output-sink (Stdlib) adapters with companion constants modules. Each adapter follows the pattern: `<adapter>/{__init__.py, <adapter>_objects.py, <adapter>_client.py}` with constants in `constants/<adapter>.py`.

## Core Components

| Module | Role |
|---|---|
| `mixin/mixin.py`, `LoggingMixin` | `log_debug/info/warning/error/exception(event, **extra)`; per-class logger `<module>.<ClassName>`; injects `correlation_id`; **decoupled from masking** (caller passes masked values explicitly via `**extra`). Instance-only (not `@classmethod`/`@staticmethod`). |
| `context/correlation/correlation_objects.py` + `correlation_client.py` | Frozen dataclass `CorrelationContext(correlation_id: str \| None)` with `is_set` property; `ContextVarClient` owning the ContextVar + `_client` singleton; `current_id/set_id/clear()` access layer. See `docs/apps/context/correlation.md`. |
| `decorators/logged/logged_objects.py` + `logged_client.py`, `@logged` | Frozen dataclass decorator `@logged(event: str)`, class-based, not function-based. Wraps a `LoggingMixin` method to emit `<event>.start`, catch exceptions and emit `<event>.error`, then re-raise unchanged. Preserves method signatures via `ParamSpec`/`Concatenate`. See `docs/apps/decorators/logged.md`. |

## Design Principles

- **Framework-neutral core**, stdlib logging + `contextvars` only; frameworks via optional adapters. Reusable beyond Django.
- **Instance-bound logging**, methods read `self._logger`; not callable from class/static methods.
- **Root-layout package structure**, `mixin_logging/<concern>/` (no `src/` wrapper); one concern per app dir.
- **Curated public API**, top-level `mixin_logging/__init__.py` is the single source of truth for the public surface. Internal subpackage `__init__.py` files are empty (docstring only, no re-exports). Public users import from the top level: `from mixin_logging import LoggingMixin, logged, CorrelationContext, ...`. Internal code and the top `__init__.py` both import from the defining file (e.g., `from .correlation.correlation_objects import CorrelationContext`), not from subpackage `__init__`s.
- **Decoupled from masking**, `LoggingMixin` does not inspect or compose masking hooks; callers explicitly pass masked data via `**extra`. This preserves framework-neutral scope and avoids hidden dependencies on `pii-aware-mixin`.
- **Frozen dataclasses**, `CorrelationContext`, `ContextVarClient`, `@logged` all use `@dataclass(frozen=True, slots=True)` per `strict-module` standards.

## Adapter Design: ASGI

The **ASGI adapter** (`mixin_logging/adapters/asgi/`) splits into two modules per the object/client pattern:

- **`asgi_objects.py`**. Type aliases (`Scope`, `Message`, `Receive`, `Send`, `App`) and `AsgiCorrelation` value object.
  - `AsgiCorrelation.from_scope()`. Reads untrusted `X-Correlation-ID` header from ASGI scope; validates via `_is_safe()` (rejects CRLF, control chars, oversized IDs >128 bytes, invalid UTF-8); on failure, generates fresh UUID4 hex[:12].
  - `AsgiCorrelation.response_header`. Property returning the safe correlation ID as `(bytes, bytes)` tuple for ASGI response headers.

- **`asgi_client.py`**. Executable middleware (`CorrelationIdMiddleware`) and context-setter (`ASGIApp`).
  - `ASGIApp`. Sets resolved correlation ID into ContextVar, then delegates to wrapped app.
  - `CorrelationIdMiddleware`. Wraps ASGI `send` to inject correlation header on response start; calls `ASGIApp` to set context; clears context in `finally` on exit.

**Security:** Validation-and-regenerate pattern ensures no unsafe correlation ID (inbound or generated) ever reaches logging or response headers. 100% test coverage of CRLF, null byte, oversized, and invalid UTF-8 cases.

## Adapter Design: WSGI

The **WSGI adapter** (`mixin_logging/adapters/wsgi/`) splits into two modules per the object/client pattern:

- **`wsgi_objects.py`**. Type aliases (`Environ`, `Headers`, `ExcInfo`, `StartResponse`, `App`) and `WsgiCorrelation` value object.
  - `WsgiCorrelation.from_environ()`. Reads untrusted `X-Correlation-ID` header from WSGI environ; validates via `_is_safe()` (rejects CRLF, control chars, oversized IDs >128 bytes); on failure, generates fresh UUID4 hex[:12].
  - `WsgiCorrelation.response_header`. Property returning the safe correlation ID as `(str, str)` tuple for WSGI response headers (PEP 3333 requires header values as strings, not bytes).

- **`wsgi_client.py`**. Executable middleware (`CorrelationIdMiddleware`) and context-setter (`WsgiApp`).
  - `WsgiApp`. Sets resolved correlation ID into ContextVar, then delegates to wrapped app.
  - `CorrelationIdMiddleware`. Wraps WSGI `start_response` to inject correlation header on response start; calls `WsgiApp` to set context; clears context in `finally` via `yield from` (WSGI uses lazy iterables, not async/await).

**Security:** Validation-and-regenerate pattern ensures no unsafe correlation ID (inbound or generated) ever reaches logging or response headers. 100% test coverage of CRLF, null byte, oversized, and invalid UTF-8 cases.

**Lifecycle semantics:** WSGI is synchronous and uses lazy iterable bodies returned from the app. Cleanup happens via `try/finally` wrapping the `yield from` call (parallel to ASGI's async-context cleanup but implemented synchronously). Context is cleared on app completion or exception.

## Adapter Design: HTTPX

The **HTTPX outbound HTTP adapter** (`mixin_logging/adapters/httpx/`) enables correlation-ID propagation on outbound HTTP requests via `httpx.Client` (sync) and `httpx.AsyncClient` (async), pairing with inbound ASGI/WSGI adapters to maintain correlation context across service boundaries.

**Naming convention**: DTO is entity-prefixed (`HttpxCorrelation`, parallel to `AsgiCorrelation` + `WsgiCorrelation`); client class is general-action-named (`CorrelationIdInjector`, parallel to `CorrelationIdMiddleware` used by both ASGI + WSGI adapters). General client names mean cross-adapter consistency, readers don't need to memorize per-adapter class names.

**Container diagram:**

```
mixin_logging/adapters/httpx/httpx_objects.py
═══════════════════════════════════════════════════════════════════════════════

Imports:
    from __future__ import annotations
    from collections.abc import Awaitable, Callable
    from dataclasses import dataclass
    from typing import Any, Self

    import httpx as httpx_lib

    from mixin_logging.adapters.constants import httpx as const

Type aliases:
    RequestHook       = Callable[[httpx_lib.Request], None]
    AsyncRequestHook  = Callable[[httpx_lib.Request], Awaitable[None]]
    EventHooks        = dict[str, list[RequestHook | AsyncRequestHook]]

┌─ [FROZEN] HttpxCorrelation ─────────── value object: correlation_id to inject into outbound httpx request ─┐
│ correlation_id : str  ← from context-var via get_correlation_id()                                          │
│                                                                                                            │
│ [vld] __post_init__(self) -> None  ← invariant: correlation_id non-empty + safe chars                      │
│ [fct] from_context(cls) -> Self | None  ← reads ctx; returns None if unset or unsafe (skip-on-unsafe)      │
│ [prp] header_tuple(self) -> tuple[str, str]  ← (CORRELATION_ID_HEADER, correlation_id)                     │
│                                                                                                            │
│ static [vld] _is_safe(value: str) -> bool  ← same safe-chars + length-cap check as asgi/wsgi               │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────┘


mixin_logging/adapters/httpx/httpx_client.py
═══════════════════════════════════════════════════════════════════════════════

Imports:
    from __future__ import annotations
    from dataclasses import dataclass

    import httpx as httpx_lib

    from mixin_logging.adapters.httpx import httpx_objects as objs

┌─ [FROZEN] CorrelationIdInjector ───── stateless event-hook surface for httpx Client/AsyncClient propagation ─┐
│                                                                                                              │
│ [fct] event_hooks(cls) -> objs.EventHooks  ← returns {"request": [cls.inject_sync, cls.inject_async]}        │
│ [mth] inject_sync(cls, request: httpx_lib.Request) -> None  ← sync hook entry point                          │
│ [mth] inject_async(cls, request: httpx_lib.Request) -> None  ← async hook entry point (awaitable)            │
│                                                                                                              │
│   Implementation: corr = objs.HttpxCorrelation.from_context()                                                │
│                  if corr is not None:                                                                        │
│                      name, value = corr.header_tuple                                                         │
│                      request.headers[name] = value                                                           │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────────┘


mixin_logging/adapters/constants/httpx.py
═══════════════════════════════════════════════════════════════════════════════

"""Constants for httpx outbound adapter, header name + safety rules."""


"""Outbound header name (matches inbound ASGI/WSGI for round-trip consistency)."""

CORRELATION_ID_HEADER     : Final = "X-Correlation-ID"
CORRELATION_ID_MAX_LENGTH : Final = 128


"""Defense-in-depth header sanity check."""

UNSAFE_HEADER_CHARS       : Final = frozenset({"\r", "\n", "\0"})
```

**Implementation pattern:**

```python
"""HttpxCorrelation + CorrelationIdInjector, outbound HTTPX correlation-ID propagation."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Self

import httpx as httpx_lib

from mixin_logging.adapters.constants import httpx as const


RequestHook = Callable[[httpx_lib.Request], None]
AsyncRequestHook = Callable[[httpx_lib.Request], Awaitable[None]]
EventHooks = dict[str, list[RequestHook | AsyncRequestHook]]


@dataclass(frozen=True, slots=True)
class HttpxCorrelation:
    """Value object capturing the correlation_id to inject into outbound httpx requests."""

    correlation_id: str

    def __post_init__(self) -> None:
        ...

    @classmethod
    def from_context(cls) -> Self | None:
        ...

    @property
    def header_tuple(self) -> tuple[str, str]:
        ...

    @staticmethod
    def _is_safe(value: str) -> bool:
        ...


@dataclass(frozen=True, slots=True)
class CorrelationIdInjector:
    """Stateless event-hook surface for httpx Client/AsyncClient correlation-ID propagation."""

    @classmethod
    def event_hooks(cls) -> EventHooks:
        ...

    @classmethod
    def inject_sync(cls, request: httpx_lib.Request) -> None:
        ...

    @classmethod
    async def inject_async(cls, request: httpx_lib.Request) -> None:
        ...
```

**Adapter design dimensions:**

1. **Scope / protocol coverage**: every outbound httpx request (sync + async); both `httpx.Client` and `httpx.AsyncClient`; covers all HTTP methods.
2. **Trace propagation interop**: `X-Correlation-ID` header only (matches inbound ASGI/WSGI). No W3C tracecontext / B3 in this iteration.
3. **Self-logging surface**: none (silent injection; cross-package aspect-isolation).
4. **Composition guidance**: correlation injection fires BEFORE auth/signing hooks so signed requests include the header in the signed payload.
5. **Compatibility surface**: httpx 0.27+ (event_hooks API stable since 0.20).

**Design decisions:**

- **Empty-context behavior**: `from_context` returns `None` when context-var is unset; `CorrelationIdInjector.inject_sync` short-circuits (no header set, no exception). Pure passthrough.
- **Unsafe-value defense-in-depth**: `from_context` returns `None` when the context-var value fails `_is_safe` check (skip-on-unsafe). Inbound adapter is the sole regenerator; outbound never regenerates.
- **File/dir naming**: `apps/adapters/httpx/` (parallel ASGI/WSGI naming) + alias library as `import httpx as httpx_lib` inside source files to avoid module-name shadow with `httpx.py`.

**Future extensibility (beyond 0.3.0):**

- `response` event hook to verify downstream echo-back of correlation_id (defense-in-depth tracing audit)
- W3C tracecontext / B3 header support for cross-vendor distributed tracing

**Cross-references:** see `## Adapter Design: ASGI` + `## Adapter Design: WSGI` above for inbound counterparts.

## Error-Handling Convention (2026-05-28)

All foundational adapters in logging-mixin (ASGI, WSGI, httpx) extract their raise-site error messages to source-side constants in `constants/<feature>.py` under an `ERR_<DOMAIN>_<CONDITION>` naming scheme. Examples:

- `constants/asgi.py` → `ERR_CORRELATION_ID_EMPTY: Final = "correlation_id must not be empty"`
- `constants/wsgi.py` → `ERR_CORRELATION_ID_EMPTY: Final = "correlation_id must not be empty"`
- `constants/httpx.py` → `ERR_CORRELATION_ID_UNSAFE: Final = "correlation_id must be non-empty, within length cap, free of unsafe chars"`

Raise sites reference the constant: `raise ValueError(const.ERR_CORRELATION_ID_EMPTY)`.

Tests reference the same source-side constant via `pytest.raises(ValueError, match=const.ERR_*)`, single source of truth; no duplicate `RAISE_MATCH_*` test-side constants.

Rationale: when `domain-errors` (planned cross-project PyPI) integrates, typed exception classes will reference these message constants directly:

```python
class CorrelationValidationError(Exception):
    code = "CORR_VALIDATION_FAILED"
    default_message = const.ERR_CORRELATION_ID_UNSAFE
```

Extracting at adapter creation time prevents fleet-wide retrofit when domain-errors lands.

## Version History

- **0.3.0**: Public API surface standardization and conformance enforcement. All 8 adapters fully implemented and tested.
- **0.2.0**: All 8 adapters implemented (ASGI, WSGI, HTTPX, Requests, Botocore, Celery, Cloud, Stdlib). Core components (`LoggingMixin`, `@logged`, `CorrelationContext`) stable.
