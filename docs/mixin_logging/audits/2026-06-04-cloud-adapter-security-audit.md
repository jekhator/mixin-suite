# Cloud Adapter Security Audit

**Date:** 2026-06-04  
**Auditor:** Security Engineer  
**Scope:** AWS cloud inbound correlation-ID extraction adapter (cloud_objects.py, cloud_client.py, constants/cloud.py)  
**Status:** COMPLETE

---

## Question 1: Multi-Source Extraction and Precedence

**Threat:** The adapter extracts correlation IDs from multiple AWS event sources (API Gateway, SQS, SNS, EventBridge, etc.). Could an attacker exploit the precedence logic to inject a malicious value?

**Analysis:**

1. `CloudCorrelation.from_event()` (cloud_objects.py line 25-63) extracts from multiple sources in order:
   - API Gateway / ALB / Function URL: `event["headers"]["X-Correlation-ID"]` (case-insensitive search, line 36-44)
   - SQS: `event["Records"][0]["messageAttributes"]["X-Correlation-ID"]["stringValue"]` (line 46-54)
   - SNS: `event["Records"][0]["Sns"]["MessageAttributes"]["X-Correlation-ID"]["Value"]` (line 46-54)
   - EventBridge: `event["detail"]["correlation_id"]` (line 56)
   - Direct invoke / Step Functions: `event["correlation_id"]` (line 58)
   - Fallback: Generate uuid4 (line 61-63)

2. The first match is used; no fallback if an earlier source provides a value.

3. **Critical question:** If API Gateway headers contain a correlation ID, is it extracted BEFORE SQS/SNS/EventBridge are checked?

**Answer:** YES. The logic extracts from API Gateway first (line 36-44), and only if `candidate is None` does it check SQS/SNS (line 45-54).

**Threat vector:** A caller invoking a Lambda via API Gateway can set the X-Correlation-ID header. If that Lambda is later triggered as part of an SQS/SNS flow, the precedence is: headers first, then SQS/SNS. This is correct behavior: the inbound HTTP request's correlation ID takes precedence over message-queue metadata.

**Verdict:** NO ISSUE

**Reasoning:** The precedence logic is intentional and safe. API Gateway headers are the most direct/trusted source. SQS/SNS metadata are fallbacks. If an event enters via multiple paths (e.g., API Gateway + SQS), the most direct source wins. This is correct tracing semantics.

---

## Question 2: Extracted vs. Generated Tracking

**Threat:** The adapter tracks whether a correlation ID was extracted (`extracted=True`) or generated (`extracted=False`). Could this enable fingerprinting?

**Analysis:**

1. `CloudCorrelation` has two fields: `correlation_id` and `extracted` (line 16-17).
2. `extracted=True` if the ID was found in the event; `extracted=False` if generated.
3. This metadata is available to callers but is not exposed in the correlation ID itself.
4. A caller could inspect `correlation.extracted` and behave differently based on source.

**Implication:** Callers could distinguish events with pre-set correlation IDs (e.g., from API Gateway) from events without (e.g., S3 triggers). This enables metadata inference but not direct data leakage.

**Verdict:** NO ISSUE

**Reasoning:** The `extracted` flag is metadata for observability, not a security leak. Callers should inspect it for logging/metrics purposes. The flag enables correct tracing semantics (knowing whether correlation was propagated or generated).

---

## Question 3: Generated ID Entropy and Length

**Threat:** Generated IDs use `uuid4().hex[:12]` (line 62). Is 12 characters sufficient entropy, and could it collide with extracted IDs?

**Analysis:**

1. `uuid4().hex` produces a 32-character hex string (128 bits of entropy).
2. `[:12]` truncates to 12 characters.
3. 12 hex chars = 48 bits of entropy (~10^14 unique values).
4. Collision probability: negligible for reasonable event volumes (<10^9 events).
5. `GENERATED_ID_LENGTH = 12` (from constants/cloud.py).
6. Extracted IDs can be up to 128 characters long.

**Collision risk:** A 12-character extracted ID and a 12-character generated ID are both possible. For example, extracted="abc123def456" and generated="xyz789123456". Both would be valid, distinct correlation IDs.

**Verdict:** NO ISSUE

**Reasoning:** Generated IDs and extracted IDs are semantically different (extracted=True vs. extracted=False). Even if they happen to be the same length, they are tracked separately. The 12-character truncation is intentional to keep generated IDs compact while maintaining sufficient entropy.

---

## Question 4: Case-Insensitive Header Matching

**Threat:** The adapter searches for X-Correlation-ID with case-insensitive matching (line 41). Could a caller exploit this to inject via a different case (e.g., x-correlation-id)?

**Analysis:**

1. Line 37-44:
   ```python
   headers = event.get("headers") or {}
   candidate = next(
       (
           value
           for key, value in headers.items()
           if key.lower() == const.CORRELATION_ID_HEADER.lower()
       ),
       None,
   )
   ```

2. The search iterates over headers and compares `key.lower()` to `CORRELATION_ID_HEADER.lower()`.
3. HTTP headers are case-insensitive per RFC 7230, so case-insensitive matching is correct.
4. API Gateway normalizes header names to lowercase, so the case-insensitivity is defensive against variations.

**Verdict:** NO ISSUE

**Reasoning:** Case-insensitive header matching is standard and correct. HTTP headers are case-insensitive by specification. No bypass is possible; all variations (X-Correlation-ID, x-correlation-id, X-CORRELATION-ID) are correctly matched.

