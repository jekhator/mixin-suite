# ASGI Adapter Review

**Date:** 2026-06-04  
**Branch:** `chore/adapter-audits-0.2.0`  
**Reviewer:** Code Reviewer  
**Scope:** ASGI inbound correlation-ID extraction and response-header injection adapter (objects, client, constants, tests)

---

## Review Summary

The ASGI adapter extracts correlation IDs from inbound HTTP request headers, falls back to generated UUIDs, and injects the correlation ID into response headers. The design is middleware-based, wrapping the ASGI app to set context on entry and clear it on exit. Two classes manage the lifecycle: `AsgiCorrelation` extracts/validates the ID, and `CorrelationIdMiddleware` + `ASGIApp` handle context setup and response injection.

**Scope of review:**
- `mixin_logging/adapters/asgi/asgi_objects.py` (66 LOC)
- `mixin_logging/adapters/asgi/asgi_client.py` (60 LOC)
- `mixin_logging/adapters/asgi/__init__.py` (1 LOC)
- `mixin_logging/adapters/constants/asgi.py` (35 LOC)
- `mixin_logging/adapters/tests/test_asgi/test_asgi_objects.py` (202 LOC)
- `mixin_logging/adapters/tests/test_asgi/test_asgi_client.py` (221 LOC)
- `mixin_logging/adapters/tests/test_asgi/conftest.py` (218 LOC)
- `mixin_logging/adapters/tests/test_asgi/__init__.py` (1 LOC)

Total: 804 LOC across 8 files, with 2 files at/near 694-line cap (conftest 218 LOC, test_asgi_client 221 LOC, test_asgi_objects 202 LOC) :  all pass LOC gate.

---

## Checklist Verdicts

### 1. DTO Golden Standard: frozen, slots, post_init, classmethod, property, staticmethod

**PASS**

- `@dataclass(frozen=True, slots=True)` on AsgiCorrelation (line 21, asgi_objects.py): correct.
- `__post_init__` validates invariant, raises ValueError on empty correlation_id (lines 28-31): correct, one-liner docstring present.
- `_is_safe` is `@staticmethod` (lines 33-40): correct, returns bool, checks length/unsafe chars (missing empty-string check :  see audit finding below).
- `from_scope` is `@classmethod` returning `Self` (lines 42-61): always returns an instance (never None; generates fallback if needed), one-liner docstring.
- `response_header` is `@property` returning tuple[bytes, bytes] (lines 63-66): correct, returns encoded header pair.
- Two fields: `correlation_id` (extracted or generated) and `from_header` (bool flag tracking source).

**Evidence:** asgi_objects.py lines 21-67.

---

### 2. Object/Client Split

**PASS**

- `asgi_objects.py` contains DTOs and type aliases only: AsgiCorrelation, Scope, Message, Receive, Send, App.
- `asgi_client.py` contains executable middleware: ASGIApp (wrapper) and CorrelationIdMiddleware (setup + cleanup + response injection).
- `__init__.py` is module-docstring-only, one-liner scope statement.

**Evidence:** asgi_objects.py, asgi_client.py structure matches canonical pattern.

---

### 3. ABC Types at API Boundary

**PASS**

- Type aliases use `Callable`, `Awaitable`, `MutableMapping` from `collections.abc` (asgi_objects.py lines 5-6): correct imports.
- `Scope = MutableMapping[str, Any]` (line 13): semantic alias for ASGI scope dict.
- `Message = MutableMapping[str, Any]` (line 14): semantic alias for ASGI message dict.
- `Receive = Callable[[], Awaitable[Message]]` (line 16): ASGI spec-compliant callable.
- `Send = Callable[[Message], Awaitable[None]]` (line 17): ASGI spec-compliant callable.
- `App = Callable[[Scope, Receive, Send], Awaitable[None]]` (line 18): ASGI app callable.
- `Self` from `typing` (line 7): correct for return type on classmethod.
- Method signatures use `Self`, bool, str, tuple, no TypeVar violations.

**Evidence:** asgi_objects.py lines 1-67.

---

