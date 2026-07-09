# Requests Adapter Security Audit

**Date:** 2026-06-04  
**Auditor:** Security Engineer  
**Scope:** requests outbound correlation-ID injection adapter (requests_objects.py, requests_client.py, constants/requests.py)  
**Status:** COMPLETE

---

## Question 1: HTTPAdapter Mounting and Hook Precedence

**Threat:** HTTPAdapter.add_headers() is called during request preparation. Does it fire before or after other hooks that might freeze headers (e.g., authentication)?

**Analysis:**

1. `CorrelationHTTPAdapter` extends `requests.adapters.HTTPAdapter`.
2. Line 16: `def add_headers(self, request: Any, **kwargs: Any) -> None:` overrides the HTTPAdapter method.
3. Line 18: `super().add_headers(request, **kwargs)` calls the parent class method first.
4. Line 19-23: Then injects the correlation ID.
5. Requests' request preparation flow: method normalization → URL parsing → prepare_auth → **prepare_headers** (add_headers fires here) → prepare body → prepare cookies → finalize headers.
6. Authentication hooks typically run during prepare_auth, which is BEFORE add_headers.

**Critical finding:** The parent `HTTPAdapter.add_headers()` is called first (line 18). If the parent method freezes headers (unlikely in standard httpx, but possible in custom adapters), the child injection would fail.

**Verdict:** ⚠️ NEEDS REVIEW

**Analysis:** The requests library's standard HTTPAdapter does NOT freeze headers in add_headers(); it only adds default headers (User-Agent, etc.). However, a subclass could override this behavior. The call to `super().add_headers()` is safe for the standard library, but documentation should clarify the order of execution.

**Recommended improvement:** Add a docstring to `add_headers()` clarifying that this method fires during request preparation, after auth hooks but before final header finalization. Consider documenting the call order or providing an example of safe integration.

---

## Question 2: Context-Var Read and Validation

**Threat:** Can the correlation ID from context be injected with CRLF/null characters, or is it re-validated?

**Analysis:**

1. Line 19: `correlation = objs.RequestsCorrelation.from_context()`
2. `from_context()` (requests_objects.py line 24-29) calls `_is_safe(raw_value)` before constructing the instance.
3. If unsafe, `from_context()` returns None (line 28).
4. Line 20-21: Early return if correlation is None.
5. `_is_safe()` checks: `if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH: return False` (line 39).
6. `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})` (from constants).

**Verdict:** NO ISSUE

**Reasoning:** The validation is re-applied at the outbound point. Even if context was polluted with unsafe chars, the adapter filters them. No injection is possible.

---

## Question 3: HTTPAdapter Lifecycle and Mounting

**Threat:** If an HTTPAdapter is mounted on a session and then removed or replaced, could residual state cause issues?

**Analysis:**

1. Line 26-29: `register_on_session()` mounts the adapter on a session.
2. Requests' session mounting is simple: `session.mount("http://", adapter)` stores the adapter in a dict.
3. If an adapter is unmounted (replaced with another), the old adapter is garbage-collected.
4. The CorrelationHTTPAdapter has no instance state (frozen=False, no __init__ override), so removal is clean.

**Verdict:** NO ISSUE

**Reasoning:** Requests' adapter lifecycle is straightforward. No residual state is left behind on unmount. The adapter is stateless.

---

## Question 4: Session-Level Mounting Isolation

**Threat:** If two sessions both mount the CorrelationHTTPAdapter, could context corruption occur between sessions?

**Analysis:**

1. Each call to `register_on_session(session)` creates a new instance: `session.mount("http://", cls())` (line 28-29).
2. Each instance is independent (no shared state due to frozen=True).
3. Both instances read from the same global ContextVar (`get_correlation_id()`).
4. The ContextVar is task-local (in async) or thread-local (in sync), not session-local.
5. If two sessions fire requests in the same task/thread, both will read the same correlation ID from context.

**Expected behavior:** Correct. Correlation ID should propagate across all outbound requests within the same task/thread.

**Verdict:** NO ISSUE

