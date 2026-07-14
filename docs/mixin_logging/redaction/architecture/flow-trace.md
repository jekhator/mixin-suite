# mixin_logging Redaction Filter Flow Trace

## Architecture Overview

mixin_logging/redaction/redaction_client.py + redaction_objects.py (+ constants)
═══════════════════════════════════════════════════════════════════════════════
Imports: logging, frozenset, dataclass
┌─ [DATACLASS,frozen,slots] RedactionFilter(logging.Filter) ──────────┐ sensitive_patterns: frozenset[str] ; filter[mth] ; _redact_record[mth] ; _is_sensitive_field_name[mth] └─...
┌─ [DATACLASS,frozen,slots] RedactionClient ──────────┐ classifier: ClassifyClient ; attach[mth] ; with_default_classifier[cls_mth] └─...

## FLOW TRACE

i INITIALIZE  RedactionClient.with_defaults()
      └─ RedactionFilter(sensitive_patterns=frozenset([
             "password", "secret", "api_key", "token",
             "auth", "credential", "key"
         ]))
      └─ return RedactionFilter instance

ii ATTACH     RedactionClient.attach_default(logger)
      └─ redaction_filter = RedactionFilter.with_defaults()
      └─ logger.addFilter(redaction_filter)  ← stdlib logging integration

iii CALL-TIME (LogRecord emission)

     a. Logger method call:
        ├─ logger.info("User login", extra={"api_key": "sk_live_secret", "user_id": "123"})
        │     └─ logging.Logger._log() creates LogRecord
        │           ├─ record.name = "myapp"
        │           ├─ record.msg = "User login"
        │           ├─ record.api_key = "sk_live_secret"  ← from extra dict
        │           ├─ record.user_id = "123"  ← from extra dict
        │           └─ record.__dict__ = {name, msg, api_key, user_id, ...}

     b. Filter execution (before handler.emit):
        ├─ for each filter in logger.filters:
        │     ├─ filter.filter(record) ──▶ RedactionFilter.filter(record)
        │     │     └─ _redact_record(record)
        │     │           ├─ if hasattr(record, "__dict__"):
        │     │           │     └─ for key in list(record.__dict__.keys()):
        │     │           │           ├─ if key.startswith("_"):
        │     │           │           │     continue  ← skip private attrs
        │     │           │           ├─ if _is_sensitive_field_name("api_key"):
        │     │           │           │     ├─ name_lower = "api_key"
        │     │           │           │     ├─ "api_key" in "api_key" → True
        │     │           │           │     └─ record.__dict__["api_key"] = "***REDACTED***"
        │     │           │           └─ if _is_sensitive_field_name("user_id"):
        │     │           │                 ├─ name_lower = "user_id"
        │     │           │                 ├─ "password"|"secret"|"api_key"|... in "user_id" → False
        │     │           │                 └─ no redaction
        │     │     └─ return True  ← always allow record emission
        │     └─ continue to next filter

     c. Handler emission (after all filters):
        ├─ handler.emit(record)
        │     ├─ record.api_key = "***REDACTED***"  ← already redacted
        │     ├─ record.user_id = "123"  ← unchanged
        │     └─ formatter formats and prints

## Pattern Matching

The _is_sensitive_field_name method uses substring matching (case-insensitive):

```
name_lower = name.lower()
return any(pattern in name_lower for pattern in self.sensitive_patterns)
```

Examples:

- "api_key" matches pattern "api_key" ──▶ REDACTED
- "API_KEY" matches pattern "api_key" (case-insensitive) ──▶ REDACTED
- "api_key_v2" matches pattern "api_key" (substring) ──▶ REDACTED
- "token" matches pattern "token" ──▶ REDACTED
- "refresh_token" matches pattern "token" (substring) ──▶ REDACTED
- "user_id" does NOT match any pattern ──▶ NOT REDACTED
- "request_id" does NOT match any pattern ──▶ NOT REDACTED

## REAL RUN OUTPUT

Example output from actual execution (Python 3.11.15):

Without redaction filter:

```
=== LOG OUTPUT WITHOUT REDACTION FILTER ===

myapp - INFO - User login attempt | api_key=sk_live_abc123xyz789secret | user_id=user_123 | action=login
```

With redaction filter:

```
=== LOG OUTPUT WITH REDACTION FILTER ===

myapp_redacted - INFO - User login attempt | api_key=***REDACTED*** | user_id=user_123 | action=login
```

Sensitive field name redaction:

```
=== SENSITIVE FIELD NAME REDACTION ===

myapp_redacted - INFO - Request processed | request_id=req_abc123 | password=***REDACTED*** | token=***REDACTED*** | duration_ms=245
```

Key observations:

- RedactionFilter.filter() is called once per LogRecord (before handler.emit)
- Only field values whose names match sensitive patterns are replaced with "***REDACTED***"
- Private attributes (_name, _levelno, etc.) are skipped and never redacted
- Non-matching field names (user_id, request_id, duration_ms) pass through unchanged
- Numeric values (duration_ms=245) are preserved
- Redaction happens in-place on the LogRecord.__dict__
- Once filter returns True, the LogRecord proceeds to handlers (never filtered out)
- Multiple filters stack (each calls filter(), results chain)
