# GraphQL Adapter Security Audit

**Date:** 2026-06-19  
**Auditor:** Security Engineer  
**Scope:** GraphQL inbound correlation-ID exposure adapter (graphql_objects.py, graphql_client.py, constants/graphql.py)  
**Status:** COMPLETE

---

## Question 1: Context Var Read Without Downstream Validation

**Threat:** Can the correlation ID read from context be injected into the resolver dict with CRLF/null characters that downstream code might fail to handle safely?

**Analysis:**

1. Line 21-23 (graphql_objects.py): `from_context()` reads via `get_correlation_id()` and returns a new instance with the value as-is.
2. Line 25-27 (graphql_objects.py): `as_context_dict()` returns `{const.CONTEXT_KEY: self.correlation_id}` with no transformation.
3. Line 16-19 (graphql_client.py): `inject()` calls `GraphQLCorrelation.from_context()` and merges the result dict directly.
4. The value is read from the global ContextVar, which is set upstream by ASGI/WSGI middleware.
5. ASGI/WSGI middleware (asgi_objects.py, wsgi_objects.py) both validate via `_is_safe()` before setting context.

**Verdict:** NO ISSUE

**Reasoning:** The GraphQL adapter does not extract headers; it reads from a ContextVar set and validated by upstream ASGI/WSGI middleware. By design, the correlation ID in context is already validated (CRLF/null checked, length-bounded) before this adapter touches it. No re-validation is needed. The adapter correctly assumes the context is clean.

---

## Question 2: Dict Merge Mutability and Context Leakage

**Threat:** Does the `inject()` method mutate the input context dict, or could it leak internal state if the resolver modifies the returned dict?

**Analysis:**

1. Line 16-19 (graphql_client.py): `inject(context)` uses dict unpacking `{**context, **correlation.as_context_dict()}`.
2. This creates a NEW dict; the input context is not mutated.
3. Line 16-17 (test_graphql_client.py): Test `test_inject_returns_new_dict` confirms input is not mutated (assertion `context == original_context` and `result is not context`).
4. If a resolver later modifies the returned dict, the mutation does not affect the global ContextVar.

**Verdict:** NO ISSUE

**Reasoning:** The dict merge is immutable (unpacking creates a new dict). The returned dict is independent of the input and does not share references with the context-var storage. No leakage or mutation risk.

---

## Question 3: Context Key Collision

**Threat:** Could the hard-coded context key `"correlation_id"` collide with application-specific context keys, causing a resolver to receive the wrong value?

**Analysis:**

1. Line 14 (constants/graphql.py): `CONTEXT_KEY = "correlation_id"`.
2. Line 27 (graphql_objects.py): Used directly in `as_context_dict()`.
3. The key is intentionally named and documented to avoid collisions.
4. GraphQL frameworks typically document the reserved keys in their context dicts (e.g., Strawberry reserves `context`, `field_name`, `operation_name`).
5. The name `"correlation_id"` is standard for correlation tracing and is unlikely to collide with application logic.

**Implication:** The adapter assumes the application reserves the key `"correlation_id"` for this purpose. If an application already uses `"correlation_id"` for a different purpose, the merge will overwrite it.

**Verdict:** NO ISSUE

**Reasoning:** Key collision is an application-configuration concern, not a security flaw. Frameworks should document reserved keys. The name `"correlation_id"` follows standard naming conventions. Overwriting is explicitly a design choice (the adapter is meant to inject this key). No insecure behavior.

---

## Question 4: None Value Propagation to Resolvers

**Threat:** If correlation ID is unset in context, the adapter injects `None`. Could resolvers expecting a string crash or behave incorrectly?

**Analysis:**

1. Line 18 (graphql_objects.py): `correlation_id: str | None` allows `None`.
2. Line 23 (graphql_objects.py): `from_context()` returns an instance with `correlation_id=None` if unset.
3. Line 27 (graphql_objects.py): `as_context_dict()` always returns a dict with the key; value is `None` or a string.
4. Line 28 (test_graphql_objects.py): Test `test_as_context_dict_with_unset_correlation_returns_dict_with_none` confirms `{const.CONTEXT_KEY: None}` is returned.
5. Resolvers receive `context["correlation_id"]` as `None` or a string.

**Implication:** Resolvers that assume `correlation_id` is always a string must handle `None`. This is by design: if no correlation ID is set, the resolver should gracefully handle the absence.

**Verdict:** NO ISSUE

**Reasoning:** The type annotation `str | None` is explicit. Resolvers must handle both cases (standard defensive coding). This is correct behavior: correlation ID is optional metadata, not a required field.

---

## Question 5: ContextVar Scope and Thread/Task Isolation

**Threat:** If two GraphQL requests run concurrently (e.g., in async), could they read each other's correlation IDs?

**Analysis:**

