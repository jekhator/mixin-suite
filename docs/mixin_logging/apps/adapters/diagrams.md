# logging-mixin. Adapters (Diagrams)

> **Location:** `logging-mixin/docs/apps/adapters/diagrams.md`
> **Status:** Reference diagrams for all 13 adapters. Updated 2026-06-19.
> **Sibling docs:** `docs/apps/adapters/asgi.md`, `docs/apps/adapters/botocore.md`

## ASGI Subsystem Structure

> **File path:** `mixin_logging/adapters/asgi/`

```
mixin_logging/adapters/asgi/asgi_objects.py
================================================
  Imports: from __future__ import annotations
           from collections.abc import (
             Awaitable,
             Callable,
             MutableMapping)
           from dataclasses import dataclass
           from typing import Any, Self
           from uuid import uuid4
           from mixin_logging.adapters.constants import asgi as const

  Type aliases:
    Scope = MutableMapping[str, Any]
    Message = MutableMapping[str, Any]
    Receive = Callable[[], Awaitable[Message]]
    Send = Callable[[Message], Awaitable[None]]
    App = Callable[[Scope, Receive, Send], Awaitable[None]]

──────────────────────────────────────────────────────────────────────────
[FROZEN]  AsgiCorrelation                         ← extracted or generated correlation ID
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id  : str                        (extracted from request or uuid4 fallback)
  ├─ from_header     : bool                       (True if read from scope header)
  │
  ├─ [vld] __post_init__(self) -> None            ← raise ValueError if correlation_id empty
  ├─ [vld @staticmethod] _is_safe(value) -> bool  ← reject CR/LF/null + length > 128
  ├─ [fct] from_scope(cls, scope) -> Self         ← Parse scope["headers"] for x-correlation-id
  │                                                 If found+UTF-8-valid+safe: decode + return
  │                                                 If decode-error or unsafe or miss: uuid4()
  └─ [prp] response_header -> tuple[bytes, bytes] ← (CORRELATION_ID_HEADER, correlation_id.encode())


mixin_logging/adapters/asgi/asgi_client.py
================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from mixin_logging import (
             clear_correlation_id,
             set_correlation_id)
           from mixin_logging.adapters.asgi import asgi_objects as objs
           from mixin_logging.adapters.constants import asgi as const

──────────────────────────────────────────────────────────────────────────
[FROZEN]  ASGIApp                                 ← wraps app with correlation context
──────────────────────────────────────────────────────────────────────────
  ├─ app         : objs.App
  ├─ correlation : objs.AsgiCorrelation
  │
  └─ [mth] async __call__(self, scope, receive, send) -> None
               ← set_correlation_id(correlation.correlation_id)
                 then delegate to wrapped app

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationIdMiddleware                 ← public ASGI middleware
──────────────────────────────────────────────────────────────────────────
  ├─ app : objs.App                               (wrapped ASGI app)
  │
  └─ [mth] async __call__(self, scope, receive, send) -> None
               ← HTTP scope only:
                 1. Resolve via AsgiCorrelation.from_scope()
                 2. Wrap send to inject correlation header on http.response.start
                 3. Execute via ASGIApp(app, correlation)
                 4. Clear context in finally
                 Non-HTTP scope: passthrough

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/adapters/constants/asgi.py
──────────────────────────────────────────────────────────────────────────
  CORRELATION_ID_HEADER         = b"x-correlation-id"
  CORRELATION_ID_MAX_LENGTH     = 128
  HTTP_SCOPE_TYPE               = "http"
  RESPONSE_START_MESSAGE_TYPE   = "http.response.start"
```


---

## Botocore Subsystem Structure

> **File path:** `mixin_logging/adapters/botocore/`

