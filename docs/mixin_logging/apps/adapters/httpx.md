# HTTPX Adapter

Instrument `httpx.Client` and `httpx.AsyncClient` to automatically inject `X-Correlation-ID` headers on every outbound request.

## Overview

The HTTPX adapter uses event hooks to inject the correlation ID from the current context into every HTTP request. Works with both synchronous and asynchronous clients.

## Installation

Install the `httpx` optional dependency:

```bash
uv add "logging-mixin[httpx]"
```

Or with pip:

```bash
pip install "logging-mixin[httpx]"
```

## Usage

### Sync Client

```python
import httpx
from mixin_logging.adapters.httpx import CorrelationIdInjector

client = httpx.Client(event_hooks=CorrelationIdInjector.event_hooks())

# When a correlation ID is set in the context:
response = client.get("https://api.example.com/users")
# Request includes header: X-Correlation-ID: <correlation-id>
```

### Async Client

```python
import httpx
from mixin_logging.adapters.httpx import CorrelationIdInjector

async_client = httpx.AsyncClient(event_hooks=CorrelationIdInjector.event_hooks())

# In an async context with correlation ID set:
response = await async_client.get("https://api.example.com/users")
# Request includes header: X-Correlation-ID: <correlation-id>
```

### With Existing Event Hooks

If you already have custom event hooks, merge them:

```python
from mixin_logging.adapters.httpx import CorrelationIdInjector

my_hooks = {
    "request": [my_custom_hook],
    "response": [my_logging_hook],
}

correlation_hooks = CorrelationIdInjector.event_hooks()

# Merge request hooks
merged_hooks = {
    "request": my_hooks.get("request", []) + correlation_hooks["request"],
    "response": my_hooks.get("response", []) + correlation_hooks.get("response", []),
}

client = httpx.Client(event_hooks=merged_hooks)
```

## API

### CorrelationIdInjector

**`event_hooks() → EventHooks`**

Returns a dict of event hooks ready for `httpx.Client(..., event_hooks=...)`:

```python
{
    "request": [inject_sync, inject_async]
}
```

The hooks read the current correlation ID from context and inject it as the `X-Correlation-ID` header.

**`inject_sync(request: httpx.Request) → None`**

Synchronously injects the correlation ID header into a request. Called automatically by the event hook system.

**`inject_async(request: httpx.Request) → Awaitable[None]`**

Async wrapper of `inject_sync`. Called for async clients.

## How It Works

1. Every outbound `httpx.get()`, `httpx.post()`, etc. triggers the request event hook
2. The hook calls `CorrelationIdInjector.inject_sync()` (or `inject_async()` for async clients)
3. The injector reads the current correlation ID from the `ContextVar`
4. If a correlation ID exists and is valid, it injects `X-Correlation-ID: <id>` into the request headers
5. If no correlation ID is set in the context, the header is not injected (no-op)

## Validation

The adapter validates correlation IDs before injection:

- **Non-empty** :  Must not be empty string
- **Max length** :  Must not exceed 128 bytes
- **Safe characters** :  Must not contain CRLF (`\r\n`), null (`\0`), or other control characters

If a correlation ID fails validation, it is silently skipped and no header is injected. This prevents invalid data from reaching downstream services.

## Correlation ID Propagation

Use with the ASGI, WSGI, or other inbound adapters to create end-to-end propagation:

```python
# Request handler (e.g., FastAPI)
from mixin_logging.adapters.asgi import CorrelationIdMiddleware
from mixin_logging.adapters.httpx import CorrelationIdInjector

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)

# Client (instrumented httpx)
client = httpx.Client(event_hooks=CorrelationIdInjector.event_hooks())

@app.get("/orders/{order_id}")
async def get_order(order_id: int):
    # Middleware sets correlation ID from request headers
    # Now outbound calls include it automatically
    response = await client.get(f"https://api.internal.example.com/orders/{order_id}")
    return response.json()
```

The correlation ID flows:
1. Client request → FastAPI (ASGI middleware sets context)
2. Handler → httpx client (injects into outbound request)
3. Downstream service receives the same correlation ID

## See Also

- [Correlation context](../context/correlation.md)
- [LoggingMixin](../mixin/mixin.md)
- [ASGI adapter](asgi.md)
