# httpx Adapter Security Audit

**Date:** 2026-05-28  
**Auditor:** Security Engineer  
**Scope:** httpx outbound correlation-ID injection adapter (httpx_objects.py, httpx_client.py, constants/httpx.py)  
**Status:** COMPLETE

---

## Question 1: Header Injection via Context-Var Bypass

**Threat:** Can a malicious caller circumvent `HttpxCorrelation`'s inbound validation by directly setting the ContextVar via `set_correlation_id('bad\r\nInjected: header')`?

**Analysis:**

1. `HttpxCorrelation.__post_init__()` validates via `_is_safe()` only on direct construction.
2. `HttpxCorrelation.from_context()` calls `get_correlation_id()`, which reads the raw ContextVar value without re-validation, then calls `_is_safe()` before constructing the instance.
3. The ASGI inbound adapter (not in scope but relevant) validates headers on request-entry.
4. Hypothesis: A caller could call `set_correlation_id('bad\r\nvalue')` directly and bypass all checks, because `set_correlation_id` (alias for `ContextVarClient.set_id`) directly wraps the raw value in `CorrelationContext(value)` with NO validation.

**Test case:** Empirically verified in test suite at `test_httpx_objects.py:test_from_context_with_unsafe_chars_returns_none`, which demonstrates that `from_context()` re-validates and returns None on unsafe chars. The `set_correlation_id` call itself does NOT raise; only `from_context()` filters.

**Verdict:** NO ISSUE

**Reasoning:** Although `set_correlation_id` does not validate, `HttpxCorrelation.from_context()` re-validates the raw context value via `_is_safe()` before returning an instance. A caller who calls `set_correlation_id('bad\r\nvalue')` will not crash, but when the outbound adapter calls `from_context()`, it will receive None and inject no header. This is defense-in-depth: context-var bypasses the inbound guard, but the outbound adapter re-validates before trusting it.

---

## Question 2: Validate-and-Regenerate vs. Reject and Denial-of-Tracing

**Threat:** Outbound adapter silently drops unsafe correlation IDs (returns None) without regenerating a trace ID. Can an attacker pollute context with an unsafe value to suppress correlation propagation, creating a denial-of-tracing attack?

**Analysis:**

1. `from_context()` returns None if value is unsafe, OR if context is unset, OR if value is overlong.
2. `inject_sync()` returns early if `from_context()` is None, and the request is shipped without an X-Correlation-ID header.
3. Downstream service observes no header. Attacker's goal: break distributed tracing so investigation becomes hard.

**Severity assessment:**
- Blast radius: Single outbound call. Correlation is lost ONLY on that call. Upstream + downstream services unaffected (each maintains their own context).
- Detectability: Logs will show a correlation ID up to the point where the polluted value was set. The gap is visible as a "no correlation on next hop" in trace reconstruction.
- Practical cost to attacker: Must have code-execution access to call `set_correlation_id` directly. If attacker has that, they can already do worse (e.g., corrupt business logic, steal data).

**Verdict:** NO ISSUE

**Reasoning:** The design is acceptable for several reasons:
1. Regenerating a new trace ID silently would mask the attack and create a false appearance of continuity (worse for debugging).
2. The skip-on-unsafe pattern is documented in the test suite and is the explicit design choice.
3. An attacker capable of calling `set_correlation_id` has already breached the boundary where access-control should apply.
4. A single lost hop is observable and recoverable via alternative tracing (CloudWatch request ID, task ID, etc.).

---

## Question 3: Header Value Disclosure

**Threat:** Does outbound injection leak internal state into the X-Correlation-ID header value beyond what was already in context?

**Analysis:**

1. `header_tuple` property returns `(CORRELATION_ID_HEADER, self.correlation_id)`.
2. `self.correlation_id` is the exact value read from context via `from_context()`.
3. No additional processing, transformation, hashing, or metadata is added.
4. No side-channel opportunity: no timing-dependent logic, no branching on value content, no reflection or introspection of the value itself.

**Verdict:** NO ISSUE

**Reasoning:** The outbound injection is a pure passthrough. No additional state is leaked. The only information in the header is what was explicitly set by caller code, which presumably is already log-safe (since it was set intentionally).

---

## Question 4: AsyncClient Race Condition (ContextVar TOCTOU)

**Threat:** Is there a TOCTOU (time-of-check-time-of-use) window where the context-var changes between `from_context()` call and `request.headers` mutation?

**Analysis:**

1. Python's `contextvars` module uses context-local storage, NOT global state.
2. Each async task / thread has its own context snapshot.
3. Within a single task (synchronous execution of `inject_sync`), the context cannot change.
4. `from_context()` calls `get_correlation_id()`, which calls `correlation_ctx.get()`, a single atomic read.
5. The returned value is immediately validated and wrapped in an `HttpxCorrelation` instance.
6. The instance is immutable (frozen=True).
7. The header is written synchronously in the next line: `request.headers[name] = value`.

**Scenario check:** Even in async, the hook is called in the same context as the request preparation. Unless the caller explicitly awaits or yields between `from_context()` and header assignment, there is no context switch.

**Verdict:** NO ISSUE

**Reasoning:** Python's ContextVar semantics guarantee isolation per async task. Within a single call to `inject_sync` (synchronous, no await), the context is immutable. No TOCTOU window exists.

---

## Question 5: Length-Bound Bypass (Boundary Condition)

**Threat:** Could a value at exactly 128 characters bypass both length AND safety checks?

**Analysis:**

1. `_is_safe()` checks: `if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH: return False`
2. `CORRELATION_ID_MAX_LENGTH = 128`
3. `len(value) > 128` means 129+ is rejected. 128 is accepted.
4. The subsequent check iterates through every character: `return not any(char in UNSAFE_HEADER_CHARS for char in value)`