```
mixin_logging/adapters/botocore/botocore_objects.py
========================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from typing import Self
           from mixin_logging import get_correlation_id
           from mixin_logging.adapters.constants import botocore as const

──────────────────────────────────────────────────────────────────────────
[FROZEN]  BotocoreCorrelation                     ← correlation ID bound for an outbound AWS request
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id : str                         (read from ContextVar; not PHI)
  │
  ├─ [vld] __post_init__(self) -> None            ← raise ValueError(ERR_CORRELATION_ID_UNSAFE) if unsafe
  ├─ [fct] from_context(cls) -> Self | None       ← read ContextVar; None if unset or unsafe (no raise)
  ├─ [prp] header_tuple -> tuple[str, str]        ← (CORRELATION_ID_HEADER, correlation_id)
  └─ [vld @staticmethod] _is_safe(value) -> bool  ← reject empty, length > 128, CR/LF/null


mixin_logging/adapters/botocore/botocore_client.py
========================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from typing import Any
           from mixin_logging.adapters.botocore import botocore_objects as objs
           from mixin_logging.adapters.constants import botocore as const

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationIdInjector                   ← stateless before-sign event-hook surface
──────────────────────────────────────────────────────────────────────────
  ├─ [mth @classmethod] register_on_session(cls, session) -> None
  │            ← session.register(BEFORE_SIGN_EVENT, inject_before_sign)
  ├─ [mth @classmethod] register_on_client(cls, client) -> None
  │            ← client.meta.events.register(BEFORE_SIGN_EVENT, inject_before_sign)
  └─ [mth @classmethod] inject_before_sign(cls, request, **kwargs) -> None
               ← 1. correlation = BotocoreCorrelation.from_context()
                 2. None (unset/unsafe) → no-op
                 3. set X-Correlation-ID on request.headers (replace_header if present)
                 Registered on before-sign so the header is part of the SigV4 canonical request

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/adapters/constants/botocore.py
──────────────────────────────────────────────────────────────────────────
  CORRELATION_ID_HEADER       = "X-Correlation-ID"
  CORRELATION_ID_MAX_LENGTH   = 128
  BEFORE_SIGN_EVENT           = "before-sign"
  UNSAFE_HEADER_CHARS         = frozenset({"\r", "\n", "\0"})
  ERR_CORRELATION_ID_UNSAFE   = "correlation_id must be non-empty, within length cap, free of unsafe chars"
```


---

## aiohttp Subsystem Structure

> **File path:** `mixin_logging/adapters/aiohttp/`

```
mixin_logging/adapters/aiohttp/aiohttp_objects.py
========================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from typing import Self
           from mixin_logging import get_correlation_id
           from mixin_logging.adapters.constants import aiohttp as const

──────────────────────────────────────────────────────────────────────────
[FROZEN]  AiohttpCorrelation                        ← correlation ID for aiohttp outbound requests
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id : str                         (read from ContextVar; not PHI)
  │
  ├─ [vld] __post_init__(self) -> None            ← raise ValueError(ERR_CORRELATION_ID_UNSAFE) if unsafe
  ├─ [fct] from_context(cls) -> Self | None       ← read ContextVar; None if unset or unsafe (no raise)
  ├─ [prp] header_tuple -> tuple[str, str]        ← (CORRELATION_ID_HEADER, correlation_id)
  └─ [vld @staticmethod] _is_safe(value) -> bool  ← reject empty, length > 128, CR/LF/null


mixin_logging/adapters/aiohttp/aiohttp_client.py
========================================================
  Imports: from __future__ import annotations
           import aiohttp
           from mixin_logging.adapters.aiohttp import aiohttp_objects as objs

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationIdInjector                    ← stateless TraceConfig surface
──────────────────────────────────────────────────────────────────────────
  ├─ [mth @classmethod] trace_config(cls) -> aiohttp.TraceConfig
  │            ← aiohttp.TraceConfig with on_request_start handler
  └─ [mth @staticmethod] async _inject(...) -> None
               ← Inject X-Correlation-ID into outbound request

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/adapters/constants/aiohttp.py
──────────────────────────────────────────────────────────────────────────
  CORRELATION_ID_HEADER         = "X-Correlation-ID"
  CORRELATION_ID_MAX_LENGTH     = 128
  UNSAFE_HEADER_CHARS           = frozenset({"\r", "\n", "\0"})
  ERR_CORRELATION_ID_UNSAFE     = "correlation_id must be non-empty, within length cap, free of unsafe chars"
```


---

## urllib3 Subsystem Structure

> **File path:** `mixin_logging/adapters/urllib3/`

