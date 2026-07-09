# logging-mixin. Cloud Adapter

> **Location:** `logging-mixin/docs/apps/adapters/cloud.md`
> **Status:** Implemented. Inbound AWS-event correlation adapter for serverless and event-driven Lambda entry points. Updated 2026-06-04.
> **Code location:** `mixin_logging/adapters/cloud/` (`cloud_objects.py` + `cloud_client.py`); constants in `mixin_logging/adapters/constants/cloud.py`.
> **Diagrams:** `docs/apps/adapters/diagrams.md` (Adapter Categories & Data Flow).
> **Sibling docs:** `docs/apps/adapters/asgi.md`, `docs/apps/adapters/botocore.md`, `docs/apps/context/correlation.md`.

## Purpose

The **cloud adapter** is the **inbound AWS-event correlation adapter** for serverless and event-driven entry points. It extracts a correlation ID from incoming cloud events (Lambda via API Gateway/ALB, SQS, SNS, EventBridge) or generates one as a fallback, then sets it into context at the handler boundary for downstream services and logging to inherit. It is the inbound counterpart to ASGI/WSGI middleware :  extracting from cloud event dicts instead of HTTP environ/scope, but following the same container pattern and uuid4-fallback strategy.

## Category

Inbound Ingress, the same category as the ASGI and WSGI adapters, specialized for AWS serverless Lambda handlers rather than HTTP frameworks.

## Behavior

- `CloudSetup.setup_correlation_id(event, context)` is called at the top of a Lambda handler to extract a correlation ID from the event, set it into context, and return it (for optional response header injection).
- Multi-source extraction follows precedence: API Gateway/ALB headers → SQS message attributes → SNS message attributes → EventBridge detail → direct top-level key → generate uuid4.
- `CloudCorrelation.from_event(event)` performs the extraction, validating safety and falling back to uuid4 hex[:12] (first 12 hex chars) whenever extraction fails or the value is unsafe.
- The extracted correlation ID is set into context via `set_correlation_id()` for all downstream services and loggers to inherit via `ContextVar`.

## Value Object

`CloudCorrelation` (frozen, slots) captures the resolved `correlation_id`:

- `from_event(cls, event)`. Class method. Extract correlation ID from the event dict following AWS-source precedence order; validate safety; generate uuid4 hex[:12] if extraction fails. Returns `CloudCorrelation(correlation_id=..., extracted=extracted_bool)` where `extracted` tracks provenance (True if from event, False if generated).
- `__post_init__()`. Validate `correlation_id` is non-empty, within length cap (≤128 characters), and free of control characters (`\r\n\0`). Raise `ValueError` if unsafe.
- `_is_safe(value)`. Static method. Return `True` if value is non-empty, within length cap, and free of unsafe header characters; else `False`.

## Multi-Source Extraction

`CloudCorrelation.from_event(event)` inspects the incoming cloud event dict in **precedence order**, falling back to generate uuid4 hex[:12] when no valid source is found:

1. **API Gateway / ALB (HTTP)** :  `event["headers"]["X-Correlation-ID"]` (case-insensitive header lookup)
2. **SQS** :  `event["Records"][0]["messageAttributes"]["X-Correlation-ID"]["stringValue"]` (first record only)
3. **SNS** :  `event["Records"][0]["Sns"]["MessageAttributes"]["X-Correlation-ID"]["Value"]` (first record only)
4. **EventBridge** :  `event["detail"]["correlation_id"]` (detail object)
5. **Direct invoke / Step Functions** :  `event["correlation_id"]` (top level)
6. **Fallback** :  Generate `uuid4().hex[:12]` if no valid source is found or all extracted values fail validation

Validation rejects empty values, values exceeding 128 characters, values containing control characters (`\r`, `\n`, `\0`), and invalid UTF-8 encoding. If validation fails on any source, the adapter automatically falls back to uuid4 generation.

## Setup Surface

`CloudSetup` is a simple setup class (frozen, slots) with one method:

