# logging-mixin. WebSocket Adapter

> **Location:** `logging-mixin/docs/apps/adapters/websocket.md`
> **Status:** Implemented. Inbound correlation-ID extraction via WebSocket handshake headers.
> **Code location:** `mixin_logging/adapters/websocket/` (`websocket_objects.py` + `websocket_client.py`); constants in `mixin_logging/adapters/constants/websocket.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Adapter Categories & Data Flow).
> **Sibling docs:** `docs/apps/adapters/asgi.md`, `docs/apps/adapters/wsgi.md`, `docs/apps/context/correlation.md`.

## Purpose

Extract or generate a correlation ID from WebSocket handshake headers (`X-Correlation-ID`) and set the correlation context for all downstream handlers, enabling end-to-end tracing across WebSocket connections.

## Category

Inbound/Ingress, alongside the ASGI and WSGI adapters, specialized for WebSocket protocols where correlation ID is transmitted in the HTTP upgrade handshake.

## Behavior

- `CorrelationIdMiddleware` is an ASGI middleware that inspects the scope type.
- For WebSocket scopes: Extract correlation ID from headers via `WebSocketCorrelation.from_headers()`. If a valid `X-Correlation-ID` header is present, use it (extracted=True); otherwise generate a fresh UUID4 hex[:12] (extracted=False).
- Set the correlation context via `set_correlation_id()`.
- Execute the wrapped ASGI app, then clear context via `clear_correlation_id()` in a finally block (guaranteed cleanup even on exception).
- For non-WebSocket (HTTP/etc) scopes: pass through untouched to the wrapped app (no correlation setup).

## Value Object

`WebSocketCorrelation` (frozen, slots) captures the resolved correlation ID from the handshake:

- `correlation_id: str`. The resolved correlation ID (safe, non-empty, 1-128 chars, no CRLF/null).
- `extracted: bool`. True if the ID was extracted from the inbound header; False if generated.
- `from_headers(headers: Headers)` (classmethod). Scan the handshake headers for `x-correlation-id` (case-insensitive); extract and return if valid, otherwise generate UUID4 hex[:12].
- `_is_safe(value: str)` (staticmethod). Reject empty strings, values over 128 chars, and values containing CR / LF / null; return bool.
- `__post_init__` + validation. Raise ValueError on direct construction with unsafe correlation_id.

## Constants

`mixin_logging/adapters/constants/websocket.py`:

- `CORRELATION_ID_HEADER = "x-correlation-id"` (HTTP handshake header name; case-insensitive match in from_headers).
- `CORRELATION_ID_MAX_LENGTH = 128`
- `GENERATED_ID_LENGTH = 12` (UUID4 hex[:12] length).
- `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})` (rejected characters in correlation ID values).
- `ERR_CORRELATION_ID_UNSAFE` (error message raised on invariant breach).

## Design Note

The WebSocket adapter operates at the ASGI middleware level, reading from the raw `scope["headers"]` list of byte-pairs (the HTTP upgrade request headers). The handshake headers are immutable at this point, making header extraction safe. Unlike HTTP request/response patterns where headers can be modified, WebSocket headers are fixed at upgrade time, so the adapter only extracts: it does not echo the header back in a response (the WebSocket protocol has no response headers in the handshake accept frame). The correlation ID is purely for context propagation downstream.

## Compatibility

Works with any ASGI framework that accepts WebSocket connections: FastAPI, Starlette, Quart, or raw ASGI apps. Requires no extra dependencies.

## Example Usage

```python
from fastapi import FastAPI, WebSocket
from mixin_logging.adapters.websocket import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    from mixin_logging import get_correlation_id
    cid = get_correlation_id()  # Extracted from headers or auto-generated
    # All logs from this handler inherit the correlation ID
    await websocket.send_text(f"Connected: {cid}")
```

When a client connects with `X-Correlation-ID: my-trace-id`, the middleware extracts it. If the client omits the header, the middleware generates a fresh UUID4 hex[:12].

## See Also

- **ASGI Adapter Overview:** `docs/apps/adapters/asgi.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
- **Correlation Context:** `docs/apps/context/correlation.md`