**Reasoning:** Context-local storage is intentional. Multiple adapters in the same task/thread should all read the same correlation ID. No isolation issue.

---

## Question 5: Header Value Disclosure (Passthrough Risk)

**Threat:** Does the adapter leak internal state by injecting the correlation ID as-is, or does it transform/hash the value?

**Analysis:**

1. Line 22: `name, value = correlation.header_tuple` returns `(const.CORRELATION_ID_HEADER, self.correlation_id)`.
2. `self.correlation_id` is the exact value read from context.
3. Line 23: `request.headers[name] = value` injects the exact value.
4. No transformation, hashing, or masking is applied.

**Implication:** The outbound header is a faithful copy of the context value. If the context value is meant to be sensitive, the adapter does not mask it. However, correlation IDs are typically non-sensitive trace identifiers (UUIDs, trace-context-propagation values), not secrets.

**Verdict:** NO ISSUE

**Reasoning:** Correlation IDs are non-sensitive metadata intended for tracing. No masking or transformation is needed. This is correct design.

---

## Question 6: Requests Library Version Compatibility

**Threat:** Could changes in requests library (header dict interface, adapter API) break the adapter?

**Analysis:**

1. Line 18: `super().add_headers(request, **kwargs)` relies on HTTPAdapter's public interface.
2. Line 23: `request.headers[name] = value` relies on the Request object's headers being dict-like.
3. Requests library has maintained stable APIs for these features across versions 2.0+.
4. No use of internal methods or undocumented attributes.

**Verdict:** NO ISSUE

**Reasoning:** The adapter uses only public, stable APIs of the requests library. No version-specific hacks. Compatible with requests 2.0+.

---

## Question 7: Deny-of-Tracing via Unsafe Context Pollution

**Threat:** If a caller sets an unsafe correlation ID in context, could they suppress correlation propagation across all requests in the session?

**Analysis:**

1. Line 19-21: If `from_context()` returns None (due to unsafe value), the early return skips injection.
2. The request is sent without an X-Correlation-ID header.
3. Downstream services observe no correlation.

**Severity:** Low. Only a caller with code-execution access can call `set_correlation_id()`. If they have that, they can already do worse.

**Verdict:** NO ISSUE

**Reasoning:** Consistent with httpx and botocore. The skip-on-unsafe pattern is acceptable when the threat actor must already have code execution. A single lost request is observable.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. HTTPAdapter mounting and hook precedence | NEEDS REVIEW | LOW | Add docstring clarifying hook order |
| 2. Context-var read and validation | NO ISSUE | N/A | None |
| 3. HTTPAdapter lifecycle and mounting | NO ISSUE | N/A | None |
| 4. Session-level mounting isolation | NO ISSUE | N/A | None |
| 5. Header value disclosure (passthrough) | NO ISSUE | N/A | None |
| 6. Requests library version compatibility | NO ISSUE | N/A | None |
| 7. Deny-of-tracing via unsafe context pollution | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS WITH DOCUMENTATION IMPROVEMENT**

The requests outbound adapter is secure against header injection, authentication bypass, and tracing suppression attacks. The design correctly validates context values before injection and uses only stable, public APIs of the requests library.

The sole item requiring attention is documentation: a docstring clarifying that `add_headers()` fires after authentication hooks but before final header finalization would improve clarity for callers integrating the adapter into complex request pipelines.

---

## Recommended Actions

1. **Add docstring to `add_headers()`:** Clarify the hook ordering and document that this method is called during request preparation after `prepare_auth()` but before final header transmission. Example:

   ```python
   def add_headers(self, request: Any, **kwargs: Any) -> None:
       """Inject X-Correlation-ID after parent headers, before transmission.
       
       This method fires during request preparation after authentication
       hooks but before final headers are sent. The parent HTTPAdapter
       method is called first, then correlation ID is injected.
       """
   ```

2. **Optional:** Add an integration test verifying that correlation injection works correctly with requests.auth.HTTPBasicAuth or similar auth hooks.

---

## Audit Conclusion

No security blockers. The adapter is safe for production use. The recommended docstring improvement is a non-blocking enhancement for caller clarity.
