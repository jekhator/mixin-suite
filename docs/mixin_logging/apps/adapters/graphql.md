# logging-mixin. GraphQL Adapter

> **Location:** `logging-mixin/docs/apps/adapters/graphql.md`
> **Status:** Implemented. Inbound correlation-ID extraction and resolver context injection for GraphQL APIs.
> **Code location:** `mixin_logging/adapters/graphql/` (`graphql_objects.py` + `graphql_client.py`); constants in `mixin_logging/adapters/constants/graphql.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Adapter Categories & Data Flow).
> **Sibling docs:** `docs/apps/adapters/asgi.md`, `docs/apps/adapters/wsgi.md`, `docs/apps/context/correlation.md`.

## Purpose

Expose the current correlation ID from context to GraphQL resolvers so query handlers can access the trace identifier and propagate it into logs, downstream calls, and audit records.

## Category

Inbound/Context Injection, specialized for GraphQL resolver context. Unlike ASGI/WSGI which extract and set correlation ID at the middleware boundary, this adapter assumes correlation ID is already set upstream (by ASGI or WSGI middleware) and exposes it to resolver code via a context object.

## Behavior

- `CorrelationContextInjector.inject(context)` reads the current correlation ID from the `ContextVar` (set upstream by ASGI/WSGI middleware) and merges it into a GraphQL resolver context dict.
- The method returns a new dict without mutating the input.
- The correlation ID is accessed via `GraphQLCorrelation.from_context()`, which reads directly from the ContextVar and returns `None` if unset (no raise).
- The injection point is designed for use in GraphQL middleware or context factories that run before resolver execution (e.g., in FastAPI `context=` parameter or Graphene/Strawberry context setup).

## Value Object

`GraphQLCorrelation` (frozen, slots) captures the `correlation_id` for resolver injection:

- `from_context()`. Read the ContextVar (set upstream by ASGI/WSGI); returns a new instance with `correlation_id` set or `None`.
- `as_context_dict()`. Returns a dict `{CONTEXT_KEY: correlation_id}` suitable for merging into resolver context.

## Constants

`mixin_logging/adapters/constants/graphql.py`:

- `CONTEXT_KEY = "correlation_id"` (the resolver context dict key under which correlation_id is exposed)

## Design Note

The GraphQL adapter does not extract correlation ID from headers or generate missing IDs. Instead, it assumes correlation ID is already managed by upstream ASGI/WSGI middleware and merely exposes the current value from context to resolver code. This separation of concerns keeps the adapter lightweight and avoids duplication of validation or generation logic. Resolvers can read the correlation ID from `context["correlation_id"]` and include it in logs, audit records, or propagate it to downstream services.

## Compatibility

Any Python GraphQL framework with a context dict: FastAPI with Strawberry or Graphene, Starlette-based GraphQL servers, Django GraphQL, or custom ASGI/WSGI applications. No extra dependencies required.

## Example Usage

### FastAPI + Strawberry

```python
import strawberry
from fastapi import FastAPI
from mixin_logging.adapters.graphql import CorrelationContextInjector

@strawberry.type
class Query:
    @strawberry.field
    def hello(self, info: strawberry.types.Info) -> str:
        correlation_id = info.context.get("correlation_id")
        return f"Hello (trace: {correlation_id})"

app = FastAPI()

@app.get("/graphql", ...)
async def graphql_endpoint(request: Request):
    context = await get_base_context()
    context = CorrelationContextInjector.inject(context)
    # Now context["correlation_id"] is set
    # Pass context to your GraphQL server
```

### Django Graphene

```python
from graphene import ObjectType, String, Schema
from mixin_logging.adapters.graphql import CorrelationContextInjector

class Query(ObjectType):
    hello = String()

    def resolve_hello(self, info):
        correlation_id = info.context.get("correlation_id")
        return f"Hello (trace: {correlation_id})"

schema = Schema(query=Query)

# In your Django view:
def graphql_view(request):
    context = {"user": request.user, ...}
    context = CorrelationContextInjector.inject(context)
    # Now context["correlation_id"] is set
    result = schema.execute(query_string, context_value=context)
    return JsonResponse(result.data)
```

## See Also

- **Inbound middleware (extract + set):** `docs/apps/adapters/asgi.md`, `docs/apps/adapters/wsgi.md`
- **Outbound propagation:** `docs/apps/adapters/httpx.md`, `docs/apps/adapters/requests.md`
- **Correlation Context:** `docs/apps/context/correlation.md`
- **Diagram:** `docs/apps/adapters/diagrams.md`
