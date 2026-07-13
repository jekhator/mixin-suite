# mixin-suite

**Composable Python mixins for production services:** structured logging with automatic correlation-ID propagation, and sensitive-data classification and masking for frozen dataclasses.

[![PyPI version](https://img.shields.io/pypi/v/mixin-suite.svg)](https://pypi.org/project/mixin-suite/)
[![CI](https://github.com/jekhator/mixin-suite/actions/workflows/ci.yml/badge.svg)](https://github.com/jekhator/mixin-suite/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](LICENSE)
[![Python Versions](https://img.shields.io/pypi/pyversions/mixin-suite.svg)](https://pypi.org/project/mixin-suite/)

This distribution consolidates two concern-specific packages:

- **mixin-logging** (v0.6.0): End-to-end correlation-ID propagation across 14 adapters for distributed systems
- **mixin-sensitivity** (v0.4.0): Decorator-based sensitivity classification and masking for frozen dataclasses

Both packages retain their original import roots (`mixin_logging`, `mixin_sensitivity`) and can be used independently or together.

## What They Do

### Logging: Correlation-ID Propagation

Track a single request through a distributed system with automatic correlation-ID injection on every log, HTTP call, database query, and background task.

**Before:**
```python
class OrderService:
    def create_order(self, order_id: int):
        print(f"Creating order {order_id}")  # No correlation tracking
        send_notification(order_id)  # Loses request context
```

**After:**
```python
from mixin_logging import LoggingMixin, set_correlation_id

set_correlation_id("req-123")

class OrderService(LoggingMixin):
    def create_order(self, order_id: int):
        self.log_info("order.create", order_id=order_id)
        # Logs with: {"correlation_id": "req-123", "order_id": 123, ...}
        send_notification(order_id)  # Correlation ID propagates automatically
```

### Sensitivity: Prevent Accidental Secret Leaks

Mark sensitive fields in dataclasses once, and they auto-mask in logs, reprs, and tracebacks.

**Before:**
```python
from dataclasses import dataclass

@dataclass(frozen=True)
class APICredentials:
    user_id: int
    api_token: str

creds = APICredentials(user_id=1, api_token="sk-abc123xyz")
logger.info("Creds: %s", creds)  # LEAKED: api_token exposed
```

**After:**
```python
from dataclasses import dataclass, field
from mixin_sensitivity import sensitive, classify

@sensitive
@dataclass(frozen=True, slots=True)
class APICredentials:
    user_id: int
    api_token: str = field(metadata={"sensitivity": "secret"})

creds = APICredentials(user_id=1, api_token="sk-abc123xyz")
logger.info("Creds: %s", creds)  # SAFE: repr shows "api_token=***"
```

## Installation

**Base installation:**
```bash
pip install mixin-suite
```

or with uv:
```bash
uv add mixin-suite
```

**With optional extras for logging adapters:**

Base package includes `mixin_logging` (stdlib adapter only) and `mixin_sensitivity` (no dependencies).

Optional extras (mixin_logging adapters):
- `[aiohttp]`: aiohttp client instrumentation
- `[botocore]`: AWS SDK instrumentation
- `[celery]`: Celery task propagation
- `[fastapi]`: FastAPI middleware and dependencies
- `[grpc]`: gRPC server instrumentation
- `[httpx]`: HTTPX client instrumentation
- `[requests]`: Requests client instrumentation
- `[urllib3]`: urllib3 client instrumentation
- `[all]`: All adapters

Install with extras:
```bash
uv add "mixin-suite[httpx,botocore]"  # Multiple extras
uv add "mixin-suite[all]"             # All adapters
```

**Python version:** Requires Python 3.11 or later (3.11 and 3.12 tested).

## Quick Start

### Logging with Correlation IDs

#### 1. Add stdlib adapter to your logging config

```python
import logging
from mixin_logging.adapters.stdlib.stdlib_client import CorrelationLogFilter

logging.basicConfig()
logging.getLogger().addFilter(CorrelationLogFilter())
```

#### 2. Install FastAPI adapter and add middleware

For FastAPI applications:

```python
from fastapi import FastAPI
from mixin_logging.adapters.fastapi import CorrelationIdMiddleware

app = FastAPI()
app.add_middleware(CorrelationIdMiddleware)
```

Or manually for other frameworks:

```python
from mixin_logging import set_correlation_id
from fastapi import Request

@app.middleware("http")
async def correlation_middleware(request: Request, call_next):
    set_correlation_id(request.headers.get("x-correlation-id", "auto-gen"))
    return await call_next(request)
```

#### 3. Use LoggingMixin in your classes

```python
from mixin_logging import LoggingMixin

class UserService(LoggingMixin):
    def create_user(self, user_name: str):
        self.log_info("user.create", user_name=user_name)
        # Logs include correlation_id automatically
```

### Sensitivity: Masking Sensitive Fields

#### 1. Decorate and mark sensitive fields

```python
from dataclasses import dataclass, field
from mixin_sensitivity import sensitive, Sensitivity

@sensitive
@dataclass(frozen=True, slots=True)
class User:
    id: int
    api_token: str = field(metadata={"sensitivity": "secret"})
    email: str = field(metadata={"sensitivity": "pii"})
    ssn: str = field(metadata={"sensitivity": "phi"})
    name: str
```

#### 2. Use in your code

```python
user = User(
    id=1,
    api_token="sk-123456",
    email="alice@example.com",
    ssn="123-45-6789",
    name="Alice"
)

# Safe for logging
logger.info("User created: %s", repr(user))
# → "User created: User(id=1, api_token='***', email='***', ssn='***', name='Alice')"

# Introspect sensitivity profile
from mixin_sensitivity import classify
profile = classify(user)
# → SensitivityProfile(classes=(
#     ('api_token', Sensitivity.SECRET),
#     ('email', Sensitivity.PII),
#     ('ssn', Sensitivity.PHI),
# ))
```

## Run-Verified Examples

These examples are executed against the published mixin-suite==0.1.1 distribution.

### Logging Example: Correlation-ID Propagation

```python
import logging
from mixin_logging import LoggingMixin, logged, set_correlation_id

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s - correlation_id=%(correlation_id)s",
)


class DocumentService(LoggingMixin):
    """Service that processes documents with correlation-ID tracking."""

    @logged("document.upload")
    def upload(self, doc_name: str, size_bytes: int) -> dict:
        """Upload a document and return metadata."""
        self.log_info("upload.initiated", doc_name=doc_name, size_bytes=size_bytes)
        result = {"id": "doc-123", "doc_name": doc_name, "stored": True}
        self.log_info("upload.complete", doc_id=result["id"])
        return result

    @logged("document.process")
    def process(self, doc_id: str) -> str:
        """Process a document and return status."""
        self.log_info("process.started", doc_id=doc_id)
        status = "processed"
        self.log_info("process.finished", doc_id=doc_id, status=status)
        return status


# Execute with correlation context
set_correlation_id("req-2026-07-10-001")
service = DocumentService()
result = service.upload("report.pdf", 1024000)
status = service.process("doc-123")
```

**Output (Python 3.12, mixin-suite==0.1.1):**
```
2026-07-10 03:05:20,405 - __main__.DocumentService - INFO - document.upload.start - correlation_id=req-2026-07-10-001
2026-07-10 03:05:20,405 - __main__.DocumentService - INFO - upload.initiated - correlation_id=req-2026-07-10-001
2026-07-10 03:05:20,405 - __main__.DocumentService - INFO - upload.complete - correlation_id=req-2026-07-10-001
2026-07-10 03:05:20,405 - __main__.DocumentService - INFO - document.process.start - correlation_id=req-2026-07-10-001
2026-07-10 03:05:20,405 - __main__.DocumentService - INFO - process.started - correlation_id=req-2026-07-10-001
2026-07-10 03:05:20,405 - __main__.DocumentService - INFO - process.finished - correlation_id=req-2026-07-10-001
```

### Sensitivity Example: Data Masking

```python
from dataclasses import dataclass, field
from mixin_sensitivity import sensitive, classify, Sensitivity

@sensitive
@dataclass(frozen=True, slots=True)
class HealthRecord:
    patient_id: int
    ssn: str = field(metadata={"sensitivity": "phi"})
    diagnosis: str = field(metadata={"sensitivity": "phi"})
    treatment_notes: str = field(metadata={"sensitivity": "phi"})
    attending_physician: str

record = HealthRecord(
    patient_id=42,
    ssn="987-65-4321",
    diagnosis="Type 2 Diabetes",
    treatment_notes="Prescribed Metformin 500mg",
    attending_physician="Dr. Smith"
)

# Safe repr
print(repr(record))

# Introspect profile
profile = classify(record)
print(f"PHI fields: {[f for f, s in profile.classes if s == Sensitivity.PHI]}")
```

**Output (Python 3.12, mixin-suite==0.1.1):**
```
HealthRecord(patient_id=42, ssn=***, diagnosis=***, treatment_notes=***, attending_physician='Dr. Smith')

PHI fields: ['ssn', 'diagnosis', 'treatment_notes']
```

## Documentation

- **Logging:** See `docs/mixin_logging/` for detailed adapter documentation, architecture, and integration patterns
- **Sensitivity:** See `docs/mixin_sensitivity/` for classifier API, masking customization, and examples
- **Historical Changelogs:** See `docs/mixin_logging/CHANGELOG-history.md` and `docs/mixin_sensitivity/CHANGELOG-history.md`

## Public API

### mixin_logging (v0.6.0)

Core classes and functions:
- `LoggingMixin`: Base class providing `log_info()`, `log_debug()`, and `@logged` support
- `logged(event_name)`: Decorator for automatic event logging and error handling
- `set_correlation_id(id)`: Set the correlation ID for the current context
- `get_correlation_id()`: Retrieve the current correlation ID
- `clear_correlation_id()`: Clear the correlation ID from context
- `CorrelationContext`: Data class representing correlation metadata
- `ContextVarClient`: Internal context-variable manager for correlation propagation
- `LoggedClient`, `LoggedContainer`: Internal decorator implementation details
- `PUBLIC_API`: Frozenset of all public names

### mixin_sensitivity (v0.4.0)

Core classes and functions:
- `sensitive`: Class decorator enabling automatic masking of sensitive fields
- `classify(dataclass_or_instance)`: Introspect sensitivity profile of a dataclass
- `Sensitivity`: Enum taxonomy: PHI, PII, PCI, SECRET
- `SensitivityProfile`: Data class containing field-to-sensitivity mappings

## Imports

Both packages maintain their original import roots:

```python
# Logging
from mixin_logging import LoggingMixin, logged, set_correlation_id, get_correlation_id

# Sensitivity
from mixin_sensitivity import sensitive, classify, Sensitivity
```

## Contributing

This is a read-only consolidation of two independently-maintained packages. Bug reports and feature requests should be filed in the respective package repositories:

- mixin-logging issues: https://github.com/jekhator/mixin-logging/issues
- mixin-sensitivity issues: https://github.com/jekhator/mixin-sensitivity/issues

## License

Licensed under the Apache License 2.0. See `LICENSE` for details.
