# WSGI Adapter

Instrument WSGI frameworks to automatically extract or generate correlation IDs and inject them into response headers.

## Overview

The WSGI adapter provides middleware for frameworks like Django, Flask, and Pyramid. It extracts the correlation ID from request headers (or generates a UUID if missing), stores it in the request context, and injects it into the response headers.

## Installation

The WSGI adapter is built-in and requires no additional dependencies.

## Usage

### Django

```python
from mixin_logging.adapters.wsgi import CorrelationIdMiddleware

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "mixin_logging.adapters.wsgi.CorrelationIdMiddleware",
    # ... other middleware ...
]
```

### Flask

```python
from mixin_logging.adapters.wsgi import CorrelationIdMiddleware
from flask import Flask

app = Flask(__name__)
app.wsgi_app = CorrelationIdMiddleware(app.wsgi_app)
```

### Pyramid

```python
from mixin_logging.adapters.wsgi import CorrelationIdMiddleware

def main(global_config, **settings):
    config = Configurator(settings=settings)
    # Wrap the WSGI app
    app = config.make_wsgi_app()
    return CorrelationIdMiddleware(app)
```

## How It Works

1. Request arrives at the middleware
2. Middleware extracts the `X-Correlation-ID` header (if present) or generates a UUID
3. Correlation ID is set in the context via `set_correlation_id()`
4. The request proceeds through the app
5. Response is created
6. Middleware injects the correlation ID into the response header: `X-Correlation-ID: <id>`
7. Response is returned

The correlation ID is now available in the context for:
- `LoggingMixin` classes (auto-injected into logs)
- Manual context access via `get_correlation_id()`
- Outbound clients (HTTPX, Requests, Botocore) that are instrumented

## API

### CorrelationIdMiddleware

WSGI middleware callable that extracts/generates and propagates correlation IDs.

**Usage:**

```python
wrapped_app = CorrelationIdMiddleware(app)
```

Where `app` is the WSGI application to wrap.

## Correlation ID Behavior

- **From header** :  If `X-Correlation-ID` header exists, use it (validated for safe characters)
- **Generate** :  If header is missing or invalid, generate a UUID4 and use that
- **Response injection** :  Always inject the final correlation ID into the `X-Correlation-ID` response header
- **Context propagation** :  Set in context via `set_correlation_id()` so all downstream code can access it

## Validation

The WSGI adapter validates correlation IDs:

- **Non-empty** :  UUID is generated if the extracted value is empty
- **Safe characters** :  Must not contain CRLF (`\r\n`), null (`\0`), or other control characters (UUID fallback if invalid)
- **Max length** :  Must not exceed 128 bytes (UUID fallback if invalid)

Invalid headers trigger automatic fallback to a generated UUID, ensuring reliable operation.

## End-to-End Example

```python
# Django example
from mixin_logging import LoggingMixin
from mixin_logging.adapters.wsgi import CorrelationIdMiddleware
from mixin_logging.adapters.httpx import CorrelationIdInjector
import httpx

MIDDLEWARE = [
    "mixin_logging.adapters.wsgi.CorrelationIdMiddleware",
    # ... other middleware ...
]

client = httpx.Client(event_hooks=CorrelationIdInjector.event_hooks())

class OrderService(LoggingMixin):
    def create(self, order_id: int):
        self.log_info("order.create", order_id=order_id)  # Includes correlation_id
        # Make outbound call with correlation ID automatically injected
        response = client.get(f"https://api.internal.example.com/orders/{order_id}")
        return response.json()

def order_view(request):
    # WSGI middleware has set correlation ID from request headers
    service = OrderService()
    return JsonResponse(service.create(order_id=123))
```

Request flow:
1. Client sends request with `X-Correlation-ID: req-123`
2. WSGI middleware extracts it into context
3. View runs, calls `OrderService.create()`
4. LoggingMixin logs include correlation_id automatically
5. Outbound httpx call includes `X-Correlation-ID: req-123` header
6. Response includes `X-Correlation-ID: req-123` header

## See Also

- [ASGI adapter](asgi.md) :  For async frameworks (FastAPI, Starlette, Quart)
- [Correlation context API](../context/correlation.md)
- [Outbound adapters](README.md#outbound-clients) :  HTTPX, Requests, Botocore
