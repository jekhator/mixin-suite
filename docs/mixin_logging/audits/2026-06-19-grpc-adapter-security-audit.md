# gRPC Adapter Security Audit

**Date:** 2026-06-19  
**Auditor:** Security Engineer  
**Scope:** gRPC inbound correlation-ID extraction adapter (grpc_objects.py, grpc_client.py, constants/grpc.py)  
**Status:** COMPLETE

---

## Question 1: ServerInterceptor Hook Firing and Metadata Access

**Threat:** ServerInterceptor.intercept_service() is called on every RPC. Does it fire before or after the actual handler starts? Can metadata be mutated before the handler sees it?

**Analysis:**

1. `CorrelationInterceptor` extends `grpc.ServerInterceptor` (grpc_client.py line 13).
2. Line 16-28: `intercept_service()` receives `handler_call_details` and `continuation` callback.
3. Line 22: `metadata: objs.Metadata = handler_call_details.invocation_metadata` reads metadata.
4. gRPC's ServerInterceptor contract: intercept_service() is called BEFORE the handler is invoked, receives handler_call_details with read-only invocation_metadata, and can call `continuation()` to delegate to the handler.
5. The metadata is not mutated; it is a tuple of (name, value) pairs passed immutably.
6. Line 26: `return continuation(handler_call_details)` delegates to the next interceptor or handler with the original call_details (no modification).

**Verdict:** NO ISSUE

**Reasoning:** gRPC's ServerInterceptor runs before handler invocation and receives read-only metadata. The adapter reads metadata without mutation and delegates cleanly via continuation().

---

## Question 2: Metadata Extraction and Type Coercion

**Threat:** gRPC metadata values can be strings or bytes. Does the adapter handle both safely?

**Analysis:**

1. Line 22: `metadata: objs.Metadata = handler_call_details.invocation_metadata` receives metadata as `tuple[tuple[str, str | bytes], ...]`.
2. grpc_objects.py line 13: `Metadata = tuple[tuple[str, str | bytes], ...]` captures the union type.
3. Line 31: `dict(metadata).get(const.CORRELATION_ID_KEY)` converts metadata tuple to dict and retrieves the value.
4. Line 32: `isinstance(candidate, str) and cls._is_safe(candidate)` checks if the value is a string BEFORE validation.
5. If the value is bytes or unsafe, line 34-37 generates a fresh UUID.

**Critical finding:** The adapter only accepts string values (line 32). Byte values are silently rejected and replaced with generated IDs. This is safe but asymmetrical with ASGI/WSGI adapters which decode bytes to UTF-8. Consider documenting this choice or normalizing across adapters.

**Verdict:** NO ISSUE

**Reasoning:** The type check is explicit and safe. Byte metadata is rejected and a fresh ID is generated, ensuring no corruption. The asymmetry with HTTP adapters (which decode bytes) is acceptable because gRPC metadata typically uses strings.

---

## Question 3: Correlation ID Validation and Regeneration

**Threat:** Can unsafe correlation IDs be injected into context?

**Analysis:**

1. Line 23: `correlation = objs.GRPCCorrelation.from_metadata(metadata)` calls the factory method.
2. grpc_objects.py line 32: `isinstance(candidate, str) and cls._is_safe(candidate)` validates before construction.
3. grpc_objects.py line 40-44: `_is_safe()` checks: empty, overlong (>128), or contains CR/LF/null.
4. Line 25-26: `set_correlation_id(correlation.correlation_id)` sets only validated IDs.
5. grpc_objects.py line 23-26: `__post_init__` re-validates via `_is_safe()` and raises ValueError if invariant is breached.

**Verdict:** NO ISSUE

**Reasoning:** Validation is applied at two gates: factory method and __post_init__. Only safe IDs reach context. The invariant is enforceable.

---

## Question 4: Context Isolation and Finally-Block Clearance

**Threat:** If the handler raises an exception, is context still cleared?

**Analysis:**

1. Line 25-28: try/finally pattern wraps the handler invocation.
2. Line 26: `return continuation(handler_call_details)` invokes the handler.
3. Line 27-28: finally block unconditionally calls `clear_correlation_id()`.
4. Python's finally semantics ensure the block runs even if continuation() raises or returns early.

**Test evidence:** test_grpc_client.py lines 62-78 verify that context is cleared even on exception (test_intercept_clears_correlation_even_if_continuation_raises).

**Verdict:** NO ISSUE

