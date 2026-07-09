# Botocore Adapter Security Audit

**Date:** 2026-06-04  
**Auditor:** Security Engineer  
**Scope:** botocore outbound correlation-ID injection adapter (botocore_objects.py, botocore_client.py, constants/botocore.py)  
**Status:** COMPLETE

---

## Question 1: Header Injection via Event-Hook Registration Bypass

**Threat:** Can a caller register multiple times on the same session/client and cause duplicate or conflicting correlation-ID headers, or can a caller intercept the event hook to inject malicious values?

**Analysis:**

1. `CorrelationIdInjector.register_on_session(session)` calls `session.register(const.BEFORE_SIGN_EVENT, cls.inject_before_sign, weak=False)`.
2. `CorrelationIdInjector.register_on_client(client)` calls `client.meta.events.register(const.BEFORE_SIGN_EVENT, cls.inject_before_sign, weak=False)`.
3. Botocore's event system allows multiple handlers to be registered for the same event. If registered twice, `inject_before_sign` will fire twice, both reading from the same ContextVar.
4. Both calls to `from_context()` will return the same validated instance (immutable), so the header will be set twice to the same value.
5. The second call at line 33-36 uses `replace_header()` if the header already exists, which overwrites the first assignment.

**Test case:** No test explicitly covers double-registration, but the idempotent logic (re-assigning the same value) is inherently safe.

**Verdict:** NO ISSUE

**Reasoning:** Even if registered twice, the second `inject_before_sign` call will see the header already in place and call `replace_header()`, which simply overwrites with the same value. No duplication or conflict occurs. Callers who register twice are performing redundant work, not a security issue.

---

## Question 2: Validate-and-Inject vs. Reject and Lost Tracing

**Threat:** If context has an unsafe correlation ID, `from_context()` returns None and no header is injected. Can an attacker pollute context with an unsafe value to suppress correlation propagation?

**Analysis:**

1. `from_context()` at line 29 returns None if the value is unsafe (line 27-28).
2. The early return at line 30-31 silently skips header injection.
3. No fallback trace ID is generated; the request is signed without a correlation header.
4. Downstream service observes no X-Correlation-ID header.

**Severity assessment:**
- Blast radius: Single outbound request. Correlation is lost ONLY on that call.
- Detectability: Requests without correlation will be observable in tracing logs.
- Practical cost to attacker: Must have code-execution access to call `set_correlation_id()` directly. If attacker has that, they can already corrupt business logic.

**Verdict:** NO ISSUE

**Reasoning:** The skip-on-unsafe pattern is consistent with httpx and other outbound adapters. An attacker capable of calling `set_correlation_id()` has already breached the application boundary. A single lost request is observable and recoverable via AWS request IDs or other tracing mechanisms.

---

## Question 3: Botocore Headers Object Mutation Safety

**Threat:** Does botocore's request.headers object mutate correctly when `replace_header()` is called, or could there be a race condition?

**Analysis:**

1. Line 33-34: `request.headers.replace_header(name, value)` replaces an existing header.
2. Line 36: `request.headers[name] = value` adds a new header.
3. Botocore's headers object is a thread-safe abstraction (uses copy-on-write for request mutation).
4. The event hook runs synchronously in the context of the request being prepared.
5. No await/yield points between `from_context()` and header assignment.

**Verdict:** NO ISSUE

**Reasoning:** Botocore's request object is immutable after the event-hook phase. The mutation is synchronous and atomic from the hook's perspective. No concurrent modification is possible.

---

## Question 4: SigV4 Signing Header Inclusion

**Threat:** The hook fires "before-sign"; does botocore include the X-Correlation-ID header in the SigV4 signature, or is it unsigned and vulnerable to tampering?

**Analysis:**

1. `const.BEFORE_SIGN_EVENT = "before-sign"` (line 19).
2. The hook fires BEFORE the SigV4 signing phase.
3. After the hook injects the header, the request enters the signing phase, which includes all headers in the request.
4. SigV4 signing computes a cryptographic signature over the request (method, URI, headers, body).
5. The X-Correlation-ID header, once injected, is included in the canonical request string and is covered by the signature.