**Test case:** `test_httpx_objects.py:test_is_safe_with_overlong_returns_false` explicitly tests 129 chars (rejected). No test for exactly 128 chars, but the logic is clear: `>128` is the rejection threshold.

**Edge case check:** No logical flaw. A 128-character string with no CRLF/null chars will pass. That is intentional and safe.

**Verdict:** NO ISSUE

**Reasoning:** The boundary condition is correct: `> 128` (not `>= 128`) is the proper threshold. A 128-char string is accepted; 129+ is rejected. No bypass exists.

---

## Question 6: Event-Hook Composition Risk (Hook Ordering)

**Threat:** Docs say correlation hook fires before auth/signing hooks. Is ordering enforced or relies on caller discipline? What if a caller registers in wrong order?

**Analysis:**

1. `CorrelationIdInjector.event_hooks()` returns `{"request": [cls.inject_sync, cls.inject_async]}`.
2. This dict is passed to `httpx.Client(event_hooks=...)` or `AsyncClient(event_hooks=...)`.
3. httpx's event-hook model executes hooks in the order they appear in the list.
4. If a caller merges this dict with other hooks (e.g., auth hooks), the merge order depends on the caller's code.

**Example risky pattern:**
```python
hooks = {"request": [some_auth_hook]}
hooks["request"].extend(CorrelationIdInjector.event_hooks()["request"])
```
This would execute auth first, then correlation. Signing hooks that freeze the headers would prevent correlation injection.

**Conversely, safe pattern:**
```python
hooks = CorrelationIdInjector.event_hooks()
hooks["request"].extend([some_auth_hook])
```
This executes correlation first, then auth (correct order).

**Current adapter responsibility:** The adapter itself does NOT enforce ordering. It documents the expected order in the return dict or docstring. The burden is on the caller to merge hooks correctly.

**Verdict:** NEEDS REVIEW

**Severity:** MEDIUM (design-time issue, not runtime vulnerability, but impacts usability).

**Recommended fix:**

1. Add a docstring to `event_hooks()` clarifying that the returned hooks MUST be registered before any auth/signing hooks.
2. Consider a helper that merges a caller's hooks list with correlation hooks in the correct order:
   ```python
   @classmethod
   def merge_with_caller_hooks(cls, caller_hooks: objs.EventHooks) -> objs.EventHooks:
       """Merge caller's request hooks with correlation hooks, preserving order."""
       merged = cls.event_hooks()
       if "request" in caller_hooks:
           merged["request"].extend(caller_hooks["request"])
       return merged
   ```
3. Add an integration test that verifies correlation hook fires before a mock signing hook.

---

## Question 7: Information Leak via Empty Correlation (Fingerprinting Risk)

**Threat:** When context is empty, `inject_sync` returns None silently and omits the header. Could a downstream service distinguish 'no correlation set' from 'correlation was filtered', enabling fingerprinting?

**Analysis:**

1. Downstream service receives a request with no X-Correlation-ID header.
2. Service logs show: "request arrived with no correlation ID".
3. Service cannot distinguish:
   - Upstream never set a correlation ID (expected for some clients).
   - Upstream filtered the correlation ID due to unsafe chars (deliberate defense).
   - Upstream lost the correlation ID due to a bug.

**Fingerprinting vector:** An attacker in a downstream service could infer "upstream must be filtering" if the absence of correlation is statistically anomalous. This is weak intelligence (does not leak data), but it does leak metadata about upstream filtering behavior.

**Practical impact:** Extremely low. Legitimate clients without correlation IDs are common. A single filtered request is not statistically distinguishable. Attacker would need to observe a pattern across many requests, which requires persistent upstream access.

**Verdict:** NO ISSUE

**Reasoning:** The fingerprinting risk is negligible in practice. The information leaked (existence of filtering) is not sensitive. Standard defensive posture is to expect missing headers as normal. No change needed.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. Header injection via context-var bypass | NO ISSUE | N/A | None |
| 2. Validate-and-regenerate vs. reject | NO ISSUE | N/A | None |
| 3. Header value disclosure | NO ISSUE | N/A | None |
| 4. AsyncClient race condition | NO ISSUE | N/A | None |
| 5. Length-bound bypass | NO ISSUE | N/A | None |
| 6. Event-hook ordering | NEEDS REVIEW | MEDIUM | Add docstring + optional merge helper |
| 7. Empty correlation fingerprinting | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS WITH DOCUMENTATION IMPROVEMENT**

The httpx outbound adapter is secure against header injection, race conditions, and denial-of-tracing attacks. The design correctly re-validates context-var values before use and rejects unsafe characters with no information leakage.

The sole item requiring attention is hook ordering: the current implementation delegates responsibility to the caller but does not provide strong guardrails. Adding a docstring that explicitly documents the required hook order (correlation before auth/signing) and optionally a helper method for safe hook merging would improve usability and reduce risk of misconfiguration.

---

## Recommended Actions

1. **Immediate (documentation):** Add a docstring to `CorrelationIdInjector.event_hooks()` clarifying:
   - Returned hooks MUST be registered before auth/signing hooks.
   - Example: "These hooks must fire before request signing hooks, as signing freezes headers."

2. **Near-term (optional enhancement):** Implement a `merge_with_caller_hooks` class method to assist callers in merging hooks safely.

3. **Testing:** Add an integration test verifying correlation hook fires before a mock signing hook that freezes headers.

---

## Audit Conclusion

No security blockers identified. The adapter is safe for production use. Recommended documentation improvements are non-blocking enhancements to caller ergonomics.