```
mixin_logging/adapters/urllib3/urllib3_objects.py
========================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from typing import Self
           from mixin_logging import get_correlation_id
           from mixin_logging.adapters.constants import urllib3 as const

──────────────────────────────────────────────────────────────────────────
[FROZEN]  Urllib3Correlation                       ← correlation ID for urllib3 outbound requests
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id : str                         (read from ContextVar; not PHI)
  │
  ├─ [vld] __post_init__(self) -> None            ← raise ValueError(ERR_CORRELATION_ID_UNSAFE) if unsafe
  ├─ [fct] from_context(cls) -> Self | None       ← read ContextVar; None if unset or unsafe (no raise)
  ├─ [prp] header_tuple -> tuple[str, str]        ← (CORRELATION_ID_HEADER, correlation_id)
  └─ [vld @staticmethod] _is_safe(value) -> bool  ← reject empty, length > 128, CR/LF/null


mixin_logging/adapters/urllib3/urllib3_client.py
========================================================
  Imports: from __future__ import annotations
           from typing import Any
           import urllib3
           from mixin_logging.adapters.urllib3 import urllib3_objects as objs

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationIdPoolManager                 ← PoolManager subclass with header injection
──────────────────────────────────────────────────────────────────────────
  └─ [mth] urlopen(method, url, **kwargs) -> urllib3.BaseHTTPResponse
               ← Extract correlation from context
                 Inject X-Correlation-ID into headers
                 Call parent urlopen

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/adapters/constants/urllib3.py
──────────────────────────────────────────────────────────────────────────
  CORRELATION_ID_HEADER         = "X-Correlation-ID"
  CORRELATION_ID_MAX_LENGTH     = 128
  UNSAFE_HEADER_CHARS           = frozenset({"\r", "\n", "\0"})
  ERR_CORRELATION_ID_UNSAFE     = "correlation_id must be non-empty, within length cap, free of unsafe chars"
```


---

## gRPC Subsystem Structure

> **File path:** `mixin_logging/adapters/grpc/`

```
mixin_logging/adapters/grpc/grpc_objects.py
========================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from typing import Self
           from uuid import uuid4
           from mixin_logging.adapters.constants import grpc as const

  Type aliases:
    Metadata = tuple[tuple[str, str | bytes], ...]

──────────────────────────────────────────────────────────────────────────
[FROZEN]  GRPCCorrelation                          ← extracted or generated correlation ID
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id : str                         (extracted from metadata or uuid4 fallback)
  ├─ extracted      : bool                        (True if read from invocation metadata)
  │
  ├─ [vld] __post_init__(self) -> None            ← raise ValueError if correlation_id unsafe
  ├─ [vld @staticmethod] _is_safe(value) -> bool  ← reject empty, length > 128, CRLF/null
  └─ [fct] from_metadata(cls, metadata) -> Self   ← Parse gRPC invocation metadata
                                                    If found+safe: decode + return
                                                    If absent or unsafe: uuid4()


mixin_logging/adapters/grpc/grpc_client.py
========================================================
  Imports: from __future__ import annotations
           from collections.abc import Callable
           import grpc
           from mixin_logging import clear_correlation_id, set_correlation_id
           from mixin_logging.adapters.grpc import grpc_objects as objs

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationInterceptor                   ← gRPC server interceptor
──────────────────────────────────────────────────────────────────────────
  └─ [mth] intercept_service(continuation, handler_call_details) -> RpcMethodHandler | None
               ← Extract correlation from invocation metadata
                 Set ContextVar for handler execution
                 Delegate to continuation
                 Clear context in finally

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/adapters/constants/grpc.py
──────────────────────────────────────────────────────────────────────────
  CORRELATION_ID_KEY            = "x-correlation-id"
  CORRELATION_ID_MAX_LENGTH     = 128
  GENERATED_ID_LENGTH           = 12
  UNSAFE_CHARS                  = frozenset({"\r", "\n", "\0"})
  ERR_CORRELATION_ID_UNSAFE     = "correlation_id must be non-empty, within length cap, free of unsafe chars"
```


---

## WebSocket Subsystem Structure

> **File path:** `mixin_logging/adapters/websocket/`

