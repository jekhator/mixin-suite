# logging-mixin. ASGI Adapter

> **Location:** `logging-mixin/docs/apps/adapters/asgi.md`
> **Status:** Living reference. All 13 adapters fully implemented in 0.3.0+. Version sourcing: canonical version in `mixin_logging/config/_version.py` (read by both `__init__.py` and the build system).
> **Code location:** `mixin_logging/adapters/` (13 adapters: ASGI, WSGI, Cloud, Stdlib, HTTPX, Requests, Botocore, Celery, aiohttp, urllib3, gRPC, WebSocket, GraphQL)
> **Diagrams:** `docs/apps/adapters/diagrams.md`
> **Sibling docs:** `docs/architecture/architecture.md`, `docs/apps/decorators/logged.md`, `docs/apps/context/correlation.md`.

## Purpose

Framework integrations for correlation ID propagation and context setup. Adapters are **protocol-level, not per-framework**, a small set of middleware and handlers covers FastAPI, Django, Starlette, Quart, Flask, Pyramid, AWS Lambda, and other platforms.

## Architecture Overview

### Five Categories

1. **Inbound/Ingress**. Extract or generate correlation ID from incoming request headers; set `CorrelationContext` for downstream handlers.
   - `asgi.py`. Generic ASGI middleware (FastAPI, Starlette, Quart)
   - `wsgi.py`. Generic WSGI middleware (Django, Flask, Pyramid)
   - `cloud.py`. Serverless handler (AWS Lambda, etc.)

2. **Inbound Edge**. Extract or generate correlation ID for WebSocket, gRPC, and GraphQL protocols.
   - `websocket.py`. WebSocket ASGI middleware (Starlette, Channels)
   - `grpc.py`. gRPC server interceptor (`[grpc]` extra)
   - `graphql.py`. GraphQL resolver-context injector (Strawberry, Ariadne)

3. **Outbound Propagation**. Inject correlation ID into outbound HTTP calls so downstream services can trace the chain.
   - `httpx.py`. HTTPX client propagation (`[httpx]` extra)
   - `requests.py`. Requests library propagation (`[requests]` extra)
   - `aiohttp.py`. aiohttp client propagation via TraceConfig (`[aiohttp]` extra)
   - `urllib3.py`. urllib3 PoolManager propagation (`[urllib3]` extra)
   - `botocore.py`. AWS SDK propagation (`[botocore]` extra)

4. **Async/Cross-Boundary**. Carry correlation ID across enqueue→execute boundaries (job queues, background tasks).
   - `celery.py`. Celery task propagation (`[celery]` extra)

5. **Output Sink**. Inject correlation ID into all Python logs, even from third-party libraries.
   - `stdlib.py`. Standard library `logging.Filter` (always included, no extra)

### Shared Internals

All adapters use the following structure:

- **Type aliases & value objects:** `mixin_logging/adapters/asgi/asgi_objects.py` (ASGI-specific) or equivalent per protocol
- **Middleware/client:** `mixin_logging/adapters/asgi/asgi_client.py` (ASGI-specific) or equivalent per protocol
- **Constants:** `mixin_logging/adapters/constants/asgi.py` (per-protocol, e.g., `CORRELATION_ID_HEADER`, `HTTP_SCOPE_TYPE`, `RESPONSE_START_MESSAGE_TYPE`)
- **Pattern:** Extract-or-generate via `<Protocol>Correlation.from_scope()` or equivalent; generate UUID4 hex[:12] on miss; set context via `set_correlation_id()`; clear via `clear_correlation_id()`.

### Lifecycle Pattern

Each adapter follows this pattern:

1. **Entry:** Clear context → read header or platform ID → set `CorrelationContext` via `_client.set_id()`.
2. **Execution:** Downstream code inherits correlation ID from `ContextVar`.
3. **Exit:** Clear context via `_client.clear()` (if scoped).
4. **Egress (optional):** Attach correlation ID to response headers or outbound requests.

## Adapter Specifications

### 1. ASGI Middleware, `asgi/`

**Scope:** FastAPI, Starlette, Quart (any ASGI framework)

**Package structure:**
- `asgi_objects.py`, `AsgiCorrelation` value object, type aliases (`Scope`, `Message`, `Receive`, `Send`, `App`)
- `asgi_client.py`, `ASGIApp` setter, `CorrelationIdMiddleware` (the public middleware)
- `__init__.py`, docstring-only (imports pulled from `asgi_client`)

**No extra imports**, operates on raw ASGI `(scope, receive, send)` protocol.

**Behavior:**

- `AsgiCorrelation.from_scope(scope)` extracts `x-correlation-id` header (binary → UTF-8 decode); on any validation failure, generates UUID4 hex[:12].
  - **Validation:** Untrusted inbound headers are validated via `_is_safe()` to reject control characters (`\r\n\0`), oversized values (>128 bytes), and invalid UTF-8. Invalid headers are rejected and a fresh UUID is auto-generated.
  - **Regenerate on failure:** If the inbound header fails validation (CRLF detected, over-length, bad UTF-8), a safe UUID4 hex[:12] is always generated and echoed in the response instead.
