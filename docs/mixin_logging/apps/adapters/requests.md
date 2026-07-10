# logging-mixin. Requests Adapter

> **Location:** `logging-mixin/docs/apps/adapters/requests.md`
> **Status:** Implemented. Outbound correlation-ID propagation via the requests library `HTTPAdapter.add_headers` hook.
> **Code location:** `mixin_logging/adapters/requests/` (`requests_objects.py` + `requests_client.py`); constants in `mixin_logging/adapters/constants/requests.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Adapter Categories & Data Flow).
> **Sibling docs:** `docs/apps/adapters/botocore.md`, `docs/apps/adapters/httpx.md`, `docs/apps/context/correlation.md`.

## Purpose

Propagate the current correlation ID onto outbound requests made via the `requests` library (synchronous HTTP client) so a single inbound request can be traced through every downstream call and into logging and external services.

## Category

Outbound Propagation, the same category as the botocore and httpx adapters, specialized for the `requests` library rather than an async client or AWS SDK.

## Behavior

- `CorrelationHTTPAdapter.register_on_session(session)` mounts the adapter on a `requests.Session` for both `http://` and `https://` schemes.
- `CorrelationHTTPAdapter.correlation_session()` (classmethod) returns a pre-configured `Session` with the adapter already mounted.
- On each outbound request, the `add_headers` method (the per-send injection point in requests' `HTTPAdapter`) reads the current correlation ID from the `ContextVar` via `RequestsCorrelation.from_context()`. If it is unset or unsafe the hook is a no-op; otherwise it sets `X-Correlation-ID` on the request headers. The hook fires on every send including retries and redirects.

## Value Object

`RequestsCorrelation` (frozen, slots) captures the `correlation_id` bound for the outbound header:

- `from_context()`. Read the ContextVar; returns `None` if unset or unsafe (no raise).
- `header_tuple`. Returns `(CORRELATION_ID_HEADER, correlation_id)`.
- `__post_init__` + `_is_safe`. Reject empty values, values over 128 chars, and values containing CR / LF / null.

## Constants

`mixin_logging/adapters/constants/requests.py`:

- `CORRELATION_ID_HEADER = "X-Correlation-ID"` (matches inbound ASGI/WSGI for round-trip consistency)
- `CORRELATION_ID_MAX_LENGTH = 128`
- `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})`
- `ERR_CORRELATION_ID_UNSAFE`

## Design Note

The requests library exposes `HTTPAdapter.add_headers(request, **kwargs)` as the standard per-request header-injection point. This is called by the adapter on every send before the request leaves the session, including retries and redirects. The correlation ID is injected at this low level to ensure it reaches every HTTP call made through the session, regardless of the calling pattern.

## Compatibility

Synchronous `requests` library (popular, widely-used HTTP client for Python). Requires the `[requests]` extra to be installed.

## Example Usage

```python
from mixin_logging.adapters.requests import CorrelationHTTPAdapter

session = CorrelationHTTPAdapter.correlation_session()
response = session.get("https://api.example.com/resource")
```

Or register on an existing session:

```python
import requests
from mixin_logging.adapters.requests import CorrelationHTTPAdapter

session = requests.Session()
CorrelationHTTPAdapter.register_on_session(session)
response = session.post("https://api.example.com/data", json={"key": "value"})
```

Every request now carries `X-Correlation-ID` into the downstream service.

## See Also

- **Adapters overview / Botocore:** `docs/apps/adapters/botocore.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
- **Correlation Context:** `docs/apps/context/correlation.md`