```
mixin_logging/adapters/websocket/websocket_objects.py
========================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from typing import Self
           from uuid import uuid4
           from mixin_logging.adapters.constants import websocket as const

  Type aliases:
    Headers = list[tuple[bytes, bytes]]

──────────────────────────────────────────────────────────────────────────
[FROZEN]  WebSocketCorrelation                     ← extracted or generated correlation ID
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id : str                         (extracted from handshake or uuid4 fallback)
  ├─ extracted      : bool                        (True if read from headers)
  │
  ├─ [vld] __post_init__(self) -> None            ← raise ValueError if correlation_id unsafe
  ├─ [vld @staticmethod] _is_safe(value) -> bool  ← reject empty, length > 128, CRLF/null
  └─ [fct] from_headers(cls, headers) -> Self     ← Parse WS handshake headers
                                                    If found+UTF-8-valid+safe: decode + return
                                                    If absent or unsafe: uuid4()


mixin_logging/adapters/websocket/websocket_client.py
========================================================
  Imports: from __future__ import annotations
           from typing import Any
           from mixin_logging import clear_correlation_id, set_correlation_id
           from mixin_logging.adapters.websocket import websocket_objects as objs

  Type aliases:
    Scope = dict[str, Any]
    Receive = Any
    Send = Any
    App = Any

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationIdMiddleware                  ← ASGI WebSocket middleware
──────────────────────────────────────────────────────────────────────────
  ├─ app : App                                    (wrapped ASGI app)
  │
  └─ [mth] async __call__(scope, receive, send) -> None
               ← WebSocket scope only:
                 1. Resolve via WebSocketCorrelation.from_headers()
                 2. Set correlation ID in context
                 3. Execute via wrapped app
                 4. Clear context in finally
                 Other scopes: passthrough

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/adapters/constants/websocket.py
──────────────────────────────────────────────────────────────────────────
  CORRELATION_ID_HEADER         = "x-correlation-id"
  CORRELATION_ID_MAX_LENGTH     = 128
  GENERATED_ID_LENGTH           = 12
  UNSAFE_HEADER_CHARS           = frozenset({"\r", "\n", "\0"})
  ERR_CORRELATION_ID_UNSAFE     = "correlation_id must be non-empty, within length cap, free of unsafe chars"
```


---

## GraphQL Subsystem Structure

> **File path:** `mixin_logging/adapters/graphql/`

```
mixin_logging/adapters/graphql/graphql_objects.py
========================================================
  Imports: from __future__ import annotations
           from dataclasses import dataclass
           from typing import Self
           from mixin_logging import get_correlation_id
           from mixin_logging.adapters.constants import graphql as const

──────────────────────────────────────────────────────────────────────────
[FROZEN]  GraphQLCorrelation                       ← correlation ID for resolver context
──────────────────────────────────────────────────────────────────────────
  ├─ correlation_id : str | None                  (read from ContextVar; may be None)
  │
  ├─ [fct] from_context(cls) -> Self              ← Read ContextVar (set upstream by ASGI/WSGI)
  └─ [prp] as_context_dict() -> dict[str, str | None]
                                                   ← Return {CONTEXT_KEY: correlation_id}


mixin_logging/adapters/graphql/graphql_client.py
========================================================
  Imports: from __future__ import annotations
           from typing import Any
           from mixin_logging.adapters.graphql import graphql_objects as objs

──────────────────────────────────────────────────────────────────────────
[FROZEN]  CorrelationContextInjector               ← stateless context merger
──────────────────────────────────────────────────────────────────────────
  └─ [mth @staticmethod] inject(context) -> dict[str, Any]
               ← Extract correlation from context
                 Merge into resolver context dict
                 Return new dict

──────────────────────────────────────────────────────────────────────────
Module constants, mixin_logging/adapters/constants/graphql.py
──────────────────────────────────────────────────────────────────────────
  CONTEXT_KEY                   = "correlation_id"
```


---

