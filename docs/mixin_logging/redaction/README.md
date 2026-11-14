# mixin_logging Redaction Filter

Logging filter that masks sensitive field names to prevent accidental exposure of secrets and credentials in logs. Attach to any logger to automatically redact fields with sensitive names.

## Features

- Masks values of fields whose names match sensitive patterns
- Works with stdlib logging.Filter interface (compatible with all loggers)
- Configurable sensitive field name patterns
- Skips private attributes (names starting with _)
- Preserves non-sensitive fields and numeric values
- Zero-impact integration (just attach to logger)

## What It Does

The redaction filter examines every LogRecord and masks the value of any field whose name matches a sensitive pattern. Common patterns include: password, secret, api_key, token, auth, credential, key.

Example: If you log with extra={"api_key": "sk_live_abc123"}, the filter will replace that value with "***REDACTED***" before emission.

## Installation

Base mixin-suite includes redaction filter:

```
uv add mixin-suite
```

## Quick Start

### Attach to a Logger

```python
import logging
from mixin_logging.redaction import RedactionClient

logger = logging.getLogger("myapp")

RedactionClient.attach_default(logger)

logger.info("User login", extra={"api_key": "sk_live_secret", "user_id": "123"})
```

Output:

```
myapp - INFO - User login | api_key=***REDACTED*** | user_id=123
```

Only the api_key value was masked because "api_key" matches a sensitive field name pattern.

### Custom Sensitive Patterns

```python
from mixin_logging.redaction import RedactionFilter

patterns = frozenset(["password", "api_key", "token", "custom_secret"])
filter_obj = RedactionFilter(sensitive_patterns=patterns)

logger.addFilter(filter_obj)
```

## Run-Verified Example

This example was executed on Python 3.14 with `uv run --all-extras python`:

```python
import logging

from mixin_logging.redaction import RedactionClient

FIELDS = ("api_key", "user_id", "password", "token", "request_id", "duration_ms")


class ExtrasFormatter(logging.Formatter):
    def format(self, record):
        extras = " | ".join(f"{name}={getattr(record, name)}" for name in FIELDS if hasattr(record, name))
        return f"{record.name} - {record.levelname} - {record.getMessage()} | {extras}"


def make_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(ExtrasFormatter())
    logger.addHandler(handler)
    return logger


plain = make_logger("myapp")
plain.info("User login attempt", extra={"api_key": "sk_live_abc123xyz789secret", "user_id": "user_123", "action": "login"})

redacted = make_logger("myapp_redacted")
RedactionClient.attach_default(redacted)
redacted.info("User login attempt", extra={"api_key": "sk_live_abc123xyz789secret", "user_id": "user_123", "action": "login"})
redacted.info("Request processed", extra={"request_id": "req_abc123", "password": "mySecurePassword123", "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", "duration_ms": 245})
```

Output:

```
```

The api_key, password and token values are masked; user_id, request_id and duration_ms remain visible because their field names are not sensitive patterns.

## Default Sensitive Patterns

The default filter recognizes these field names (case-insensitive substring match):

- password
- secret
- api_key
- token
- auth
- credential
- key

## Behavior Details

### Masking

- Applies to any LogRecord extra field whose name contains a sensitive pattern (substring match, case-insensitive)
- Value is replaced with "***REDACTED***" constant
- Only string and non-string values in extra dict are checked
- Private attributes (names starting with _) are skipped

### Integration Points

The filter integrates with:

- Any stdlib logging.Logger (via addFilter)
- Any custom handler or formatter
- Both synchronous and asynchronous logging
- Third-party libraries that use Python logging

### Non-Redacted Fields

- Logger standard fields (name, levelname, message, pathname, etc.) are unchanged
- Private attributes starting with _ are not modified
- Non-string field values (numbers, objects) pass through unchanged
- Field names that do not match sensitive patterns are unchanged

## See Also

- Architecture and flow trace: docs/mixin_logging/redaction/architecture/flow-trace.md
- Correlation ID propagation: mixin_logging.adapters.stdlib.CorrelationLogFilter
- mixin-suite: https://github.com/jekhator/mixin-suite
