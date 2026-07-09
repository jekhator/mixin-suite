# ASGI Adapter Security Audit

**Date:** 2026-06-04  
**Auditor:** Security Engineer  
**Scope:** ASGI inbound correlation-ID extraction and response-header injection adapter (asgi_objects.py, asgi_client.py, constants/asgi.py)  
**Status:** COMPLETE

---

## Question 1: ASGI Scope Headers Format (Bytes vs. Strings)

**Threat:** ASGI scope["headers"] is a list of byte-tuples. Could a malformed header (non-bytes, non-utf8, oversized) crash the decoder?

**Analysis:**

1. Line 45-46 (asgi_client.py):
   ```python
   headers = scope.get("headers", [])
   for header_name, header_value in headers:
   ```

2. Line 47: `if header_name.lower() == const.CORRELATION_ID_HEADER:`
3. `CORRELATION_ID_HEADER = b"x-correlation-id"` (from constants, bytes).
4. Line 49: `decoded_id = header_value.decode("utf-8")`

**Edge cases:**
- header_value is not bytes: `.decode()` will crash with AttributeError.
- header_value is bytes but not valid UTF-8: `.decode("utf-8")` raises UnicodeDecodeError (line 50 catches it).
- header_name is not bytes: `.lower()` might fail (line 47).

**Issue:** The code assumes header_name and header_value are bytes. If a malicious/broken ASGI server sends strings instead, the code crashes with AttributeError (not caught).

**Severity:** LOW-MEDIUM. A broken ASGI server is already a major problem. The crash is in correlation extraction, not in the application proper (which would fail earlier). This is a robustness issue, not a security vulnerability.

**Verdict:** ⚠️ NEEDS REVIEW

**Recommended improvement:** Add defensive type checking and skip malformed headers:

```python
for header_name, header_value in headers:
    if not isinstance(header_name, bytes) or not isinstance(header_value, bytes):
        continue
    if header_name.lower() == const.CORRELATION_ID_HEADER:
        try:
            decoded_id = header_value.decode("utf-8")
        except UnicodeDecodeError:
            break
        ...
```

---

## Question 2: Case-Insensitive Header Matching

**Threat:** ASGI headers are byte-tuples with lowercase names (per spec). Is the case-insensitive comparison (line 47) necessary or could it introduce confusion?

**Analysis:**

1. ASGI spec (PEP 3333 / ASGI 3.0): header names MUST be lowercased and normalized to bytes.
2. Line 47: `if header_name.lower() == const.CORRELATION_ID_HEADER.lower()`
3. `CORRELATION_ID_HEADER = b"x-correlation-id"` (already lowercase).
4. Calling `.lower()` on an already-lowercase bytes object is idempotent but redundant.

**Verdict:** NO ISSUE

**Reasoning:** The case-insensitive comparison is defensive and correct. ASGI spec guarantees lowercase headers, but the comparison is harmless. No security issue, though slightly redundant.

---

## Question 3: Unicode Decoding Robustness

**Threat:** If header_value contains invalid UTF-8, the UnicodeDecodeError is caught (line 50), but does the function continue correctly?

**Analysis:**

1. Line 49-50: `try: decoded_id = header_value.decode("utf-8")`
2. `except UnicodeDecodeError: break`
3. The `break` exits the loop, stopping the search.
4. If no valid correlation ID is found, the fallback at line 58-61 generates a uuid4.

**Scenario:** A request with `X-Correlation-ID: <invalid-utf-8>` arrives. The decoder catches the exception, breaks, and falls back to generated. The request proceeds with a generated correlation ID.

**Verdict:** NO ISSUE

**Reasoning:** The exception handling is correct. Invalid UTF-8 is rejected gracefully with a fallback to generated ID. No crash, no data leakage.

---

## Question 4: Value Validation Before Context Setup

**Threat:** The adapter validates extracted IDs with `_is_safe()` (line 52) before setting context. Does validation cover all unsafe cases?

**Analysis:**

1. Line 52: `if cls._is_safe(decoded_id):`
2. `_is_safe()` (line 34-40):
   ```python
   if len(value) > const.CORRELATION_ID_MAX_LENGTH:
       return False
   if any(char in const.UNSAFE_HEADER_CHARS for char in value):
       return False
   return True
   ```

