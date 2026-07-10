# Stdlib Adapter Security Audit

**Date:** 2026-06-04  
**Auditor:** Security Engineer  
**Scope:** stdlib logging.Filter adapter (stdlib_client.py, constants/stdlib.py)  
**Status:** COMPLETE

---

## Question 1: LogRecord Attribute Injection and Name Collision

**Threat:** The filter stamps `record.correlation_id` directly. Could a caller tamper with the LogRecord before it reaches the filter, or could the attribute name collide with a legitimate record attribute?

**Analysis:**

1. Line 16-20: `setattr(record, const.CORRELATION_RECORD_ATTR, get_correlation_id() or const.UNSET_CORRELATION_ID)`
2. `CORRELATION_RECORD_ATTR = "correlation_id"` (from stdlib constants).
3. Python's LogRecord class has a fixed set of standard attributes: name, msg, args, created, msecs, levelname, levelno, pathname, filename, module, exc_info, exc_text, stack_info, lineno, funcName, etc.
4. `correlation_id` is NOT a standard LogRecord attribute; it is a custom attribute added by this filter.
5. A caller can pre-set `record.correlation_id = 'value'` before the filter runs, but the filter will overwrite it (line 16-20).

**Severity:** Low. A caller who can manipulate LogRecords before they reach filters already has code-execution access and can do worse (e.g., modify log levels, suppress messages).

**Verdict:** NO ISSUE

**Reasoning:** The attribute name is unlikely to collide with standard logging attributes. Custom attributes on LogRecords are common practice. The filter runs before the record is formatted, so it always has the final say on the `correlation_id` value. No security issue.

---

## Question 2: Unset Correlation Sentinel vs. No Correlation

**Threat:** The filter sets `record.correlation_id = "-"` (the UNSET_CORRELATION_ID sentinel) when context has no correlation. Could a formatter distinguish this from a truly set value, enabling fingerprinting?

**Analysis:**

1. Line 19: `get_correlation_id() or const.UNSET_CORRELATION_ID`
2. `UNSET_CORRELATION_ID = "-"` (from constants).
3. When context is unset, the record attribute is set to `"-"`.
4. When context has a value, the record attribute is set to that value.
5. A downstream formatter can inspect `record.correlation_id` and distinguish `"-"` from other values.

**Fingerprinting vector:** An attacker could observe that requests with no correlation ID are stamped with `"-"`, enabling them to fingerprint requests that never had a correlation set. However, this is weak intelligence (does not leak data), and the existence of an "unset" indicator is intentional and expected.

**Verdict:** NO ISSUE

**Reasoning:** The sentinel value is intentional and expected. Distinguishing unset from set is a feature, not a bug. The information leaked (existence of unset state) is not sensitive. Standard logging practice includes similar sentinel values (e.g., `None` for missing values).

---

## Question 3: No Wire-Level Injection (Pure Internal Logging)

**Threat:** Does the stdlib filter ever stamp correlation IDs into HTTP headers or wire-level messages?

**Analysis:**

1. Line 16-20: `setattr(record, const.CORRELATION_RECORD_ATTR, ...)`
2. This sets a Python LogRecord attribute, not a wire-level header.
3. The LogRecord is then formatted by a logging.Formatter (which the caller provides).
4. The formatter can use the `record.correlation_id` attribute in the log message, but that is the formatter's responsibility.
5. This adapter does NOT inject headers into HTTP responses or wire protocols.

**Verdict:** NO ISSUE

**Reasoning:** This is purely an internal logging adapter. It does not touch wire-level communication. Any correlation ID included in log output is the formatter's choice, not the adapter's. No injection or wire-level vulnerability.

---

## Question 4: LogRecord Filter Return Value (Always True)

**Threat:** The filter always returns True (line 21). Could this suppress logs or cause unintended behavior?

**Analysis:**

1. Line 21: `return True`
2. In Python's logging framework, a filter returning False suppresses the log record (discards it).
3. Returning True allows the record to pass to the next handler/filter.
4. This filter always returns True, so it never suppresses logs.
5. The filter's only side-effect is stamping the correlation_id attribute.

**Verdict:** NO ISSUE

**Reasoning:** Returning True is the correct behavior for a filter that does not suppress logs. The filter is purely additive (adding an attribute), so suppression would be incorrect.

---

## Question 5: ContextVar Read Without Validation

**Threat:** The filter reads `get_correlation_id()` directly without calling `_is_safe()`. Could an unsafe correlation ID from context be logged?

**Analysis:**