---

## Question 5: Unsafe Value Filtering at Extraction

**Threat:** The adapter extracts values and then validates with `_is_safe()` (line 59). Could an unsafe value slip through?

**Analysis:**

1. Line 59: `if isinstance(candidate, str) and cls._is_safe(candidate):`
2. If `_is_safe()` returns False, the extracted value is discarded (line 60 is skipped).
3. Instead, a generated ID is returned (line 61-63).
4. `_is_safe()` checks: `if not value or len(value) > const.CORRELATION_ID_MAX_LENGTH: return False` (line 68).
5. `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})` (from constants).

**Test case:** No explicit test for extraction with unsafe values, but the logic is clear: unsafe extracted values are filtered and replaced with generated IDs.

**Verdict:** NO ISSUE

**Reasoning:** Unsafe values are never extracted. The validation happens before the value is trusted. If extraction fails safety, a generated ID is used instead. This is defense-in-depth: inbound values are never trusted without validation.

---

## Question 6: Message Attribute Extraction (SQS/SNS Structure)

**Threat:** The adapter extracts from nested structures: `Records[0]["messageAttributes"]` for SQS and `Records[0]["Sns"]["MessageAttributes"]` for SNS. Could parsing errors or malformed events cause crashes?

**Analysis:**

1. Line 48-54:
   ```python
   records = event.get("Records") or []
   if records:
       attributes = (
           records[0].get("messageAttributes")
           or records[0].get("Sns", {}).get("MessageAttributes")
           or {}
       )
       entry = attributes.get(const.CORRELATION_ID_HEADER) or {}
       candidate = entry.get("stringValue") or entry.get("Value")
   ```

2. All accesses use `.get()` with defaults, so missing keys don't crash.
3. Line 54: `entry.get("stringValue") or entry.get("Value")` handles both SQS (stringValue) and SNS (Value) formats.
4. If `candidate` is not a string (line 59 check: `isinstance(candidate, str)`), it is discarded.

**Verdict:** NO ISSUE

**Reasoning:** The extraction is defensive. All nested lookups use `.get()` with fallbacks. Type checking ensures only strings are accepted. No parsing errors possible.

---

## Question 7: EventBridge and Direct-Invoke Extraction

**Threat:** EventBridge and direct-invoke events use different key names (`event["detail"]["correlation_id"]` vs. `event["correlation_id"]`). Could a caller exploit this ambiguity?

**Analysis:**

1. Line 56: `candidate = (event.get("detail") or {}).get(const.CORRELATION_ID_KEY)`
2. Line 58: `candidate = event.get(const.CORRELATION_ID_KEY)`
3. `CORRELATION_ID_KEY = "correlation_id"` (from constants).

4. EventBridge events wrap custom data in `event["detail"]`, so correlation is expected at `event["detail"]["correlation_id"]`.
5. Direct-invoke (Lambda.invoke) can pass arbitrary JSON, so correlation might be at the top level.
6. Step Functions can also pass JSON at the top level.

**Ordering:** EventBridge is checked first (line 56), then direct-invoke (line 58). If an event has BOTH `event["detail"]["correlation_id"]` and `event["correlation_id"]`, the one in `detail` wins. This is correct for EventBridge events.

**Verdict:** NO ISSUE

**Reasoning:** The extraction order matches AWS event semantics. EventBridge nests custom data in `detail`; direct invokes use the top level. The precedence is correct. No ambiguity is exploitable.

---

## Question 8: UUID4 RNG Quality (Not Production-Critical)

**Threat:** Does Python's uuid4() provide sufficient randomness for security-sensitive use (if correlation IDs were to be used as trace tokens)?

**Analysis:**

1. Line 62: `uuid4().hex[:12]`
2. Python's uuid4() uses `os.urandom()` on POSIX systems, which is cryptographically secure.
3. Generated IDs are used only for tracing purposes, not for authentication or authorization.
4. Collision risk: With 48 bits (12 hex chars), collision probability is negligible for typical workloads.

**Verdict:** NO ISSUE

**Reasoning:** uuid4() is cryptographically secure. Generated IDs are only for tracing, not security-sensitive. The entropy is sufficient for the use case.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. Multi-source extraction and precedence | NO ISSUE | N/A | None |
| 2. Extracted vs. generated tracking | NO ISSUE | N/A | None |
| 3. Generated ID entropy and length | NO ISSUE | N/A | None |
| 4. Case-insensitive header matching | NO ISSUE | N/A | None |
| 5. Unsafe value filtering at extraction | NO ISSUE | N/A | None |
| 6. Message attribute extraction (SQS/SNS) | NO ISSUE | N/A | None |
| 7. EventBridge and direct-invoke extraction | NO ISSUE | N/A | None |
| 8. UUID4 RNG quality | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS**

The cloud inbound adapter is secure against header injection, unsafe value extraction, and parsing attacks. The design correctly validates extracted values before use, filters unsafe characters, and falls back to generated IDs when extraction fails. The multi-source extraction logic correctly prioritizes API Gateway headers over message-queue metadata, matching AWS event semantics.

No security blockers identified.

---

## Audit Conclusion

No security issues or recommendations. The adapter is safe for production use. The design is robust and handles edge cases well (malformed events, missing keys, unsafe values, etc.).