1. Line 8 (graphql_objects.py): `get_correlation_id()` reads from the global ContextVar.
2. ContextVar is task-local (async) or thread-local (sync), not request-local.
3. Each concurrent request in an async framework (FastAPI, Strawberry) runs in its own asyncio task.
4. Each task has an isolated ContextVar store (AsyncContextVar semantics in Python 3.7+).
5. Two concurrent requests each call `inject()` and each reads its own ContextVar value (no cross-talk).

**Verdict:** NO ISSUE

**Reasoning:** ContextVar provides task-level isolation in async, thread-level isolation in sync. Two concurrent requests cannot read each other's correlation IDs. This is correct.

---

## Question 6: Unset Context Denial of Tracing

**Threat:** If an application fails to set correlation ID upstream (e.g., ASGI middleware not installed), does the adapter silently inject `None` and mask the problem?

**Analysis:**

1. Line 21 (graphql_objects.py): `from_context()` calls `get_correlation_id()`, which returns `None` if unset.
2. No exception is raised; no warning is logged.
3. Line 28-29 (test_graphql_client.py): Test `test_inject_without_context_merges_none_correlation` confirms `inject()` returns `{const.CONTEXT_KEY: None}`.
4. Resolvers receive `None` silently; they may not log it or propagate it downstream.

**Implication:** If upstream middleware fails to set correlation ID, the adapter does not alert. A resolver might log `None` or use a fallback without realizing tracing is incomplete.

**Severity:** Low. The adapter is a **context-injection surface**, not a correlation-extraction surface. Extraction and validation happen in ASGI/WSGI adapters (which will fail loudly or generate a UUID if needed). If the ContextVar is unset, it's upstream's job to set it; the GraphQL adapter only exposes what's there.

**Verdict:** NO ISSUE

**Reasoning:** Consistent with httpx/requests/botocore outbound adapters: silent pass-through of unset values. The assumption is that correlation ID is set upstream by ASGI/WSGI middleware; if it's not set, that's an upstream configuration error. The GraphQL adapter is not responsible for detecting it. Resolvers and downstream code are responsible for handling `None` gracefully.

---

## Question 7: Type Annotation and Cast Safety

**Threat:** The `as_context_dict()` return type is `dict[str, str | None]`, but the input context is `dict[str, Any]` (line 16, graphql_client.py). Could a type mismatch cause runtime issues?

**Analysis:**

1. Line 25-27 (graphql_objects.py): `as_context_dict()` returns `dict[str, str | None]`.
2. Line 16 (graphql_client.py): `inject(context: dict[str, Any]) -> dict[str, Any]`.
3. The merge `{**context, **correlation.as_context_dict()}` combines two dicts: one with `str | Any` values, one with `str | (str | None)` values.
4. The returned dict is annotated as `dict[str, Any]`, which is correct (union of `Any` and `str | None` is still `Any`).
5. No cast or narrow is needed; the type is sound.

**Verdict:** NO ISSUE

**Reasoning:** Type annotations are correct. The wider `dict[str, Any]` return type on `inject()` correctly reflects that the input may contain arbitrary values. No casting or runtime type error.

---

## Question 8: Staticmethod and Statelessness

**Threat:** The `inject()` method is a `@staticmethod`. Could stateless design hide shared state or dependencies?

**Analysis:**

1. Line 15-16 (graphql_client.py): `@staticmethod def inject(...)` has no reference to `self` or class state.
2. Line 18 (graphql_client.py): Creates a local `correlation` object.
3. Line 19 (graphql_client.py): Merges and returns a new dict.
4. No global variables or singletons are mutated.
5. The class `CorrelationContextInjector` has no `__init__` or fields.

**Verdict:** NO ISSUE

**Reasoning:** Staticmethod is appropriate. The operation is pure: same input always produces the same output (given the same ContextVar state). No hidden state or side effects. Correct design.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. Context Var read without downstream validation | NO ISSUE | N/A | None |
| 2. Dict merge mutability and context leakage | NO ISSUE | N/A | None |
| 3. Context key collision | NO ISSUE | N/A | None |
| 4. None value propagation to resolvers | NO ISSUE | N/A | None |
| 5. ContextVar scope and thread/task isolation | NO ISSUE | N/A | None |
| 6. Unset context denial of tracing | NO ISSUE | N/A | None |
| 7. Type annotation and cast safety | NO ISSUE | N/A | None |
| 8. Staticmethod and statelessness | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS**

The GraphQL adapter is secure for production use. The design correctly assumes correlation ID is already validated upstream by ASGI/WSGI middleware and safely exposes it to resolver code via context injection. No injection, mutation, leakage, or type-safety issues detected. The adapter is a thin, stateless wrapper over ContextVar access.

---

## Recommended Actions

No mandatory changes. The code is production-ready as-is.

**Optional documentation note:** Resolvers should be documented to expect `context.get("correlation_id")` to return `str | None` and handle the `None` case gracefully (e.g., log a fallback identifier or warn).

---

## Audit Conclusion

No security blockers. The adapter is safe and ready for release.