- `setup_correlation_id(event, context)`. Static method. Extract correlation ID via `CloudCorrelation.from_event(event)`, set it into context via `set_correlation_id()`, and return the correlation_id string (for optional response header injection). The `context` parameter is included to match the Lambda handler signature, though unused for extraction.

## Constants

`mixin_logging/adapters/constants/cloud.py`:

- `CORRELATION_ID_HEADER = "X-Correlation-ID"` (matches inbound ASGI/WSGI headers for round-trip consistency)
- `CORRELATION_ID_KEY = "correlation_id"` (for EventBridge detail + top-level direct-invoke field)
- `CORRELATION_ID_MAX_LENGTH = 128`
- `GENERATED_ID_LENGTH = 12`
- `UNSAFE_HEADER_CHARS = frozenset({"\r", "\n", "\0"})`
- `ERR_CORRELATION_ID_UNSAFE = "correlation_id must be non-empty, within length cap, free of unsafe chars"`

## Design Note

The cloud adapter extracts from plain event dicts (AWS Lambda event payloads as specified in AWS documentation) rather than HTTP protocol objects. Lambda receives one event type per invocation (not mixed), so extraction precedence is a safety measure for flexibility. The multi-source extractor handles the most common AWS event shapes (API Gateway, SQS, SNS, EventBridge); other triggers (S3, DynamoDB, etc.) fall through to uuid4 generation without special handling.

All generated correlation IDs use uuid4 hex[:12] (first 12 hex chars) to match the ASGI/WSGI adapters and keep correlation IDs short (12 chars) but collision-resistant (uuid4 hex is 128 bits / ~6.2 bits per char = ~72 bits of entropy in 12 chars, sufficient for request-scoped uniqueness).

## Compatibility

AWS Lambda (any trigger type: HTTP via API Gateway/ALB, SQS, SNS, EventBridge, direct invoke, Step Functions). No extra imports required; operates on standard Python dicts.

## Example Usage

```python
from mixin_logging.adapters.cloud.cloud_client import CloudSetup

def lambda_handler(event, context):
    correlation_id = CloudSetup.setup_correlation_id(event, context)
    
    # Application code (services, loggers) inherit correlation_id via ContextVar
    svc = MyService()
    result = svc.process(event)
    
    # Optional: inject correlation_id into HTTP response headers
    return {
        "statusCode": 200,
        "headers": {"X-Correlation-ID": correlation_id},
        "body": json.dumps(result)
    }
```

For SQS or other async triggers (no HTTP response):

```python
from mixin_logging.adapters.cloud.cloud_client import CloudSetup

def sqs_handler(event, context):
    correlation_id = CloudSetup.setup_correlation_id(event, context)
    
    svc = MyService()
    for record in event["Records"]:
        svc.process_message(record)
```

Every downstream call (boto3, httpx, requests, Celery, logging) inherits the correlation_id via `ContextVar` and propagates it (inbound adapters set it; stdlib logging filter stamps it into logs; outbound adapters inject it into headers/metadata).

## Lifecycle

1. **Entry:** `CloudSetup.setup_correlation_id(event, context)` extracts and sets correlation ID into context.
2. **Execution:** Downstream code (services, logging, outbound adapters) reads correlation ID from `ContextVar`.
3. **Exit:** Context is implicitly cleared when Lambda execution scope ends (no explicit cleanup needed; ContextVar is function-scoped).
4. **Response (HTTP only):** Correlation ID returned to caller via response headers.

## See Also

- **Inbound adapters overview / ASGI/WSGI siblings:** `docs/apps/adapters/asgi.md`
- **Outbound adapters:** `docs/apps/adapters/botocore.md`, `docs/apps/adapters/httpx.md`, `docs/apps/adapters/requests.md`
- **Cross-boundary adapter:** `docs/apps/adapters/celery.md`
- **Output sink / stdlib logging filter:** `docs/apps/adapters/stdlib.md`
- **Correlation context & ContextVar internals:** `docs/apps/context/correlation.md`
- **Adapter diagrams (categories & data flow):** `docs/apps/adapters/diagrams.md`
