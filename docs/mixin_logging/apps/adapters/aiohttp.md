# logging-mixin. Aiohttp Adapter

> **Location:** `logging-mixin/docs/apps/adapters/aiohttp.md`
> **Status:** Implemented. Outbound correlation-ID propagation via the aiohttp library `TraceConfig.on_request_start` hook.
> **Code location:** `mixin_logging/adapters/aiohttp/` (`aiohttp_objects.py` + `aiohttp_client.py`); constants in `mixin_logging/adapters/constants/aiohttp.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Adapter Categories & Data Flow).
> **Sibling docs:** `docs/apps/adapters/requests.md`, `docs/apps/adapters/httpx.md`, `docs/apps/context/correlation.md`.

## Purpose

Propagate the current correlation ID onto outbound requests made via the `aiohttp` library (async HTTP client) so a single inbound request can be traced through every downstream call and into logging and external services.

## Category

Outbound Propagation, the same category as the requests and httpx adapters, specialized for the `aiohttp` library rather than a synchronous client or pre-async offering.

## Behavior

- `CorrelationIdInjector.trace_config()` (classmethod) returns a pre-configured `aiohttp.TraceConfig` with the correlation-ID injection hook attached.
- Pass the returned config to `aiohttp.ClientSession(trace_configs=[...])` to activate.
- On each outbound request, the `_inject` async method (the `on_request_start` hook in aiohttp's trace system) reads the current correlation ID from the `ContextVar` via `AiohttpCorrelation.from_context()`. If it is unset or unsafe the hook is a no-op; otherwise it sets `X-Correlation-ID` on the request headers. The hook fires on every send.

## Value Object

`AiohttpCorrelation` (frozen, slots) captures the `correlation_id` bound for the outbound header:

- `from_context()`. Read the ContextVar; returns `None` if unset or unsafe (no raise).
- `header_tuple`. Returns `(CORRELATION_ID_HEADER, correlation_id)`.
- `__post_init__` + `_is_safe`. Reject empty values, values over 128 chars, and values containing CR / LF / null.

## Constants

`mixin_logging/adapters/constants/aiohttp.py`:

- `CORRELATION_ID_HEADER = "X-Correlation-ID"` (matches inbound ASGI/WSGI for round-trip consistency)
- `CORRELATION_ID_MAX_LENGTH = 128`
- `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})`
- `ERR_CORRELATION_ID_UNSAFE`

## Design Note

The aiohttp library exposes `TraceConfig.on_request_start` as the standard hook fired before every outbound request (but after request creation and URL setup). The `_inject` async method hooks into this callback to inject the correlation ID at the lowest level, ensuring it reaches every HTTP call made through the session, regardless of the calling pattern (get, post, etc.).

## Compatibility

Async `aiohttp` library (widely-used async HTTP client for Python). Requires the `[aiohttp]` extra to be installed.

## Example Usage

```python
import aiohttp
from mixin_logging import set_correlation_id
from mixin_logging.adapters.aiohttp import CorrelationIdInjector

set_correlation_id("request-123")

async def fetch_data():
    trace_config = CorrelationIdInjector.trace_config()
    async with aiohttp.ClientSession(trace_configs=[trace_config]) as session:
        async with session.get("https://api.example.com/resource") as resp:
            return await resp.json()
```

Every request now carries `X-Correlation-ID: request-123` into the downstream service.

## See Also

- **Adapters overview / Requests:** `docs/apps/adapters/requests.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
- **Correlation Context:** `docs/apps/context/correlation.md`
