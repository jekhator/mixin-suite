# mixin_notifications

Cross-cutting notification dispatch abstraction for Python services. Framework-agnostic, zero-dependencies core (stdlib only).

**Key features:**

- **NotificationEvent**: Immutable dataclass (frozen+slots) with category, severity, title, body, fingerprint, correlation_id, occurred_at, and optional metadata.
- **NotificationBackend protocol**: Extensible interface for backends (built-in: NullBackend, CollectingBackend, LoggingBackend; consumers implement DB/Slack/webhook/email).
- **Dispatcher**: Guarded dispatch to explicit tuple of backends. One backend failure does not raise; all exceptions logged as warnings.
- **Suppression**: Optional in-memory suppression on (category, fingerprint) key within a configurable window.
- **Egress gate**: Automatically masks sensitive content (via mixin_sensitivity) when sending to backends marked with `external_egress=True`.

## Installation

```bash
pip install mixin-suite
```

## Service-Class Example

Run-verified example using Dispatcher + CollectingBackend + suppression:

```python
from mixin_notifications import (
    CollectingBackend,
    Dispatcher,
    NotificationEventClient,
    SuppressionPolicy,
)
from mixin_logging import set_correlation_id, clear_correlation_id

set_correlation_id("example-correlation-123")

collecting_backend = CollectingBackend()
dispatcher = Dispatcher(
    backends=(collecting_backend,),
    suppression_policy=SuppressionPolicy(window_seconds=60)
)

event = NotificationEventClient.create(
    category="user_auth",
    severity="WARNING",
    title="Login Failed",
    body="User provided invalid credentials",
    fingerprint="login-failed-user-456"
)

result = dispatcher.notify(event)

print(f"Dispatch result:")
print(f"  Suppressed: {result.suppressed}")
print(f"  Total backends: {result.total_backends}")
print(f"  Delivery outcomes: {len(result.results)}")
print(f"  First result delivered: {result.results[0].delivered}")
print()
print(f"Collected event:")
print(f"  Category: {collecting_backend.events[0].category}")
print(f"  Severity: {collecting_backend.events[0].severity}")
print(f"  Title: {collecting_backend.events[0].title}")
print(f"  Fingerprint: {collecting_backend.events[0].fingerprint}")
print(f"  Correlation ID: {collecting_backend.events[0].correlation_id}")

event2 = NotificationEventClient.create(
    category="user_auth",
    severity="WARNING",
    title="Login Failed Again",
    body="Same user provided invalid credentials again",
    fingerprint="login-failed-user-456"
)

result2 = dispatcher.notify(event2)
print()
print(f"Second dispatch (same fingerprint within window):")
print(f"  Suppressed: {result2.suppressed}")
print(f"  Events in backend: {len(collecting_backend.events)}")

clear_correlation_id()
```

**Output:**

```
Dispatch result:
  Suppressed: False
  Total backends: 1
  Delivery outcomes: 1
  First result delivered: True

Collected event:
  Category: user_auth
  Severity: WARNING
  Title: Login Failed
  Fingerprint: login-failed-user-456
  Correlation ID: example-correlation-123

Second dispatch (same fingerprint within window):
  Suppressed: True
  Events in backend: 1
```

## 0.6.0+ Features: Delivery Semantics & Attachment Support

### Attachments

Attach binary payloads to notifications with egress-safe marking:

```python
from mixin_notifications import Attachment, CollectingBackend, Dispatcher, NotificationEventClient

collecting_backend = CollectingBackend()
dispatcher = Dispatcher(backends=(collecting_backend,))

event = NotificationEventClient.create(
    category="report",
    severity="INFO",
    title="Monthly Report Ready",
    body="Report is attached",
    fingerprint="monthly-report-2026-07"
)

event_with_attachment = NotificationEventClient.create(
    category="report",
    severity="INFO",
    title="Monthly Report Ready",
    body="Report is attached",
    fingerprint="monthly-report-2026-07",
    attachments=(
        Attachment(
            filename="report_2026_07.pdf",
            content_type="application/pdf",
            content=b"PDF binary data here...",
            egress_safe=True
        ),
    )
)

result = dispatcher.notify(event_with_attachment)

print(f"Event dispatched with {len(collecting_backend.events[0].attachments)} attachment(s)")
print(f"Attachment filename: {collecting_backend.events[0].attachments[0].filename}")
print(f"Attachment egress_safe: {collecting_backend.events[0].attachments[0].egress_safe}")
```

**Output:**

```
Event dispatched with 1 attachment(s)
Attachment filename: report_2026_07.pdf
Attachment egress_safe: True
```

**Note:** `egress_safe=True` allows attachments to pass through external backends (e.g., SNS, email). Unmarked attachments (default `egress_safe=False`) are stripped when sending to external backends.

### RetryingBackend (optional, requires mixin_retry)

Wrap any backend with exponential backoff retry logic and optional dead-letter fallback:

```python
from mixin_notifications import (
    CollectingBackend,
    Dispatcher,
    NotificationEventClient,
    RetryingBackend,
)
from mixin_retry import RetryPolicy

# This example is illustrative; in production, integrate with SNSBackend or SESBackend
collecting_backend = CollectingBackend()
dlq_backend = CollectingBackend()

retry_policy = RetryPolicy(
    max_attempts=3,
    backoff_base_seconds=0.5,
    backoff_multiplier=2,
    backoff_max_seconds=30,
    jitter=True
)

retrying_backend = RetryingBackend(
    inner=collecting_backend,
    policy=retry_policy,
    dead_letter=dlq_backend
)

dispatcher = Dispatcher(backends=(retrying_backend,))

event = NotificationEventClient.create(
    category="alert",
    severity="CRITICAL",
    title="System Critical",
    body="System health critical",
    fingerprint="system-critical-001"
)

result = dispatcher.notify(event)

print(f"Event delivered: {result.results[0].delivered}")
print(f"Backend name: {result.results[0].backend_name}")
print(f"Events in collecting backend: {len(collecting_backend.events)}")
print(f"Dead-letter queue: {len(dlq_backend.events)} events")
```

**Output:**

```
Event delivered: True
Backend name: CollectingBackend
Events in collecting backend: 1
Dead-letter queue: 0 events
```

**SNS/SES Backends (optional, requires boto3)**

For AWS integration, use SNSBackend (with topic override via metadata) or SESBackend (with MIME attachments):

```python
# SNSBackend example (requires boto3, [sns] extra)
# backend = SNSBackend(
#     sns_client=boto3.client("sns"),
#     default_topic_arn="arn:aws:sns:us-east-1:123456789012:notifications"
# )
#
# # Per-event topic override:
# event = NotificationEventClient.create(
#     category="alert",
#     severity="CRITICAL",
#     title="Alert",
#     body="...",
#     fingerprint="...",
#     metadata=(("topic_arn", "arn:aws:sns:us-east-1:123456789012:critical-alerts"),)
# )

# SESBackend example (requires boto3, [ses] extra)
# backend = SESBackend(
#     ses_client=boto3.client("ses"),
#     to_addresses=("ops@example.com",),
#     from_address="alerts@example.com"
# )
```

## Documentation

- [Flow Trace](architecture/flow-trace.md): Dispatch flow and architecture diagram
- [Security Audit](audits/2026-07-29-0.6.0-delivery-security-audit.md): 0.6.0 delivery semantics audit
- [Architecture Review](reviews/2026-07-29-0.6.0-delivery-architecture-review.md): Design and backward compatibility review
