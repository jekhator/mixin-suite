# logging-mixin. gRPC Adapter

> **Location:** `logging-mixin/docs/apps/adapters/grpc.md`
> **Status:** Implemented. Inbound correlation-ID extraction and context setup via gRPC ServerInterceptor.
> **Code location:** `mixin_logging/adapters/grpc/` (`grpc_objects.py` + `grpc_client.py`); constants in `mixin_logging/adapters/constants/grpc.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Adapter Categories & Data Flow).
> **Sibling docs:** `docs/apps/adapters/asgi.md`, `docs/apps/adapters/wsgi.md`, `docs/apps/context/correlation.md`.

## Purpose

Extract correlation ID from inbound gRPC invocation metadata and set up the correlation context for downstream handlers so a single inbound request can be traced through every downstream call and into logging and external services.

## Category

Inbound/Ingress, the same category as the ASGI and WSGI adapters, specialized for the gRPC protocol rather than HTTP frameworks.

## Behavior

- `CorrelationInterceptor` is a `grpc.ServerInterceptor` registered on a gRPC server.
- On each inbound RPC invocation, `intercept_service()` is called with the handler call details.
- The interceptor extracts the correlation ID from invocation metadata via `GRPCCorrelation.from_metadata()`. If the metadata key is present and safe, the ID is extracted with `extracted=True`; if absent or unsafe, a new UUID4 hex[:12] ID is generated with `extracted=False`.
- The correlation ID is set in the `CorrelationContext` via `set_correlation_id()`.
- The RPC handler is invoked via `continuation()`.
- After the handler completes or raises, the correlation context is cleared via `clear_correlation_id()` in a finally block, ensuring isolation between requests.

## Value Object

`GRPCCorrelation` (frozen, slots) captures the correlation ID resolved from gRPC metadata:

- `correlation_id: str`. The extracted or generated correlation ID.
- `extracted: bool`. True if the ID was extracted from metadata, False if generated.
- `from_metadata(metadata)`. Class method. Extract correlation ID from gRPC invocation metadata (tuple of (name, value) pairs); returns a GRPCCorrelation with extracted=True if the metadata contains a safe `x-correlation-id` key, or a fresh UUID4 hex[:12] with extracted=False if absent or unsafe.
- `_is_safe(value)`. Static method. Return True if value is non-empty, within 128 chars, and contains no CR/LF/null bytes.
- `__post_init__` + invariant validation. Raise ValueError if correlation_id is unsafe, enforcing the invariant at construction time.

## Constants

`mixin_logging/adapters/constants/grpc.py`:

- `CORRELATION_ID_KEY = "x-correlation-id"` (lowercase, matches inbound ASGI/WSGI for round-trip consistency)
- `CORRELATION_ID_MAX_LENGTH = 128`
- `GENERATED_ID_LENGTH = 12` (length of UUID4 hex[:12])
- `UNSAFE_CHARS = frozenset({"\r", "\n", "\0"})` (carriage return, line feed, null byte)
- `ERR_CORRELATION_ID_UNSAFE` (error message for validation failure)

## Design Note

gRPC servers use `ServerInterceptor.intercept_service()` as the universal per-request entry point. The interceptor receives the `handler_call_details` with `invocation_metadata` as a tuple of (name, value) pairs. Names are strings; values are either strings or bytes. The correlation ID is extracted at this low level to ensure it reaches every RPC method invoked through the server, regardless of the calling pattern. The metadata is passed through to the actual handler after setup; no filtering occurs.

## Compatibility

gRPC Python library (modern async/sync RPC framework). Requires the `[grpc]` extra to be installed.

## Example Usage

```python
import grpc
from mixin_logging.adapters.grpc import CorrelationInterceptor

def serve():
    server = grpc.aio.server(
        interceptors=[CorrelationInterceptor()]
    )
    # Add services to server
    server.add_insecure_port("[::]:50051")
    await server.start()
    await server.wait_for_termination()

# Incoming RPC now sets up correlation context automatically.
# All logging within the handler includes the correlation ID.
```

Or with synchronous gRPC:

```python
import grpc
from mixin_logging.adapters.grpc import CorrelationInterceptor

server = grpc.server(
    thread_pool=grpc.ThreadPoolExecutor(max_workers=10),
    interceptors=[CorrelationInterceptor()]
)
# Add services to server
server.add_insecure_port("[::]:50051")
server.start()
server.wait_for_termination()
```

Every RPC now carries correlation-ID context from inbound metadata or a freshly generated ID, and all logs from the handler inherit that context.

## See Also

- **Adapters overview / ASGI:** `docs/apps/adapters/asgi.md`
- **Adapters overview / WSGI:** `docs/apps/adapters/wsgi.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
- **Correlation Context:** `docs/apps/context/correlation.md`
