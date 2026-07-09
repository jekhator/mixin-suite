# WebSocket Adapter Security Audit

**Date:** 2026-06-19  
**Auditor:** Security Engineer  
**Scope:** WebSocket inbound correlation-ID extraction adapter (websocket_objects.py, websocket_client.py, constants/websocket.py)  
**Status:** COMPLETE

---

## Question 1: Header Extraction and Byte-Pair Iteration

**Threat:** The adapter iterates over ASGI scope["headers"] (list of (bytes, bytes) pairs). Could an attacker craft malformed headers to cause parsing failure, infinite loops, or memory exhaustion?

**Analysis:**

1. `websocket_objects.py` line 32-36: `from_headers()` uses a simple generator expression:
   ```python
   candidate = next(
       (value for key, value in headers if key.lower() == target),
       None,
   )
   ```
2. The iteration is linear over the headers list provided by the ASGI server (Starlette, etc.).
3. The ASGI server validates and parses headers before passing to middleware; the adapter receives already-valid (bytes, bytes) tuples.
4. No unbounded loops, no dynamic allocation based on header count.
5. The `.lower()` call on the key is a safe bytes operation (O(len(key))).

**Verdict:** NO ISSUE

**Reasoning:** The adapter trusts the ASGI server to provide well-formed headers. No parsing of the raw HTTP stream occurs in the adapter: parsing happens in the server (Starlette, FastAPI, etc.). The adapter iterates once over the list and stops at the first match via `next()`. No attack surface.

---

## Question 2: Header Value Decoding and Character Validation

**Threat:** Line 38 uses `.decode(errors="ignore")`. Could this mask injected control characters or create log-injection vulnerabilities?

**Analysis:**

1. `websocket_objects.py` line 38: `decoded = candidate.decode(errors="ignore")`
2. `errors="ignore"` silently drops invalid UTF-8 bytes rather than raising an exception.
3. This is followed immediately by `_is_safe()` validation (line 39), which checks:
   - Line 49-51: `if not any(char in const.UNSAFE_HEADER_CHARS for char in value)`
   - `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})` (constants/websocket.py line 25)
4. The validation happens AFTER decoding but BEFORE the ID is accepted.
5. If decoding drops bytes and produces a string with CR/LF/null, `_is_safe()` catches it.
6. If decoding produces a valid string without unsafe chars, it is accepted.

**Severity:** Potential log-injection if unsafe chars pass validation.

**Verdict:** NO ISSUE

**Reasoning:** The `errors="ignore"` approach is safe because it avoids raising an exception on invalid UTF-8 (which could be a DoS vector). The resulting decoded string is then validated by `_is_safe()` to reject CR/LF/null. A decoded string with these chars is rejected and a fresh ID is generated. No injection is possible downstream because the accepted ID is guaranteed safe.

---

## Question 3: Context Variable Lifecycle and Exception Handling

**Threat:** The middleware sets correlation context but clears it only in a finally block. Could an exception in the app cause context to leak to the next request?

**Analysis:**

1. `websocket_client.py` lines 25-37:
   ```python
   async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
       if scope["type"] != "websocket":
           await self.app(scope, receive, send)
           return
       
       headers: objs.Headers = scope.get("headers", [])
       correlation = objs.WebSocketCorrelation.from_headers(headers)
       set_correlation_id(correlation.correlation_id)
       try:
           await self.app(scope, receive, send)
       finally:
           clear_correlation_id()
   ```
2. The context is set at line 33.
3. The finally block (line 37) unconditionally clears context.
4. In WebSocket, each new connection triggers a new `__call__` invocation, so context is cleared between connections.
5. Even if the app raises an exception, the finally block executes and clears context.

**Verdict:** NO ISSUE

**Reasoning:** The finally block guarantees cleanup. Each WebSocket connection is a separate ASGI invocation with its own context lifecycle. No context leakage between connections.

---

## Question 4: Scope Type Check and Passthrough Safety

**Threat:** The middleware checks `if scope["type"] != "websocket"` and passes through. Could this cause HTTP requests to be mishandled if mounted alongside HTTP handlers?

**Analysis:**

1. Line 27: `if scope["type"] != "websocket":`
2. Line 28: `await self.app(scope, receive, send)` and immediate `return`
3. Non-WebSocket scopes (HTTP, lifespan, etc.) are passed through WITHOUT setting correlation context.
4. This is the intended design: WebSocket-specific middleware should not affect HTTP requests.
5. If both HTTP and WebSocket handlers exist in the same app, there should be separate inbound middleware:
   - ASGI middleware for HTTP: `mixin_logging.adapters.asgi.CorrelationIdMiddleware`
   - WebSocket middleware for WebSocket: `mixin_logging.adapters.websocket.CorrelationIdMiddleware`

**Verdict:** NO ISSUE

**Reasoning:** The passthrough is intentional and safe. WebSocket middleware only affects WebSocket scopes. HTTP scopes are handled by separate HTTP middleware. This is the correct design pattern.

---

