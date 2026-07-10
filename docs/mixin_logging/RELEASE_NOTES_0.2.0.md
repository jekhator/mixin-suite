# Release Notes - 0.2.0

**2026-06-03**

## Overview

logging-mixin 0.2.0 ships the complete **correlation-ID adapter suite** for end-to-end request tracing across HTTP frameworks, outbound clients, task queues, and AWS services.

## Major Features

### Complete Adapter Suite (8 adapters)

All adapters are now available in `mixin_logging/adapters/`:

- **ASGI Adapter**: FastAPI, Starlette, Quart, and other ASGI frameworks. Extract or generate correlation ID from request scope. Inject into response headers. **Security-hardened:** CRLF injection prevention, log injection prevention, unbounded length DoS protection, encoding-error DoS protection.

- **WSGI Adapter**: Django, Flask, Pyramid, and other WSGI frameworks. Inbound middleware extraction and response header injection.

- **HTTPX Adapter**: `httpx.Client` and `httpx.AsyncClient`. Inject `X-Correlation-ID` header on every request via event hooks.

- **Requests Adapter**: `requests.Session`. Inject `X-Correlation-ID` header via HTTP adapter interface.

- **Botocore Adapter**: AWS SDK (boto3). Inject correlation ID into all AWS service calls via event system hooks.

- **Celery Adapter**: Task-boundary propagation. Maintains correlation ID across task publish → prerun → postrun via Celery signals.

- **Stdlib Adapter**: `logging.Filter` implementation. Stamps `correlation_id` on every `LogRecord` automatically.

- **Cloud Adapter**: AWS Lambda inbound. Supports API Gateway (v1/v2), ALB, SQS, SNS, EventBridge, and direct-invoke. Auto-generates fallback correlation ID if not present.

### ASGI Security Hardening

All critical and medium security vulnerabilities remediated:

- **Response header / CRLF injection**: Fixed via control character validation + validate-and-regenerate semantics
- **Log injection / forging**: Fixed via validation; no newlines or control characters reach logging or response headers
- **Unbounded length DoS**: Fixed via `CORRELATION_ID_MAX_LENGTH = 128` + length check
- **Encoding-error DoS**: Fixed via try-except guard on UTF-8 decode; invalid UTF-8 triggers safe UUID4 fallback
- **100% test coverage** for all attack vectors

## Dependency & Infrastructure Changes

### Dependency Management

- **Adopted `uv`**: Faster, more predictable lock-file generation. Committed `uv.lock`; CI migrated to `astral-sh/setup-uv@v2`

### Python Version Requirement

- **Dropped Python 3.10 support**: Now requires **Python >=3.11** (3.11 and 3.12 supported)

### Package Layout

- **Root-layout restructure**: Moved all adapter code to `mixin_logging/adapters/` with specialized adapter modules (8 adapters, each with `objects/` + `client/` split)

## Installation

```bash
uv add logging-mixin
```

With optional dependencies:

```bash
uv add "logging-mixin[celery]"      # Celery task propagation
uv add "logging-mixin[requests]"    # Requests client instrumentation
```

Requires Python 3.11+.

## Usage Example

End-to-end correlation ID propagation:

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
        # Outbound call automatically includes correlation ID header
        response = client.get(f"https://api.internal.example.com/orders/{order_id}")
        return response.json()

@app.get("/orders/{order_id}")
async def handle_order(order_id: int):
    service = OrderService()
    return service.create(order_id)
```

## Documentation

- `docs/`: Complete documentation (architecture, adapters, context, decorators)
- `docs/architecture/architecture.md`: System design and package structure
- `docs/apps/adapters/README.md`: Adapter overview and navigation
- `docs/apps/adapters/`: Per-adapter documentation (ASGI, WSGI, HTTPX, Requests, Botocore, Celery, Stdlib, Cloud)
- `README.md`: Updated with 0.2.0 features and adapter suite reference

## Breaking Changes

None. 0.2.0 is backward-compatible with 0.1.x `LoggingMixin` API.

## Removed

- Python 3.10 classifier: Dropped from supported versions in `pyproject.toml`

## Contributors

Built with security-first, async-safe, and framework-agnostic design principles.

## See Also

- [README.md](../../README.md): Quick start and core API
- [docs/apps/adapters/README.md](apps/adapters/README.md): Complete adapter overview