## Adapter Categories & Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                                 INBOUND / INGRESS                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐           │
│  │  ASGI Middleware │    │  WSGI Middleware │    │  Cloud Handler   │           │
│  │  (FastAPI, etc)  │    │  (Django, Flask) │    │  (AWS Lambda)    │           │
│  │                  │    │                  │    │                  │           │
│  │ • Extract header │    │ • Extract header │    │ • Extract header │           │
│  │ • Generate UUID  │    │ • Generate UUID  │    │ • Generate UUID  │           │
│  │ • Set context    │    │ • Set context    │    │ • Set context    │           │
│  └────────┬─────────┘    └────────┬─────────┘    └────────┬─────────┘           │
│           │                       │                       │                      │
│           └───────────────────────┴───────────────────────┘                      │
│                           │                                                      │
│                           ↓                                                      │
│           ┌───────────────────────────────┐                                     │
│           │  ContextVar[CorrelationContext]                                    │
│           │  _client.set_id(correlation_id)                                    │
│           └───────────────┬───────────────┘                                     │
│                           │                                                      │
└───────────────────────────┼──────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION / SERVICE CODE                             │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌──────────────────────┐                                                       │
│  │  LoggingMixin        │ ← Pulls correlation_id from ContextVar                │
│  │  log_info()          │   via _client.current_id()                            │
│  │  log_error()         │   → All logs include correlation_id field             │
│  └──────────────────────┘                                                       │
│                                                                                   │
│  ┌──────────────────────┐                                                       │
│  │  @logged decorator   │ ← Inherits correlation_id via LoggingMixin            │
│  │  emit start/error    │   → Decorated method logs include correlation_id      │
│  └──────────────────────┘                                                       │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                         OUTBOUND / EGRESS ADAPTERS                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  │
│  │  HTTPX Client        │  │  Requests Session    │  │  Celery Task         │  │
│  │  Propagation         │  │  Propagation         │  │  Propagation         │  │
│  │                      │  │                      │  │                      │  │
│  │ • Read current_id()  │  │ • Read current_id()  │  │ • Inject into task   │  │
│  │ • Inject header      │  │ • Inject header      │  │   metadata           │  │
│  │ • Call downstream    │  │ • Call downstream    │  │ • Task consumer      │  │
│  │                      │  │                      │  │   extracts + sets    │  │
│  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘  │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            OUTPUT SINK ADAPTER                                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                   │
│  ┌────────────────────────────────────────────────────────────────────────────┐ │
│  │  stdlib.py, logging.Filter                                                │ │
│  │                                                                              │ │
│  │  • Injects correlation_id into every LogRecord                            │ │
│  │  • Pulls from ContextVar via _client.current_id()                         │ │
│  │  • Defaults to "-" if unset                                               │ │
│  │  • Covers all logs: LoggingMixin, @logged, third-party, stdlib            │ │
│  │                                                                              │ │
│  └────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

## Request Lifecycle with ASGI Middleware

```
HTTP Request
     │
     ↓
┌─────────────────────────────────────────────────┐
│  ASGI Middleware Entry                          │
│  ┌───────────────────────────────────────────┐  │
│  │ Extract X-Correlation-ID from headers     │  │
│  │  → Found: use it                          │  │
│  │  → Missing: generate UUID4 hex[:12]       │  │
│  └───────────┬───────────────────────────────┘  │
│              │                                   │
│              ↓                                   │
│  ┌───────────────────────────────────────────┐  │
│  │ _client.set_id(correlation_id)            │  │
│  │ (sets ContextVar for request scope)       │  │
│  └───────────┬───────────────────────────────┘  │
└──────────────┼──────────────────────────────────┘
               │
               ↓
        ┌──────────────────┐
        │ Application Code │ ← Inherits correlation_id via ContextVar
        │ (FastAPI handler)│
        │                  │
        │ → LoggingMixin   │ ← Auto-includes in all log events
        │ → Call services  │
        │ → Maybe: HTTPX   │ ← Injects header on outbound calls
        │   outbound call  │
        └────────┬─────────┘
                 │
                 ↓
┌─────────────────────────────────────────────────┐
│  ASGI Middleware Exit                           │
│  ┌───────────────────────────────────────────┐  │
│  │ _client.clear()                           │  │
│  │ (reset context after request)             │  │
│  └───────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────┐  │
│  │ response.headers["X-Correlation-ID"] =    │  │
│  │   correlation_id                          │  │
│  │ (return correlation_id to caller)         │  │
│  └───────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
               │
               ↓
        HTTP Response
     (headers include X-Correlation-ID)
```

## Celery Task Propagation Lifecycle