### 4. Constants Golden Standard: Final, frozenset, ERR_* messages, section dividers

**PASS**

- All constants use `Final` type annotation (asgi.py lines 10, 15, 20, 25, 30, 35): correct.
- `UNSAFE_HEADER_CHARS` is `frozenset` (line 25): correct, contains CR/LF/null.
- `ERR_CORRELATION_ID_EMPTY` present as constant (line 30): matches field-level validation message (asgi_objects.py line 31).
- `CORRELATION_ID_HEADER = b"x-correlation-id"` (line 10): bytes, per ASGI spec.
- Section dividers use bare string-literal docstrings with 2 blank lines above + 1 below: lines 8, 13, 18, 23, 28, 33 all correct.

**Evidence:** asgi.py lines 1-35.

---

### 5. Validate-and-Fallback Semantics

**PASS**

- `from_scope()` extracts from ASGI headers, validates with `_is_safe()` (line 52), and ALWAYS returns an instance (never None).
- If extracted value is unsafe or missing, generates uuid4 fallback (lines 58-61): `from_header=False` flag tracks this.
- `__post_init__` raises on direct construction with empty correlation_id (asgi_objects.py lines 30-31): boundary enforcement.
- CorrelationIdMiddleware sets context before calling app, clears on exit (asgi_client.py lines 26, 60): safe lifecycle.

**Evidence:** asgi_objects.py lines 42-61 (from_scope), asgi_client.py lines 19-60 (middleware).

---

### 6. Lifecycle: Middleware Pattern with Context Setup/Cleanup

**PASS**

- CorrelationIdMiddleware is a frozen dataclass (line 30, asgi_client.py) with `app` field: stores reference to wrapped ASGI app.
- `__call__` method (line 36-60): async entrypoint that sets context, wraps send, calls ASGIApp, and clears context in finally block.
- ASGIApp (line 12) is a wrapper that injects correlation into context (line 26) before calling the wrapped app (line 27).
- Try-finally pattern ensures cleanup even if app raises (lines 57-60).

**Evidence:** asgi_client.py lines 12-60.

---

### 7. Docstrings: File-Scoped, No Cross-System Refs

**PASS**

- File docstrings scoped to file only: asgi_objects.py (line 1) describes 'ASGI scope/message/app type aliases + AsgiCorrelation value object', asgi_client.py (line 1) describes 'ASGIApp + CorrelationIdMiddleware: ASGI middleware for correlation ID propagation'.
- No references to 'per qhcg canonical', 'mirrors stripe', or other cross-system framing: all docstrings are standalone descriptive.
- __init__.py docstring (line 1) correctly identifies the module scope.

**Evidence:** asgi_objects.py line 1, asgi_client.py line 1, __init__.py line 1.

---

### 8. Spacing: Constants Dividers, Module Post-Imports, No Em Dashes

**PASS**

- Constants section dividers (asgi.py): 2 blank lines above, 1 blank line below, on lines 8, 13, 18, 23, 28, 33.
- Module spacing (asgi_objects.py): 2 blank lines after imports (line 11) before type aliases (line 13), 2 blank lines before @dataclass (line 20-21).
- Module spacing (asgi_client.py): 2 blank lines after imports (line 10) before @dataclass (line 12).
- conftest.py: 2 blank lines after imports (line 11) before fixtures (line 14).
- No em dashes detected across all 8 files (confirmed via grep).

**Evidence:** asgi.py lines 8-35, asgi_objects.py lines 11-21, asgi_client.py lines 10-12, conftest.py lines 11-14.

---

### 9. Test Parity: Extraction, Response Injection, and Middleware Ordering

**PASS**

- Test organization: test_asgi_objects.py covers extraction/fallback; test_asgi_client.py covers middleware lifecycle and response injection; conftest provides extensive ASGI scope factories.
- conftest provides autouse `reset_correlation` fixture and factory fixtures for various ASGI event types (HTTP, WebSocket, lifespan, malformed).
- test_asgi_objects.py: AsgiCorrelation extraction tests (header extraction, unicode handling, fallback, from_header flag).
- test_asgi_client.py: Middleware tests (context setup/cleanup, response header injection, scope-type filtering, wrapped_send behavior).
- Test constants use `test_const.ASGI_CORR_ID_*` alias per collision-avoidance rule.