**Reasoning:** The finally block is airtight. Context is cleared unconditionally, preventing leakage between requests.

---

## Question 5: Metadata Key Lookup and Case Sensitivity

**Threat:** gRPC metadata keys are case-sensitive. Does the adapter normalize keys, or does a caller sending "X-CORRELATION-ID" bypass the adapter?

**Analysis:**

1. Line 18: `CORRELATION_ID_KEY: Final = "x-correlation-id"` (lowercase).
2. grpc_objects.py line 31: `dict(metadata).get(const.CORRELATION_ID_KEY)` does a case-sensitive lookup.
3. gRPC metadata is case-sensitive; "x-correlation-id" ≠ "X-CORRELATION-ID".
4. If a caller sends "X-CORRELATION-ID" (uppercase), the adapter will not find it and will generate a fresh ID.

**Expected behavior:** gRPC convention is lowercase header names (matching HTTP/2 pseudo-headers). Uppercase is discouraged but valid.

**Implication:** Callers sending uppercase or mixed-case metadata will not have their IDs recognized. This is acceptable because the spec is case-sensitive, and the adapter generates fallback IDs. However, it could be surprising to callers migrating from HTTP.

**Verdict:** NO ISSUE

**Reasoning:** Case sensitivity is gRPC's standard. The adapter enforces the spec. Callers should use lowercase "x-correlation-id". Fallback generation ensures no tracing breakage.

---

## Question 6: Invocation Metadata Mutation and Passthrough

**Threat:** Does the interceptor filter, mutate, or suppress metadata before passing to the handler?

**Analysis:**

1. Line 26: `return continuation(handler_call_details)` passes the original handler_call_details unchanged.
2. handler_call_details.invocation_metadata is not modified.
3. The handler receives all original metadata, including any "x-correlation-id" header.

**Implication:** The handler receives the inbound metadata as-is, even if the adapter rejected it as unsafe and generated a fresh ID. The handler could read the unsafe metadata directly if it accesses handler_call_details.invocation_metadata. However, the adapter's responsibility is to set context, not to filter the raw transport.

**Verdict:** NO ISSUE

**Reasoning:** The adapter's responsibility is to set context, not to sanitize the inbound transport. The handler is responsible for validating metadata it consumes directly. This is acceptable separation of concerns.

---

## Question 7: UUID4 Generation and Entropy

**Threat:** Is the generated correlation ID sufficiently random and unique?

**Analysis:**

1. grpc_objects.py line 35: `uuid4().hex[: const.GENERATED_ID_LENGTH]` generates a UUID4 and truncates to 12 hex chars.
2. UUID4 provides ~122 bits of entropy (2^122).
3. Truncating to 12 hex chars (48 bits) reduces entropy to ~48 bits.
4. For correlation-ID purposes (non-cryptographic, collision detection only), 48 bits is sufficient for typical request volumes (< 1M concurrent requests).

**Verdict:** NO ISSUE

**Reasoning:** The truncation is intentional (readability). Entropy is sufficient for correlation-ID use cases. UUID4 is a standard Python library, well-implemented.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. ServerInterceptor hook firing and metadata access | NO ISSUE | N/A | None |
| 2. Metadata extraction and type coercion | NO ISSUE | N/A | Acceptable asymmetry with HTTP adapters (strings only) |
| 3. Correlation ID validation and regeneration | NO ISSUE | N/A | None |
| 4. Context isolation and finally-block clearance | NO ISSUE | N/A | None |
| 5. Metadata key lookup and case sensitivity | NO ISSUE | N/A | Callers must use lowercase "x-correlation-id" |
| 6. Invocation metadata mutation and passthrough | NO ISSUE | N/A | None |
| 7. UUID4 generation and entropy | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS**

The gRPC inbound adapter is secure against metadata injection, context corruption, and leakage attacks. The design correctly validates metadata before setting context, uses gRPC's standard ServerInterceptor protocol safely, and ensures context cleanup via finally block.

All seven threat questions resolve to NO ISSUE. No security blockers identified.

---

## Recommended Actions

None. The adapter is production-ready as-is.

**Optional documentation note:** Callers should be aware that metadata keys are case-sensitive and must use lowercase "x-correlation-id" for correlation IDs to be recognized. This aligns with gRPC/HTTP/2 convention but may surprise callers migrating from case-insensitive HTTP frameworks.

---

## Audit Conclusion

No security defects. The adapter is safe for production use.
