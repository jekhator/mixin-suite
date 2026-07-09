# Aiohttp Adapter Security Audit

**Date:** 2026-06-19  
**Auditor:** Security Engineer  
**Scope:** aiohttp outbound correlation-ID injection adapter (aiohttp_objects.py, aiohttp_client.py, constants/aiohttp.py)  
**Status:** COMPLETE

---

## Question 1: TraceConfig Hook Lifecycle and Timing

**Threat:** The `on_request_start` hook fires at a specific point in aiohttp's request lifecycle. If it fires after headers are frozen or before all required headers are set, injection could be bypassed or overwritten.

**Analysis:**

1. Line 18 (aiohttp_client.py): `config.on_request_start.append(cls._inject)` registers the hook.
2. `on_request_start` is fired by aiohttp AFTER request object creation but BEFORE transmission (per aiohttp documentation).
3. Line 32 (aiohttp_client.py): `params.headers[name] = value` modifies the headers dict directly.
4. The `TraceRequestStartParams.headers` object is a mutable dict until transmission, not frozen.
5. Aiohttp's execution order: session.get() → request prep → **on_request_start fires** → connection → send.

**Verdict:** NO ISSUE

**Reasoning:** The hook fires at the correct injection point, before headers are transmitted but after request initialization. The headers dict is mutable at this stage. No race conditions or freezing issues.

---

## Question 2: Context-Var Read and Re-Validation at Injection Point

**Threat:** Can the correlation ID from context be injected with CRLF/null characters, or is it re-validated at the injection point?

**Analysis:**

1. Line 29 (aiohttp_client.py): `correlation = objs.AiohttpCorrelation.from_context()`
2. `from_context()` (aiohttp_objects.py, lines 26-31) calls `_is_safe(raw_value)` before constructing the instance.
3. If unsafe, `from_context()` returns None (line 30).
4. Line 30-31 (aiohttp_client.py): Early return if correlation is None.
5. `_is_safe()` (aiohttp_objects.py, lines 39-43) checks: `if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH: return False` and `return not any(char in const.UNSAFE_HEADER_CHARS for char in value)`.
6. `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})` (constants/aiohttp.py, line 27).

**Verdict:** NO ISSUE

**Reasoning:** The validation is re-applied at the outbound injection point. Even if context was polluted with unsafe chars, the adapter filters them via `from_context()`. No header injection is possible.

---

## Question 3: TraceConfig Multiplexing and State Leakage

**Threat:** If multiple TraceConfig instances are created and attached to different sessions, could context values leak across sessions?

**Analysis:**

1. Line 16-20 (aiohttp_client.py): `trace_config()` creates a NEW `aiohttp.TraceConfig()` instance each time.
2. Each TraceConfig is independent; no shared state is stored on the config object.
3. The `_inject` method (lines 23-33) reads from the global ContextVar `get_correlation_id()`, not from the TraceConfig.
4. The ContextVar is task-local (in async) or thread-local (in sync), not session-local.
5. If two ClientSessions fire requests in the same async task, both will read the same correlation ID from context (correct behavior for tracing).

**Expected behavior:** Both sessions should inject the same correlation ID within the same task. This is intentional for end-to-end tracing.

**Verdict:** NO ISSUE

**Reasoning:** Context-local storage is intentional. Multiple TraceConfigs in the same task should all read the same correlation ID. No leakage issue; correct isolation per task.

---

## Question 4: Async Hook Signature Compliance

**Threat:** The `_inject` method is declared `async` and receives `(session, trace_config_ctx, params)`. Does it match aiohttp's on_request_start hook signature?

**Analysis:**

1. Lines 22-33 (aiohttp_client.py): `_inject` is declared `async def` with signature `(session: aiohttp.ClientSession, trace_config_ctx: object, params: aiohttp.TraceRequestStartParams) -> None`.
2. Aiohttp's `on_request_start` hooks expect: `async def hook(session, trace_config_ctx, params) -> None`.
3. The return type is `None` (line 27): correct, no return value expected.
4. The method is decorated `@staticmethod` (line 22): correct, no instance state needed.

**Verdict:** NO ISSUE

**Reasoning:** The async signature matches aiohttp's hook contract exactly. No type mismatches or protocol violations.

---

## Question 5: Exception Handling in the Injection Hook

**Threat:** If `_inject` raises an exception (e.g., due to a malformed TraceRequestStartParams), could it crash the request or bypass tracing silently?

**Analysis:**

1. Lines 29-33 (aiohttp_client.py): The method reads from context and injects the header.
2. No explicit error handling (try/except) is present.
3. Potential exceptions:
   - `from_context()` never raises (line 26-31 in aiohttp_objects.py handles all cases gracefully).
   - `correlation.header_tuple` (line 32) is a `@property` returning a tuple (aiohttp_objects.py, lines 34-36): never raises.
   - `params.headers[name] = value` (line 33): Could raise if headers is immutable or if session is in an unexpected state.