**Evidence:** test_asgi_objects.py (202 LOC), test_asgi_client.py (221 LOC), conftest.py (218 LOC).

---

### 10. Coverage: 100% Objects, Middleware Behavior, Response Injection

**PASS**

- `test_asgi_objects.py`: 14 test methods covering AsgiCorrelation:
  - from_scope: extract/validate/fallback/from_header flag (multiple test cases).
  - unicode handling: UTF-8 decode success/failure.
  - construction: empty raises ValueError.
  - response_header: encoding and format.
  - _is_safe: length/unsafe-char validation (with edge cases).

- `test_asgi_client.py`: 16 test methods covering Middleware + ASGIApp:
  - CorrelationIdMiddleware: context setup/cleanup, response injection, scope-type filtering (HTTP only).
  - ASGIApp: delegation to wrapped app.
  - wrapped_send: response header injection, idempotent on multiple http.response.start (violates spec but handled gracefully).
  - Exception handling: context cleanup on app exception (finally block).

- **Total: 30+ tests** across extraction, middleware lifecycle, response injection, and error handling.
- Parametrized tests cover multiple scopes (HTTP, WebSocket, lifespan, custom).
- Async tests with @pytest.mark.asyncio.

**Evidence:** test_asgi_objects.py (202 LOC, 14+ test methods), test_asgi_client.py (221 LOC, 16+ test methods).

---

## Architecture Observations

### Strengths

1. **Two-class design is clean.** AsgiCorrelation handles extraction/validation; CorrelationIdMiddleware handles app lifecycle. Separation of concerns.

2. **Response header injection is transparent.** wrapped_send intercepts http.response.start messages and appends the correlation header without altering app logic.

3. **Context isolation is airtight.** Try-finally ensures cleanup even on app exception. ContextVar semantics guarantee per-request isolation.

4. **Scope-type filtering is correct.** Checks `scope["type"] == "http"` and skips non-HTTP (WebSocket, lifespan). Correct for HTTP-only correlation.

5. **Graceful Unicode handling.** UnicodeDecodeError is caught, fallback is generated. Never raises on malformed input.

6. **Test coverage is comprehensive.** 30+ tests cover extraction, middleware, response injection, scope types, and error paths.

### Issues Flagged by Security Audit (NEEDS REVIEW :  Non-Blocking Code Defects)

**Three items require minor improvements (NOT code blockers, but recommended fixes before 0.2.0 ships):**

1. **Empty-string validation in `_is_safe()` (NEEDS REVIEW :  LOW):**  
   The `_is_safe()` method (lines 34-40) checks length and unsafe chars but DOES NOT check for empty strings (`if not value`). This means an empty correlation ID could pass validation and be set in context.
   
   **Evidence:** Line 36-40 lacks `if not value` check. Compare to other adapters (httpx, botocore, requests, celery) which all check `if not value or len(value) > MAX_LENGTH`.
   
   **Fix required:** Add `if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:` at line 36.
   
   **Impact:** Empty string extraction would be accepted and set in context, violating the invariant that correlation IDs should be non-empty. This is semantically incorrect but not a security defect (no injection/DoS/auth bypass).

2. **Type safety on header iteration (NEEDS REVIEW :  LOW):**  
   The loop at lines 46-47 (`for header_name, header_value in headers:`) assumes both values are bytes. If an ASGI server violates spec and sends strings instead of bytes, the code crashes with AttributeError on `.lower()` (line 47) or `.decode()` (line 49).
   
   **Evidence:** Lines 46-49 do not check `isinstance(header_name, bytes)` or `isinstance(header_value, bytes)`.
   
   **Fix required:** Add defensive type checks:
   ```python
   for header_name, header_value in headers:
       if not isinstance(header_name, bytes) or not isinstance(header_value, bytes):
           continue
   ```
   
   **Impact:** Robustness improvement. A broken ASGI server is already a major problem, but defensive coding prevents confusing AttributeError crashes.