```
┌────────────────────────────────────────────────┐
│  Producer (e.g., HTTP handler)                 │
├────────────────────────────────────────────────┤
│                                                 │
│  1. HTTP request enters                        │
│     _client.set_id("req-123")                  │
│                                                 │
│  2. Application calls Celery task:             │
│     process_order.delay(order_id=42)           │
│                                                 │
│  3. Celery signal (before_task_publish):       │
│     Extract current_id() → "req-123"           │
│     Inject into task.kwargs["__correlation_id│
│       "]                                        │
│                                                 │
└─────────────────────────────────────────────────┘
                    │
                    ↓
            (Task queued to broker)
                    │
                    ↓
┌────────────────────────────────────────────────┐
│  Consumer (Celery worker)                      │
├────────────────────────────────────────────────┤
│                                                 │
│  1. Task dequeued from broker                  │
│                                                 │
│  2. Celery signal (task_prerun):               │
│     Extract "__correlation_id" from task data  │
│     _client.set_id("req-123")                  │
│                                                 │
│  3. Execute task body:                         │
│     @app.task                                  │
│     def process_order(order_id):               │
│         svc = OrderService()                   │
│         svc.process(order_id)                  │
│         ← LoggingMixin logs auto-include       │
│           correlation_id="req-123"             │
│                                                 │
│  4. Celery signal (task_postrun):              │
│     _client.clear()                            │
│                                                 │
└────────────────────────────────────────────────┘
```

## Module & Constant Organization

```
mixin_logging/
├── apps/
│   ├── adapters/
│   │   ├── __init__.py              ← Re-exports all adapters
│   │   ├── asgi/
│   │   │   ├── asgi_objects.py
│   │   │   └── asgi_client.py
│   │   ├── wsgi.py                  ← WSGI middleware (no extra)
│   │   ├── cloud.py                 ← Cloud/Lambda handler (no extra)
│   │   ├── stdlib.py                ← logging.Filter (no extra)
│   │   ├── httpx.py                 ← HTTPX client (extra: [httpx])
│   │   ├── requests.py              ← Requests client (extra: [requests])
│   │   ├── celery.py                ← Celery integration (extra: [celery])
│   │   └── constants/
│   │       └── asgi.py              ← HEADER_NAME, UUID4_HEX_LENGTH
│   │
│   └── context/
│       └── correlation/
│           ├── correlation_objects.py
│           └── correlation_client.py  ← _client singleton (used by all adapters)

Public Access Points:
  from mixin_logging.adapters.asgi import CorrelationIdMiddleware
  from mixin_logging.adapters.constants import asgi
  from mixin_logging import _client, set_correlation_id, get_correlation_id
```

## Adapter Coverage Map

| Framework | Protocol | Adapter | Extra | Status |
|-----------|----------|---------|-------|--------|
| FastAPI | ASGI | `asgi/` | None | Implemented |
| Starlette | ASGI | `asgi/` | None | Implemented |
| Quart | ASGI | `asgi/` | None | Implemented |
| Django | WSGI | `wsgi/` | None | Implemented |
| Flask | WSGI | `wsgi/` | None | Implemented |
| Pyramid | WSGI | `wsgi/` | None | Implemented |
| AWS Lambda | Event-based | `cloud/` | None | Implemented |
| GCP Cloud Functions | Event-based | `cloud/` | None | Implemented |
| Azure Functions | Event-based | `cloud/` | None | Implemented |
| HTTPX | HTTP Client | `httpx/` | `[httpx]` | Implemented |
| boto3 / botocore | AWS SDK | `botocore/` | `[botocore]` | Implemented (before-sign injection) |
| Requests | HTTP Client | `requests/` | `[requests]` | Implemented |
| Celery | Task Queue | `celery/` | `[celery]` | Implemented |
| Stdlib Logging | Output | `stdlib/` | None | Implemented |
| aiohttp | HTTP Client | `aiohttp/` | `[aiohttp]` | Implemented |
| urllib3 | HTTP Client | `urllib3/` | `[urllib3]` | Implemented |
| gRPC | gRPC Server | `grpc/` | `[grpc]` | Implemented |
| WebSocket (Starlette/Channels) | ASGI websocket | `websocket/` | None | Implemented |
| GraphQL (Strawberry/Ariadne) | Resolver context | `graphql/` | None | Implemented |