4. If params.headers is unexpectedly immutable, the header injection fails silently (AttributeError or TypeError) and the request proceeds without correlation ID.

**Severity:** Low. An unmapped exception would bubble to aiohttp's trace handler, which logs it but does not crash the request (aiohttp's trace system is designed for non-fatal monitoring).

**Verdict:** NO ISSUE (acceptable risk)

**Reasoning:** `from_context()` and `header_tuple` are guaranteed to not raise. The only risk is a malformed params object, which is an aiohttp internal error. If it occurs, the trace system logs it; the request continues without correlation ID. This is acceptable for a monitoring hook. Adding explicit try/except would mask aiohttp bugs.

---

## Question 6: Aiohttp Library Version Compatibility

**Threat:** Could changes in aiohttp's TraceConfig or on_request_start API break the adapter?

**Analysis:**

1. Line 18 (aiohttp_client.py): `config.on_request_start.append(cls._inject)` relies on TraceConfig's public list interface.
2. Line 23-33: The hook signature uses aiohttp's public types: `aiohttp.ClientSession`, `aiohttp.TraceRequestStartParams`.
3. Lines 32: `params.headers[name] = value` relies on TraceRequestStartParams.headers being dict-like.
4. Aiohttp has maintained stable TraceConfig and on_request_start APIs across versions 3.0+.
5. No use of internal methods (_on_request_start, __trace_config, etc.) or undocumented attributes.

**Verdict:** NO ISSUE

**Reasoning:** The adapter uses only public, stable APIs of aiohttp. Compatible with aiohttp 3.0+. No version-specific hacks.

---

## Question 7: Denial-of-Tracing via Unsafe Context Pollution

**Threat:** If a caller sets an unsafe correlation ID in context, could they suppress correlation propagation across all requests in the session?

**Analysis:**

1. Lines 29-31 (aiohttp_client.py): If `from_context()` returns None (due to unsafe value), the early return skips injection.
2. The request is sent without an X-Correlation-ID header.
3. Downstream services observe no correlation.

**Severity:** Low. Only a caller with code-execution access can call `set_correlation_id()`. If they have that, they can already do worse (modify payloads, redirect requests, etc.).

**Verdict:** NO ISSUE

**Reasoning:** Consistent with requests and httpx. The skip-on-unsafe pattern is acceptable when the threat actor must already have code execution. A single lost request is observable in logs.

---

## Question 8: Header Value Disclosure and Passthrough

**Threat:** Does the adapter leak internal state by injecting the correlation ID as-is, or does it transform/hash the value?

**Analysis:**

1. Line 32 (aiohttp_client.py): `name, value = correlation.header_tuple` returns `(const.CORRELATION_ID_HEADER, self.correlation_id)` (aiohttp_objects.py, lines 34-36).
2. `self.correlation_id` is the exact value read from context.
3. Line 33: `params.headers[name] = value` injects the exact value.
4. No transformation, hashing, or masking is applied.

**Implication:** The outbound header is a faithful copy of the context value. Correlation IDs are typically non-sensitive trace identifiers (UUIDs, request IDs, trace-context values), not secrets.

**Verdict:** NO ISSUE

**Reasoning:** Correlation IDs are non-sensitive metadata intended for tracing. No masking or transformation is needed. This is correct design.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. TraceConfig hook lifecycle and timing | NO ISSUE | N/A | None |
| 2. Context-var read and validation | NO ISSUE | N/A | None |
| 3. TraceConfig multiplexing and state leakage | NO ISSUE | N/A | None |
| 4. Async hook signature compliance | NO ISSUE | N/A | None |
| 5. Exception handling in injection hook | NO ISSUE | LOW | None (acceptable risk) |
| 6. Aiohttp library version compatibility | NO ISSUE | N/A | None |
| 7. Denial-of-tracing via unsafe context pollution | NO ISSUE | N/A | None |
| 8. Header value disclosure and passthrough | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS**

The aiohttp outbound adapter is secure against header injection, authentication bypass, and tracing suppression attacks. The design correctly validates context values before injection, hooks at the correct lifecycle point, and uses only stable, public APIs of the aiohttp library.

---

## Recommended Actions

No mandatory actions. The adapter is production-ready. The following are optional enhancements:

1. **Optional docstring expansion in `_inject`:** Add a clarifying comment explaining that early return on unset/unsafe context is intentional (no-op tracing when context is absent or invalid). Example:

   ```python
   async def _inject(
       session: aiohttp.ClientSession,
       trace_config_ctx: object,
       params: aiohttp.TraceRequestStartParams,
   ) -> None:
       """Inject X-Correlation-ID header into outbound request when context is populated.
       
       If context is unset or contains unsafe characters, this method returns early
       without modifying headers (silent no-op tracing).
       """
   ```

2. **Optional integration test:** Add a test verifying that correlation injection works with redirects (aiohttp follows redirects automatically and fires on_request_start for each). This is already covered in the test suite implicitly via parametrized hook tests.

---

## Audit Conclusion

No security blockers. The adapter is safe for production use.