3. `CORRELATION_ID_MAX_LENGTH = 128`, `UNSAFE_HEADER_CHARS = {"\r", "\n", "\0"}`.
4. Missing: check for empty string (no `if not value`).

**Issue:** If decoded_id is an empty string, `_is_safe()` returns True (no check for empty), and the correlation ID is set to `""`. This violates the invariant that correlation IDs should be non-empty.

**Severity:** LOW. An empty correlation ID is logged, traced, and propagated, but doesn't cause crashes. However, it's semantically incorrect.

**Verdict:** ⚠️ NEEDS REVIEW

**Analysis:** The `_is_safe()` check is missing the empty-string guard. Compare with other adapters (httpx, botocore, requests, celery):
```python
if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:
    return False
```

The ASGI adapter's `_is_safe()` (line 37) lacks the `not value` check.

**Recommended improvement:** Add empty-string check:

```python
@staticmethod
def _is_safe(value: str) -> bool:
    """Check if a correlation ID value is safe for logging and HTTP headers."""
    if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:
        return False
    if any(char in const.UNSAFE_HEADER_CHARS for char in value):
        return False
    return True
```

---

## Question 5: Response Header Injection via Message Mutation

**Threat:** The middleware wraps the send callable and injects the correlation ID into the response (line 49-55). Could this cause issues with streaming responses or header finalization?

**Analysis:**

1. Line 49-55:
   ```python
   async def wrapped_send(message: objs.Message) -> None:
       """Inject correlation ID into response start message."""
       if message["type"] == const.RESPONSE_START_MESSAGE_TYPE:
           headers = list(message.get("headers", []))
           headers.append(correlation.response_header)
           message["headers"] = headers
       await send(message)
   ```

2. Line 63: `response_header` property: `return (const.CORRELATION_ID_HEADER, self.correlation_id.encode())`
3. `CORRELATION_ID_HEADER = b"x-correlation-id"`

**Semantics:** The middleware appends the correlation header to the response. This is safe IF the application has not already sent the response (line 51 checks `message["type"] == "http.response.start"`).

**Edge case:** If the application sends multiple "http.response.start" messages (violates ASGI spec but possible with buggy apps), each would have the correlation header appended. This is idempotent (same header injected multiple times) but violates the ASGI spec.

**Verdict:** NO ISSUE

**Reasoning:** The response header injection is correct and safe. ASGI applications are expected to send only one "http.response.start" message. If an application violates this, it's a bug in the application, not the middleware.

---

## Question 6: Context Setup and Cleanup Ordering

**Threat:** The middleware sets the correlation ID before calling the app and clears it in a finally block (line 57-60). Could an exception in the app prevent cleanup?

**Analysis:**

1. Line 26: `set_correlation_id(self.correlation.correlation_id)` (in ASGIApp)
2. Line 27: `await self.app(scope, receive, send)` (wrapped call)
3. Line 57-60 (CorrelationIdMiddleware):
   ```python
   try:
       await ASGIApp(self.app, correlation)(scope, receive, wrapped_send)
   finally:
       clear_correlation_id()
   ```

4. The finally block guarantees cleanup even if the app raises.

**Verdict:** NO ISSUE

**Reasoning:** The try-finally pattern is correct. Context is cleared unconditionally on exit, even if the app crashes. No context carryover is possible.

---

## Question 7: Scope-Type Filtering (Non-HTTP Requests)

**Threat:** The middleware checks `scope["type"] != const.HTTP_SCOPE_TYPE` (line 43) and skips non-HTTP. Could this miss WebSocket or other protocols?

**Analysis:**

1. Line 43: `if scope["type"] != const.HTTP_SCOPE_TYPE: await self.app(scope, receive, send); return`
2. `HTTP_SCOPE_TYPE = "http"` (from constants).
3. ASGI scope types: "http", "websocket", "lifespan", custom.
4. The middleware skips WebSocket and lifespan scopes, passing them through without correlation setup.

**Implication:** WebSocket connections don't propagate correlation IDs. This is intentional (WebSocket is bidirectional streaming, not request-response). Correlation ID extraction from WebSocket headers could be added in a future version.

**Verdict:** NO ISSUE