- `ASGIApp` performs the **set** via `set_correlation_id()`, then delegates to wrapped app.
- `CorrelationIdMiddleware` resolves correlation → wraps `send` to inject header on `http.response.start` → executes via `ASGIApp` → clears in `finally`.
- All logs inherit correlation ID via `ContextVar`. The correlation ID is guaranteed to be safe (either validated inbound or freshly generated).

**Example usage:**

```python
from fastapi import FastAPI
from mixin_logging.adapters.asgi.asgi_client import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)
```

### 2. WSGI Middleware, `wsgi.py`

**Scope:** Django, Flask, Pyramid (any WSGI framework)

**No extra imports**, operates on raw WSGI `(environ, start_response)` protocol.

**Behavior:**

- Extract `HTTP_X_CORRELATION_ID` from WSGI environ (WSGI uppercases headers with `HTTP_` prefix).
- If missing, generate UUID4 hex[:12].
- Set `CorrelationContext` at request entry.
- Clear at request exit.
- Inject correlation ID into response headers (via `start_response`).

**Example usage (Django):**

```python
MIDDLEWARE = [
    # ... other middleware
    "mixin_logging.adapters.wsgi.CorrelationIdMiddleware",
]
```

**Example usage (Flask):**

```python
from flask import Flask
from mixin_logging.adapters.wsgi import CorrelationIdMiddleware

app = Flask(__name__)
app.wsgi_app = CorrelationIdMiddleware(app.wsgi_app)
```

### 3. Cloud/Serverless Handler, `cloud.py`

**Scope:** AWS Lambda, Google Cloud Functions, Azure Functions (any serverless platform)

**No extra imports**, reads platform-specific request context (AWS `event`, GCP request metadata, etc.).

**Behavior:**

- For AWS Lambda: read `X-Correlation-ID` from `event.get("headers", {})` or from `context.request_id` (AWS-provided request ID).
- If missing, generate UUID4 hex[:12].
- Set `CorrelationContext` at handler entry.
- Clear at handler exit (optional; Lambda process dies after invocation).
- Inject correlation ID into response headers (if HTTP response).

**Example usage (AWS Lambda):**

```python
from mixin_logging.adapters.cloud import CloudSetup

def lambda_handler(event, context):
    CloudSetup.setup_correlation_id(event, context)  # Reads X-Correlation-ID or generates
    svc = MyService()
    return svc.process(event)
```

### 4. Standard Library Filter, `stdlib.py`

**Scope:** All Python logging calls (third-party libraries, stdlib, application code)

**Always included**, no extra required.

**Behavior:**

- Registers a `logging.Filter` that injects `correlation_id` into every `LogRecord`.
- Pulls the correlation ID from `ContextVar` (set by inbound adapters).
- Defaulting to `"-"` if unset (so all logs have a correlation_id field).

**Example usage:**

```python
import logging
from mixin_logging.adapters.stdlib import CorrelationLogFilter

logger = logging.getLogger("myapp")
CorrelationLogFilter.add_correlation_filter(logger)

# All emitted LogRecords now include correlation_id field
logger.info("User logged in", extra={"user_id": 123})
# LogRecord contains: correlation_id="<current>", user_id=123
```

### 5. HTTPX Outbound Propagation, `httpx.py`

**Scope:** HTTPX client library calls

**Extra required:** `[httpx]`

**Behavior:**

- Wraps HTTPX `Client` or `AsyncClient` to inject `X-Correlation-ID` header on every outbound request.
- Reads current correlation ID from `ContextVar`; skips injection if unset.

**Example usage:**

```python
import httpx
from mixin_logging.adapters.httpx import CorrelationIdInjector

async def call_downstream():
    async with httpx.AsyncClient(event_hooks=CorrelationIdInjector.event_hooks()) as client:
        response = await client.get("https://api.example.com/data")
        # X-Correlation-ID automatically injected
```

### 6. Requests Outbound Propagation, `requests.py`

**Scope:** Requests library calls

**Extra required:** `[requests]`

**Behavior:**

- Wraps Requests `Session` to inject `X-Correlation-ID` header on every outbound request.
- Reads current correlation ID from `ContextVar`; skips injection if unset.

**Example usage:**

```python
import requests
from mixin_logging.adapters.requests import CorrelationHTTPAdapter

def call_downstream():
    session = requests.Session()
    CorrelationHTTPAdapter.register_on_session(session)
    response = session.get("https://api.example.com/data")
    # X-Correlation-ID automatically injected
```

### 7. Celery Task Propagation, `celery.py`

**Scope:** Celery tasks and job queue handlers

**Extra required:** `[celery]`

**Behavior:**

