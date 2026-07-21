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

## Documentation

- [Flow Trace](architecture/flow-trace.md) — Dispatch flow and architecture diagram