**Reasoning:** The decision to handle only HTTP is correct. WebSocket correlation propagation is a separate concern and can be added later if needed.

---

## Question 8: Generated ID Length and Collision (Byte Encoding)

**Threat:** The generated ID is `uuid4().hex[:12]` encoded as bytes (line 64-66). Is the byte encoding safe for HTTP headers?

**Analysis:**

1. Line 64: `return (const.CORRELATION_ID_HEADER, self.correlation_id.encode())`
2. `self.correlation_id` is a 12-character hex string (from line 59).
3. `.encode()` produces bytes: `"abc123def456".encode()` → `b"abc123def456"`.
4. Hex characters (0-9, a-f) are all ASCII, so encoding to UTF-8 is unambiguous.

**Verdict:** NO ISSUE

**Reasoning:** Hex strings encode cleanly to ASCII/UTF-8. No encoding ambiguities. The resulting bytes are valid for HTTP headers.

---

## Question 9: Event-Hook Timing vs. WSGI Adapter Precedence

**Threat:** Unlike httpx/requests (which use event hooks), ASGI uses middleware. Is middleware ordering enforced, and could a downstream middleware interfere with correlation?

**Analysis:**

1. Middleware are typically stacked as a chain: `app = CorrelationIdMiddleware(app1)(app2)(...)(original_app)`.
2. The innermost middleware executes last (closest to the app).
3. If CorrelationIdMiddleware is outermost, it sets correlation before any other middleware runs.
4. Downstream middleware can read/modify context but cannot prevent setup.

**Best practice:** CorrelationIdMiddleware should be the outermost middleware to ensure correlation is available to all downstream handlers.

**Documentation:** The adapter should document this requirement.

**Verdict:** ⚠️ NEEDS REVIEW

**Reasoning:** The middleware ordering dependency is implicit. Documentation should clarify that CorrelationIdMiddleware should be the outermost middleware for proper correlation propagation.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. ASGI scope headers format (bytes vs. strings) | NEEDS REVIEW | LOW | Add defensive type checking |
| 2. Case-insensitive header matching | NO ISSUE | N/A | None |
| 3. Unicode decoding robustness | NO ISSUE | N/A | None |
| 4. Value validation before context setup | NEEDS REVIEW | LOW | Add empty-string check to _is_safe() |
| 5. Response header injection via message mutation | NO ISSUE | N/A | None |
| 6. Context setup and cleanup ordering | NO ISSUE | N/A | None |
| 7. Scope-type filtering (non-HTTP) | NO ISSUE | N/A | None |
| 8. Generated ID length and byte encoding | NO ISSUE | N/A | None |
| 9. Event-hook timing vs. middleware ordering | NEEDS REVIEW | LOW | Document middleware ordering requirement |

---

## Overall Verdict

**PASS WITH MINOR IMPROVEMENTS**

The ASGI inbound adapter is secure against header injection and response header tampering. The design correctly validates extracted values, falls back to generated IDs, and cleans up context on exit.

Three improvements are recommended for robustness and consistency:

1. **Type safety:** Add defensive checks for header byte types (prevents AttributeError if ASGI server violates spec).
2. **Validation consistency:** Add empty-string check to `_is_safe()` to match other adapters.
3. **Documentation:** Clarify middleware ordering requirement.

---

## Recommended Actions

1. **Add defensive type checking (robustness):**

   ```python
   for header_name, header_value in headers:
       if not isinstance(header_name, bytes) or not isinstance(header_value, bytes):
           continue
       ...
   ```

2. **Add empty-string check to `_is_safe()` (consistency):**

   ```python
   @staticmethod
   def _is_safe(value: str) -> bool:
       if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:
           return False
       if any(char in const.UNSAFE_HEADER_CHARS for char in value):
           return False
       return True
   ```

3. **Add docstring to `CorrelationIdMiddleware` (documentation):**

   ```python
   class CorrelationIdMiddleware:
       """ASGI middleware for correlation ID context propagation.
       
       IMPORTANT: This middleware should be registered as the OUTERMOST
       middleware to ensure correlation ID is available to all downstream
       handlers and middleware.
       """
   ```

---

## Audit Conclusion

No security blockers. The adapter is safe for production use. The three recommended improvements are for robustness and consistency with other adapters, not for security.