- Celery signal handlers (`before_task_publish` / `task_prerun`) carry correlation ID from producer to consumer.
- Producer: injects correlation ID into task metadata if set.
- Consumer: extracts correlation ID from task metadata and sets `CorrelationContext` before task execution.
- Clears context after task execution.

**Example usage:**

```python
from celery import Celery
from mixin_logging.adapters.celery import CorrelationSignals

app = Celery()
CorrelationSignals.connect()

@app.task
def process_order(order_id: str):
    from mixin_logging import get_correlation_id
    cid = get_correlation_id()  # Inherited from producer
    # ... process order, logs include correlation_id
```

## Architecture Design

The ASGI adapter (and all others) lives **in logging-mixin's `adapters/asgi/`**, providing a clean, reusable surface that works with any ASGI framework. This design ensures:

- **No framework lock-in:** Adapters are protocol-level, not framework-specific.
- **Single responsibility:** Correlation ID is a logging-mixin concern; framework adapters are logging-mixin's domain.
- **Reusability:** The same `CorrelationIdMiddleware` works with FastAPI, Starlette, Quart, and any ASGI app.

## Constants

Constants are protocol-specific, living in `mixin_logging/adapters/constants/<protocol>.py`. Each adapter has its own constant module with protocol-specific header encodings, message type names, and validation thresholds. For example:

### `mixin_logging/adapters/constants/asgi.py`

```python
from typing import Final

CORRELATION_ID_HEADER: Final = b"x-correlation-id"  # Binary for ASGI headers
HTTP_SCOPE_TYPE: Final = "http"
RESPONSE_START_MESSAGE_TYPE: Final = "http.response.start"
CORRELATION_ID_MAX_LENGTH: Final = 128
UNSAFE_HEADER_CHARS: Final = {"\r", "\n", "\0"}
```

All adapters use similar constants with protocol-specific variations (e.g., WSGI uses string header names; ASGI uses bytes).

## Implementation Status

| Adapter | Status | Version |
|---------|--------|---------|
| `asgi/` | **Implemented**, `asgi_objects.py` + `asgi_client.py` | 0.1.0+ |
| `wsgi/` | **Implemented**, `wsgi_objects.py` + `wsgi_client.py` | 0.3.0+ |
| `cloud/` | **Implemented**, `cloud_objects.py` + `cloud_client.py` | 0.3.0+ |
| `stdlib/` | **Implemented**, `stdlib_client.py` (no objects file needed) | 0.3.0+ |
| `httpx/` | **Implemented**, `httpx_objects.py` + `httpx_client.py` | 0.3.0+ (extra: `[httpx]`) |
| `requests/` | **Implemented**, `requests_objects.py` + `requests_client.py` | 0.3.0+ (extra: `[requests]`) |
| `celery/` | **Implemented**, `celery_objects.py` + `celery_client.py` | 0.3.0+ (extra: `[celery]`) |
| `botocore/` | **Implemented**, `botocore_objects.py` + `botocore_client.py` | 0.3.0+ (extra: `[botocore]`) |
| `aiohttp/` | **Implemented**, `aiohttp_objects.py` + `aiohttp_client.py` | 0.3.0+ (extra: `[aiohttp]`) |
| `urllib3/` | **Implemented**, `urllib3_objects.py` + `urllib3_client.py` | 0.3.0+ (extra: `[urllib3]`) |
| `grpc/` | **Implemented**, `grpc_objects.py` + `grpc_client.py` | 0.3.0+ (extra: `[grpc]`) |
| `websocket/` | **Implemented**, `websocket_objects.py` + `websocket_client.py` | 0.3.0+ |
| `graphql/` | **Implemented**, `graphql_objects.py` + `graphql_client.py` | 0.3.0+ |

All 13 adapters are fully implemented and available in 0.3.0+.

## Design Notes

### UUID4 Hex Shortening

Generated correlation IDs use UUID4 hex format, shortened to first 12 characters (`hex[:12]`) for readability in logs and HTTP headers:

```python
import uuid

correlation_id = uuid.uuid4().hex[:12]  # e.g., "a1b2c3d4e5f6"
```

Full 32-character UUIDs are supported if passed via header; the shortening applies only to generation (missing-header case).

### Context Lifecycle Responsibility

- **Middleware (ASGI/WSGI/Cloud):** Owns context setup/teardown at request boundaries.
- **Task handlers (Celery):** Own context setup/teardown at task boundaries.
- **Application code:** Never calls `set_id()` / `clear()` directly; relies on adapters.

This ensures clean separation and prevents accidental context pollution.

### Error Handling

All adapters handle missing/malformed headers gracefully:

- Missing header → generate UUID4 hex[:12].
- Malformed header → log warning (via `LoggingMixin` if applicable) and generate fallback.
- No breaking exceptions on header extraction.

## See Also

- **Correlation Context Reference:** `docs/apps/context/correlation.md`
- **Decorators Reference:** `docs/apps/decorators/logged.md`
- **Architecture:** `docs/architecture/architecture.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