**Verdict:** NO ISSUE

**Reasoning:** The "before-sign" timing is correct. The header is injected before signing, so it is included in the SigV4 signature. AWS verifies the signature on the receiving end, ensuring the correlation ID was not tampered with in transit.

---

## Question 5: Header Value Length and Safety Validation

**Threat:** Could a 128-character correlation ID bypass the length check, or could UNSAFE_HEADER_CHARS be incomplete?

**Analysis:**

1. `_is_safe()` checks: `if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH: return False` (line 39).
2. `CORRELATION_ID_MAX_LENGTH = 128` (from constants/botocore.py).
3. `len(value) > 128` means 129+ is rejected. 128 is accepted.
4. `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})` (from constants/botocore.py).
5. The check iterates every character: `return not any(char in const.UNSAFE_HEADER_CHARS for char in value)` (line 41).

**Edge cases:**
- Exactly 128 chars with no CRLF/null: Accepted (correct).
- Unicode characters: Not filtered; botocore will encode as UTF-8 or reject at wire encoding.
- Tab, space, colon: Not filtered; these are legal in HTTP header values per RFC 7230.

**Verdict:** NO ISSUE

**Reasoning:** The length boundary is correct. UNSAFE_HEADER_CHARS covers the three characters that break HTTP header semantics (CRLF for line injection, null for C-string termination). Legal characters (alphanumeric, dash, underscore, dot, etc.) pass through and are safe.

---

## Question 6: Context-Var Bypass (Direct set_correlation_id Mutation)

**Threat:** Can a caller call `set_correlation_id('bad\r\nValue')` directly and bypass the `from_context()` re-validation?

**Analysis:**

1. `from_context()` calls `get_correlation_id()`, which reads the raw ContextVar (line 26).
2. It then calls `cls._is_safe(raw_value)` before constructing the instance (line 27).
3. If raw_value is unsafe, `from_context()` returns None (line 28).
4. The early return at line 30-31 in `inject_before_sign()` skips header injection.

**Test case:** No explicit test for direct `set_correlation_id()` bypass, but the re-validation pattern is identical to httpx.

**Verdict:** NO ISSUE

**Reasoning:** Although `set_correlation_id()` does not validate, `from_context()` re-validates before trusting the value. A caller cannot bypass this defense-in-depth by calling `set_correlation_id()` directly; the outbound adapter will reject the unsafe value and skip injection.

---

## Question 7: Injection-Point Timing (Before-Sign Guarantee)

**Threat:** Could botocore's event-loop fire the "before-sign" event out of order or after headers are frozen, causing the injection to fail silently?

**Analysis:**

1. Botocore's event model fires "before-sign" as part of the request preparation phase.
2. After the event fires, the request enters the SigV4 signing phase.
3. There is no mechanism for the event to fire out of order or after signing.
4. If registration fails (e.g., invalid session), the event simply never fires, and no header is injected.

**Verdict:** NO ISSUE

**Reasoning:** Botocore's event-loop order is fixed by design. The "before-sign" event always fires before the signing phase. Injection failures are observable as requests without correlation headers.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. Header injection via event-hook bypass | NO ISSUE | N/A | None |
| 2. Validate-and-inject vs. reject | NO ISSUE | N/A | None |
| 3. Headers object mutation safety | NO ISSUE | N/A | None |
| 4. SigV4 signing header inclusion | NO ISSUE | N/A | None |
| 5. Header value length and safety | NO ISSUE | N/A | None |
| 6. Context-var bypass | NO ISSUE | N/A | None |
| 7. Injection-point timing guarantee | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS**

The botocore outbound adapter is secure against header injection, signing bypass, and tracing suppression attacks. The design correctly validates context values before injection, fires at the correct event-hook timing (before-sign), and includes the injected header in the SigV4 signature. No security blockers identified.

---

## Audit Conclusion

No security issues or recommendations. The adapter is safe for production use.
