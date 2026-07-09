# Adapters

The adapter suite provides end-to-end correlation-ID propagation across HTTP frameworks, outbound clients, task queues, and AWS services.

## Overview

Adapters are grouped by where they operate in a request/response lifecycle:

| Group | Purpose | Adapters |
|-------|---------|----------|
| **Inbound HTTP** | Extract/generate correlation ID at request entry | [ASGI](asgi.md), [WSGI](wsgi.md) |
| **Inbound edge** | Extract/generate for WebSocket, gRPC, GraphQL | [WebSocket](websocket.md), [gRPC](grpc.md), [GraphQL](graphql.md) |
| **Outbound clients** | Inject correlation ID into downstream calls | [HTTPX](httpx.md), [Requests](requests.md), [aiohttp](aiohttp.md), [urllib3](urllib3.md), [Botocore](botocore.md) |
| **Task/async** | Propagate across task publish → execute | [Celery](celery.md) |
| **Logging** | Stamp correlation ID on all log records | [Stdlib](stdlib.md) |
| **Serverless** | Extract from AWS Lambda events | [Cloud](cloud.md) |

## Quick Navigation

### Inbound HTTP

- **[ASGI](asgi.md)** :  FastAPI, Starlette, Quart. Extract correlation ID from request headers or generate UUID. Inject into response headers. Security-hardened (CRLF injection, log injection, DoS protection).
- **[WSGI](wsgi.md)** :  Django, Flask, Pyramid. Extract/generate correlation ID. Inject response header.

### Inbound Edge

- **[WebSocket](websocket.md)** :  Starlette, Channels. Extract/generate correlation ID from WebSocket handshake headers.
- **[gRPC](grpc.md)** :  gRPC servers. Extract/generate correlation ID from invocation metadata via server interceptor.
- **[GraphQL](graphql.md)** :  Strawberry, Ariadne. Inject correlation ID into resolver context for downstream resolvers.

### Outbound Clients

- **[HTTPX](httpx.md)** :  `httpx.Client` and `httpx.AsyncClient`. Inject `X-Correlation-ID` header on every request via event hooks.
- **[Requests](requests.md)** :  `requests.Session`. Inject `X-Correlation-ID` header via HTTP adapter.
- **[aiohttp](aiohttp.md)** :  `aiohttp.ClientSession`. Inject `X-Correlation-ID` header via TraceConfig.
- **[urllib3](urllib3.md)** :  `urllib3.PoolManager`. Inject `X-Correlation-ID` header on every request.
- **[Botocore](botocore.md)** :  AWS SDK (boto3). Inject correlation ID into AWS service calls via event system.

### Task & Async

- **[Celery](celery.md)** :  Propagate correlation ID across task publish → prerun → postrun via Celery signals.

### Logging

- **[Stdlib](stdlib.md)** :  `logging.Filter`. Stamp `correlation_id` on every `LogRecord`.

### Serverless

- **[Cloud](cloud.md)** :  AWS Lambda. Extract correlation ID from API Gateway v1/v2, ALB, SQS, SNS, EventBridge, or direct-invoke events. Auto-generate fallback if not present.

## Typical Flow

1. **Request entry:** Use ASGI or WSGI adapter to extract/generate correlation ID
2. **Logging setup:** Add Stdlib adapter to ensure all logs carry correlation_id
3. **Service code:** Use `LoggingMixin` for class-bound logging (automatic injection)
4. **Outbound calls:** Instrument clients (HTTPX, Requests, Botocore) to propagate downstream
5. **Background tasks:** Instrument Celery to propagate across task boundaries
6. **Serverless:** Use Cloud adapter to extract from Lambda events

Example:

```python
from fastapi import FastAPI
from mixin_logging.adapters.asgi import CorrelationIdMiddleware
from mixin_logging.adapters.httpx import CorrelationIdInjector
from mixin_logging import LoggingMixin
import httpx

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)  # Set correlation ID from request

client = httpx.Client(event_hooks=CorrelationIdInjector.event_hooks())

class OrderService(LoggingMixin):
    def create(self, order_id: int):
        self.log_info("order.create", order_id=order_id)  # Includes correlation_id
        # Make outbound call with correlation ID automatically injected
        response = client.get(f"https://api.internal.example.com/orders/{order_id}")
        return response.json()
```

## Installation

Core library (required):

```bash
uv add logging-mixin
```

Optional dependencies for specific adapters:

```bash
uv add "logging-mixin[aiohttp]"    # aiohttp client instrumentation
uv add "logging-mixin[urllib3]"    # urllib3 client instrumentation
uv add "logging-mixin[celery]"     # Celery propagation
uv add "logging-mixin[requests]"   # Requests client instrumentation
uv add "logging-mixin[grpc]"       # gRPC server instrumentation
```

Note: ASGI, WSGI, HTTPX, Botocore, Stdlib, Cloud, WebSocket, and GraphQL adapters have no external dependencies beyond the standard library.

## Design Philosophy

- **Zero boilerplate** :  Adapters hook into framework middleware/event systems automatically
- **Opt-in per adapter** :  Use only what you need; no unused instrumentation
- **Framework-agnostic core** :  logging-mixin itself has zero dependencies
- **Security-hardened** :  Input validation, CRLF injection prevention, length limits
- **ContextVar-based** :  Survives async/await, thread pools, and background tasks

## See Also

- [Correlation context API](../context/correlation.md)
- [LoggingMixin](../mixin/mixin.md)
- [Logged decorator](../decorators/logged.md)