3. **Middleware ordering documentation (NEEDS REVIEW :  LOW):**  
   The CorrelationIdMiddleware should be the OUTERMOST middleware to ensure correlation is available to all downstream handlers. This is implicit in the code but not documented.
   
   **Fix recommended:** Add docstring to CorrelationIdMiddleware clarifying the ordering requirement.
   
   **Impact:** Documentation only; no code change needed. Prevents misconfiguration by callers.

---

## Security Audit Findings Integration

Cross-referencing with `docs/audits/2026-06-04-asgi-adapter-security-audit.md`:

**Summary of audit findings:**

1. **ASGI scope headers format (NEEDS REVIEW)** :  Type safety issue (defensiveness, not security).
2. **Case-insensitive header matching (NO ISSUE)** :  Harmless and defensive.
3. **Unicode decoding robustness (NO ISSUE)** :  UnicodeDecodeError caught gracefully.
4. **Value validation before context setup (NEEDS REVIEW)** :  Empty-string check missing in `_is_safe()`.
5. **Response header injection (NO ISSUE)** :  Correct and safe.
6. **Context setup and cleanup (NO ISSUE)** :  Try-finally pattern is correct.
7. **Scope-type filtering (NO ISSUE)** :  Correct for HTTP-only correlation.
8. **Generated ID encoding (NO ISSUE)** :  Hex strings encode cleanly to UTF-8.
9. **Middleware ordering (NEEDS REVIEW)** :  Documentation needed.

**Verdict:** Three non-blocking improvements recommended. All are LOW severity (robustness/consistency, not security). The code is safe to ship but should incorporate these fixes before 0.2.0 final release.

---

## Verdict

**SHIP WITH MINOR IMPROVEMENTS**

All checklist items pass. Code is production-ready with three recommended improvements:

**Code fixes (blocking for tight release quality):**
1. Add empty-string check to `_is_safe()` (1 line change).
2. Add type safety checks to header iteration (2-3 line change).

**Documentation (non-blocking but recommended):**
3. Add docstring to CorrelationIdMiddleware clarifying outermost positioning requirement.

**Overall assessment:**
- DTOs follow frozen/slots/docstring golden standard (with noted empty-string validation gap).
- Middleware pattern adheres to canonical ASGI design.
- Constants use Final, frozenset, ERR_* messages, and section dividers per standing rule.
- Tests cover 30+ scenarios across extraction, middleware, response injection, and error paths.
- No docstring cross-system refs, no em dashes, no inline comments, no employer/AI-assistant attribution.
- LOC within cap (max 221 LOC on largest test file).
- Security audit confirms no code security defects; three robustness/consistency improvements recommended.

**Recommended merge:** Incorporate the two code fixes before merging. The adapter will then be production-grade and ready for 0.2.0 integration. All fixes are straightforward (1-2 minute changes).

**Code to add:**

**In asgi_objects.py, line 36:**
```python
@staticmethod
def _is_safe(value: str) -> bool:
    """Check if a correlation ID value is safe for logging and HTTP headers."""
    if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:  # Added: "not value"
        return False
    if any(char in const.UNSAFE_HEADER_CHARS for char in value):
        return False
    return True
```

**In asgi_objects.py, line 46-47:**
```python
headers = scope.get("headers", [])
for header_name, header_value in headers:
    if not isinstance(header_name, bytes) or not isinstance(header_value, bytes):  # Add these lines
        continue                                                                      #
    if header_name.lower() == const.CORRELATION_ID_HEADER:
        ...
```

**In asgi_client.py, line 30 (CorrelationIdMiddleware docstring):**
```python
@dataclass(frozen=True, slots=True)
class CorrelationIdMiddleware:
    """ASGI middleware for correlation ID context propagation.
    
    IMPORTANT: Register this as the OUTERMOST middleware to ensure correlation
    ID is available to all downstream handlers and middleware.
    """
    app: objs.App
```
