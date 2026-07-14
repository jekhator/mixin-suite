# FastAPI Adapter Security Audit

**Date:** 2026-07-13
**Auditor:** Security Engineer
**Scope:** FastAPI middleware correlation-ID extraction and response-header injection adapter (fastapi_objects.py, fastapi_client.py, constants/fastapi.py)
**Status:** COMPLETE

---

## Question 1: HTTP Header Extraction from FastAPI Request

**Threat:** FastAPI Request.headers is case-insensitive, but could a missing or malformed header cause issues?

**Analysis:**

1. Line 26 (fastapi_client.py):
   ```python
   headers = dict(request.headers)
   correlation = objs.FastApiCorrelation.from_headers(headers)
   ```

2. Line 35 (fastapi_objects.py): `raw = headers.get(const.CORRELATION_ID_HEADER)`
3. `CORRELATION_ID_HEADER = "x-correlation-id"` (from constants, string).
4. The conversion to dict preserves header casing.

**Edge cases:**
- Missing header: `.get()` returns None, fallback to uuid4 (correct).
- Header present but empty string: Falls through to uuid4 (correct, checked by `_is_safe`).
- Non-string value: Not possible with FastAPI Request.headers (always strings).

**Verdict:** GREEN

**Reasoning:** HTTP header extraction is defensive. Missing or malformed headers safely fall back to UUID generation.

---

## Question 2: Unsafe Character Validation (CRLF Injection Prevention)

**Threat:** Could unsafe header characters bypass validation and cause header injection?

**Analysis:**

1. Line 25 (fastapi_objects.py):
   ```python
   if any(char in const.UNSAFE_HEADER_CHARS for char in value):
       return False
   ```

2. `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})` (constants/fastapi.py line 28).
3. These are the canonical injection vectors: CRLF for header wrapping, null byte for string termination.

**Verdict:** GREEN

**Reasoning:** Character validation is complete for the threat model. The frozenset is immutable and efficient.

---

## Question 3: Max Length Validation

**Threat:** Could an oversized correlation ID cause memory exhaustion or buffer overflow?

**Analysis:**

1. Line 26 (fastapi_objects.py):
   ```python
   if len(value) > const.CORRELATION_ID_MAX_LENGTH:
       return False
   ```

2. `CORRELATION_ID_MAX_LENGTH = 128` (constants/fastapi.py line 20).
3. Typical UUID is 36 chars, trace IDs ~20 chars; 128 is a reasonable ceiling.
4. String length in Python is O(1) for built-in strings (cached).

**Verdict:** GREEN

**Reasoning:** Max length check prevents denial-of-service via oversized headers. Limit is reasonable.

---

## Question 4: Empty String Handling

**Threat:** Is an empty correlation ID correctly rejected?

**Analysis:**

1. Line 25 (fastapi_objects.py):
   ```python
   if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH:
       return False
   ```

2. The `not value` check catches empty strings before length check.
3. Line 21 (fastapi_objects.py): `__post_init__` validates non-empty.

**Verdict:** GREEN

**Reasoning:** Empty strings are rejected at both the factory method and the DTO level.

---

## Question 5: Middleware Context Cleanup

**Threat:** Could a missing `finally` block cause correlation ID to leak between requests?

**Analysis:**

1. Lines 29-34 (fastapi_client.py):
   ```python
   try:
       response = await call_next(request)
       response.headers[...] = ...
       return response
   finally:
       clear_correlation_id()
   ```

2. The `finally` block is present and unconditional.
3. Exception in `call_next` will still trigger cleanup.

**Verdict:** GREEN

**Reasoning:** Context cleanup is guaranteed by try/finally semantics.

---

## Question 6: Dependency Null Check

**Threat:** Could the dependency function return None and cause issues downstream?

**Analysis:**

1. Lines 40-47 (fastapi_client.py):
   ```python
   async def get_correlation_id_dependency() -> str:
       ...
       if corr_id is None:
           raise ValueError(...)
       return corr_id
   ```

2. Return type is `str` (not `str | None`).
3. Raises ValueError explicitly if None (defensive).

**Verdict:** GREEN

**Reasoning:** Dependency enforces non-None return via exception, preventing silent None propagation.

---

## Summary

All security aspects of the FastAPI adapter are sound. The adapter:
- Validates and rejects unsafe/oversized correlation IDs
- Falls back safely to UUID generation on missing headers
- Cleans up context reliably via try/finally
- Enforces non-None dependencies with explicit exceptions

**Overall Status:** APPROVED