## Question 5: Generated UUID Format and Collision Risk

**Threat:** The generated correlation IDs use UUID4 hex[:12]. Could collisions occur? Could this cause tracing ambiguity?

**Analysis:**

1. Line 42-43: `uuid4().hex[: const.GENERATED_ID_LENGTH]` where `GENERATED_ID_LENGTH = 12`
2. UUID4 hex is 32 hex characters; taking the first 12 gives 2^48 possible values (~281 trillion).
3. For tracing purposes, collision probability in typical workloads (< 1 million concurrent connections) is negligible (birthday paradox).
4. The format matches other adapters in logging-mixin (ASGI, WSGI, Cloud).
5. Test coverage (test_websocket_objects.py line 29-31) verifies the generated ID is 12 hex chars.

**Verdict:** NO ISSUE

**Reasoning:** UUID4 hex[:12] is the canonical format for logging-mixin. Collision probability is acceptable for distributed tracing. The design is consistent with all other adapters.

---

## Question 6: Case-Insensitive Header Matching and Normalization

**Threat:** The adapter uses `.lower()` on header keys for case-insensitive matching (line 34). Could this create issues with other middleware that expect specific case?

**Analysis:**

1. Line 32: `target = const.CORRELATION_ID_HEADER.encode()` gives `b"x-correlation-id"`
2. Line 34: `if key.lower() == target` :  comparing lowercased key with the lowercase constant
3. HTTP headers are case-insensitive per RFC 7230; lowercasing both sides is the standard approach.
4. The matching is READ-ONLY; the adapter does not modify headers or scope.
5. Downstream middleware sees the original scope unchanged.

**Verdict:** NO ISSUE

**Reasoning:** Case-insensitive header matching is HTTP-standard. The adapter only reads; it does not modify the scope. No side effects on other middleware.

---

## Question 7: Correlation ID Propagation to Logs and External Systems

**Threat:** The correlation ID is extracted from inbound headers and set in context. Could an attacker inject a correlation ID that causes denial-of-logging (e.g., filling log storage with values that bypass log sampling)?

**Analysis:**

1. The correlation ID is a simple string, validated to be safe (non-empty, 1-128 chars, no CRLF/null).
2. The correlation ID is attached to logs via the stdlib adapter (mixin_logging.adapters.stdlib).
3. The ID itself cannot cause log injection (CRLF/null rejected).
4. The ID is a fixed-length string, bounded to 128 chars, so it cannot cause unbounded log growth.
5. Denial-of-logging would require the attacker to send millions of requests with unique IDs, which is a volume DoS, not an adapter vulnerability.

**Verdict:** NO ISSUE

**Reasoning:** The correlation ID is bounded and validated. Log injection is impossible due to character filtering. Denial-of-logging via volume is a network-layer concern, not an adapter defect.

---

## Question 8: Immutability and Frozen Dataclass Safety

**Threat:** `WebSocketCorrelation` is `@dataclass(frozen=True, slots=True)`. Could field mutation or pickling issues arise?

**Analysis:**

1. Line 17: `@dataclass(frozen=True, slots=True)`
2. `frozen=True` prevents field assignment after construction.
3. `slots=True` reduces memory overhead and prevents dynamic attribute assignment.
4. `__post_init__` (line 24-27) validates the invariant before the object is exposed.
5. If validation fails, the exception is raised before the object is constructed.

**Verdict:** NO ISSUE

**Reasoning:** Frozen dataclass with slots is the canonical pattern in logging-mixin. Immutability prevents accidental corruption. The __post_init__ guard ensures only safe values are exposed.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. Header extraction and iteration | NO ISSUE | N/A | None |
| 2. Header decoding and character validation | NO ISSUE | N/A | None |
| 3. Context variable lifecycle and exceptions | NO ISSUE | N/A | None |
| 4. Scope type check and passthrough | NO ISSUE | N/A | None |
| 5. Generated UUID format and collisions | NO ISSUE | N/A | None |
| 6. Case-insensitive header matching | NO ISSUE | N/A | None |
| 7. Correlation ID propagation and log injection | NO ISSUE | N/A | None |
| 8. Frozen dataclass immutability | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS**

The WebSocket adapter is secure against header injection, log injection, context leakage, and denial-of-service attacks. All threats were analyzed and found to have mitigations in place:

1. **Header parsing:** Safe iteration over ASGI server-validated headers.
2. **Character validation:** CRLF/null/oversized values are rejected; safe values are accepted.
3. **Context cleanup:** Finally block guarantees cleanup even on exception.
4. **Scope isolation:** WebSocket scopes are handled separately from HTTP; no cross-contamination.
5. **UUID safety:** UUID4 hex[:12] is bounded, collision probability is acceptable.
6. **Immutability:** Frozen dataclass prevents field mutation and accidental corruption.

No security blockers. The adapter is safe for production use.

---

## Recommended Actions

None. The adapter meets the security baseline for inbound correlation-ID extraction. No changes required.

---

## Audit Conclusion

The WebSocket adapter is secure and ready for production deployment.