1. Line 19: `get_correlation_id() or const.UNSET_CORRELATION_ID`
2. Unlike outbound adapters (httpx, requests, botocore), the stdlib filter does NOT validate the correlation ID.
3. The value is a Python LogRecord attribute, NOT a wire-level header.
4. Log formatters typically quote or escape log values, so CRLF/null characters are rendered as escaped sequences in the output.
5. Even if a LogRecord attribute contains CRLF, it would be rendered as `\r\n` in the formatted log message.

**Severity:** Low. Log output is typically line-oriented, and CRLF in log values can cause alignment issues or confuse log parsers, but does not cause injection attacks.

**Test case:** No test explicitly covers unsafe correlation ID logging.

**Verdict:** ⚠️ MILD CONCERN

**Analysis:** While the stdlib adapter does not validate the correlation ID, the practical impact is low. Log formatters typically escape special characters. However, for consistency with other adapters (httpx, requests, botocore, celery) and to prevent malformed logs, the filter could optionally validate or strip unsafe characters.

**Recommended improvement:** Consider adding an optional `_is_safe()` check and either rejecting unsafe values (falling back to sentinel) or stripping CRLF/null characters from the correlation ID before setting the attribute. Example:

```python
def filter(self, record: logging.LogRecord) -> bool:
    correlation_id = get_correlation_id()
    if correlation_id and not self._is_safe(correlation_id):
        correlation_id = None
    setattr(
        record,
        const.CORRELATION_RECORD_ATTR,
        correlation_id or const.UNSET_CORRELATION_ID,
    )
    return True
```

---

## Question 6: Filter Attachment and Lifecycle

**Threat:** The `add_correlation_filter()` helper (line 24-28) attaches the filter to a logger. Could the filter be attached multiple times, or could it persist indefinitely?

**Analysis:**

1. Line 26-27: `logger.addFilter(correlation_filter)` attaches the filter.
2. Python's logging framework allows multiple filters on the same logger. If attached twice, both fire.
3. Both calls to `setattr(record, 'correlation_id', ...)` overwrite the previous value with the same value.
4. No duplication or corruption occurs.

**Lifecycle:** Filters persist on a logger until explicitly removed (line: no `remove_filter` call). The filter object is referenced by the logger, so it won't be garbage-collected while the logger is alive.

**Verdict:** NO ISSUE

**Reasoning:** Attaching the same filter multiple times is idempotent. The filter persists for the lifetime of the logger, which is expected behavior. Explicit removal is the caller's responsibility.

---

## Question 7: Thread-Safety of LogRecord Mutation

**Threat:** Multiple threads logging simultaneously might cause a race condition when setting the correlation_id attribute on a LogRecord.

**Analysis:**

1. Each thread has its own ContextVar context, so `get_correlation_id()` returns thread-local values.
2. Each call to a logging handler creates a new LogRecord instance.
3. The filter receives the new LogRecord and calls `setattr(record, 'correlation_id', ...)`.
4. No two threads mutate the same LogRecord (each has its own).

**Verdict:** NO ISSUE

**Reasoning:** LogRecords are created per log call; no shared state. ContextVar values are thread-local. No race condition is possible.

---

## Summary

| Question | Verdict | Severity | Action |
|----------|---------|----------|--------|
| 1. LogRecord attribute injection and collision | NO ISSUE | N/A | None |
| 2. Unset correlation sentinel | NO ISSUE | N/A | None |
| 3. Wire-level injection (pure internal) | NO ISSUE | N/A | None |
| 4. Filter return value always True | NO ISSUE | N/A | None |
| 5. ContextVar read without validation | MILD CONCERN | LOW | Optional: add _is_safe() check |
| 6. Filter attachment and lifecycle | NO ISSUE | N/A | None |
| 7. Thread-safety of LogRecord mutation | NO ISSUE | N/A | None |

---

## Overall Verdict

**PASS WITH OPTIONAL IMPROVEMENT**

The stdlib logging filter adapter is safe for production use. It correctly stamps the correlation ID onto LogRecords without modifying wire-level communication. The only minor concern is the lack of validation on the correlation ID value read from context, which could result in CRLF or null characters in log output.

---

## Recommended Actions

1. **Optional enhancement (non-blocking):** Add `_is_safe()` validation to the filter and strip or reject unsafe correlation IDs, for consistency with other adapters and to prevent malformed log output.

2. **Documentation:** Document that the filter does NOT validate the correlation ID; formatters should escape special characters. Add an example formatter that safely handles correlation_id attributes.

---

## Audit Conclusion

No security blockers. The adapter is safe for production use. The recommendation to add optional validation is for log hygiene and consistency, not for security.
