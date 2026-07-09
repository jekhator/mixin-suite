# logging-mixin. Urllib3 Adapter

> **Location:** `logging-mixin/docs/apps/adapters/urllib3.md`
> **Status:** Implemented. Outbound correlation-ID propagation via the urllib3 library `PoolManager.urlopen()` hook.
> **Code location:** `mixin_logging/adapters/urllib3/` (`urllib3_objects.py` + `urllib3_client.py`); constants in `mixin_logging/adapters/constants/urllib3.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Adapter Categories & Data Flow).
> **Sibling docs:** `docs/apps/adapters/requests.md`, `docs/apps/adapters/httpx.md`, `docs/apps/adapters/botocore.md`, `docs/apps/context/correlation.md`.

## Purpose

Propagate the current correlation ID onto outbound requests made via the `urllib3` library (synchronous HTTP client) so a single inbound request can be traced through every downstream call and into logging and external services.

## Category

Outbound Propagation, the same category as the requests and httpx adapters, specialized for the `urllib3` library rather than the requests Session API or async client.

## Behavior

- `CorrelationIdPoolManager` extends `urllib3.PoolManager` and overrides `urlopen()`.
- On each outbound request, the `urlopen()` method reads the current correlation ID from the `ContextVar` via `Urllib3Correlation.from_context()`. If it is unset or unsafe, the injection is skipped; otherwise it sets `X-Correlation-ID` on the request headers.
- The injection happens before the request is sent to the parent `PoolManager.urlopen()` method, ensuring the header is attached to every HTTP call.

## Value Object

`Urllib3Correlation` (frozen, slots) captures the `correlation_id` bound for the outbound header:

- `from_context()`. Read the ContextVar; returns `None` if unset or unsafe (no raise).
- `header_tuple`. Returns `(CORRELATION_ID_HEADER, correlation_id)`.
- `__post_init__` + `_is_safe`. Reject empty values, values over 128 chars, and values containing CR / LF / null.

## Constants

`mixin_logging/adapters/constants/urllib3.py`:

- `CORRELATION_ID_HEADER = "X-Correlation-ID"` (matches inbound ASGI/WSGI and outbound requests/httpx for round-trip consistency)
- `CORRELATION_ID_MAX_LENGTH = 128`
- `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})`
- `ERR_CORRELATION_ID_UNSAFE`

## Design Note

The urllib3 library exposes `PoolManager.urlopen(method, url, **kwargs)` as the standard request method. By subclassing `PoolManager` and overriding `urlopen()`, we intercept every request before it is sent. The correlation ID is validated and injected into the headers dict in kwargs before delegating to the parent method, ensuring it reaches every HTTP call made through the pool manager.

## Compatibility

Synchronous `urllib3` library (widely-used HTTP client for Python, used as the transport layer by requests). Requires the `[urllib3]` extra to be installed.

## Example Usage

```python
from mixin_logging.adapters.urllib3 import CorrelationIdPoolManager

http = CorrelationIdPoolManager()
response = http.request("GET", "https://api.example.com/resource")
```

Every request now carries `X-Correlation-ID` into the downstream service.

## See Also

- **Adapters overview / Requests:** `docs/apps/adapters/requests.md`
- **Adapters overview / Httpx:** `docs/apps/adapters/httpx.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
- **Correlation Context:** `docs/apps/context/correlation.md`
