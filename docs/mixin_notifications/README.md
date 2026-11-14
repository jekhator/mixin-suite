# mixin_notifications

Notification dispatch for Python services: a frozen event type, backends, a guarded dispatcher with suppression, and an egress gate for backends that send data outside the process. The core uses no third-party packages; it builds on the mixin_logging and mixin_retry roots of the same distribution.

**Key features:**

- **NotificationEvent**: frozen, slotted dataclass with category, severity, title, body, fingerprint, correlation_id, occurred_at, optional metadata and optional attachments.
- **NotificationBackend protocol**: built-in NullBackend, CollectingBackend and LoggingBackend; SNSBackend and SESBackend behind extras; RetryingBackend wraps any backend with retries and an optional dead-letter backend.
- **Dispatcher**: guarded dispatch to an explicit tuple of backends. A backend that raises does not stop the others; the failure is logged and reported in the result.
- **Suppression**: optional in-memory suppression on the (category, fingerprint) key within a time window.
- **Egress gate**: for backends with `external_egress=True`, the dispatcher replaces the title and body with fixed text, keeps only a count of metadata entries, and removes attachments that are not marked `egress_safe`.

## Installation

```bash
pip install mixin-suite
```

The AWS backends need boto3, installed by extras:

```bash
uv add "mixin-suite[sns]"
uv add "mixin-suite[ses]"
```

## Service-Class Example

The example below was executed with `uv run --all-extras python` on Python 3.14 against the 0.7.0 tree. The output is pasted from that run.

```python
from mixin_logging import clear_correlation_id, set_correlation_id
from mixin_notifications import (
    CollectingBackend,
    Dispatcher,
    NotificationEventClient,
    SuppressionPolicy,
)

set_correlation_id("example-correlation-123")

collecting_backend = CollectingBackend()
dispatcher = Dispatcher(
    backends=(collecting_backend,),
    suppression_policy=SuppressionPolicy(window_seconds=60),
)

event = NotificationEventClient.create(
    category="user_auth",
    severity="WARNING",
    title="Login Failed",
    body="User provided invalid credentials",
    fingerprint="login-failed-user-456",
)

result = dispatcher.notify(event)

print("Dispatch result:")
print(f"  Suppressed: {result.suppressed}")
print(f"  Total backends: {result.total_backends}")
print(f"  Delivery outcomes: {len(result.results)}")
print(f"  First result delivered: {result.results[0].delivered}")
print()
print("Collected event:")
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
    fingerprint="login-failed-user-456",
)

result2 = dispatcher.notify(event2)
print()
print("Second dispatch (same fingerprint within window):")
print(f"  Suppressed: {result2.suppressed}")
print(f"  Events in backend: {len(collecting_backend.events)}")

clear_correlation_id()
```

Output:

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

## Attachments

Attachments are a tuple on the event. `NotificationEventClient.create()` does not accept an `attachments` argument; build the event first and add the tuple with `dataclasses.replace`:

```python
from dataclasses import replace

from mixin_notifications import Attachment, CollectingBackend, Dispatcher, NotificationEventClient

collecting_backend = CollectingBackend()
dispatcher = Dispatcher(backends=(collecting_backend,))

event = NotificationEventClient.create(
    category="report",
    severity="INFO",
    title="Monthly Report Ready",
    body="Report is attached",
    fingerprint="monthly-report-2026-07",
)

attachment = Attachment(
    filename="report_2026_07.pdf",
    content_type="application/pdf",
    content=b"PDF binary data here...",
    egress_safe=True,
)
event_with_attachment = replace(event, attachments=(attachment,))

dispatcher.notify(event_with_attachment)

delivered = collecting_backend.events[0]
print(f"Event dispatched with {len(delivered.attachments)} attachment(s)")
print(f"Attachment filename: {delivered.attachments[0].filename}")
print(f"Attachment egress_safe: {delivered.attachments[0].egress_safe}")
```

Output:

```
Event dispatched with 1 attachment(s)
Attachment filename: report_2026_07.pdf
Attachment egress_safe: True
```

An attachment is forwarded to external backends only when `egress_safe=True`. Attachments with the default `egress_safe=False` are removed before an external backend sees the event. Internal backends receive all attachments.

## RetryingBackend

`RetryingBackend` wraps a backend with a `mixin_retry` `RetryPolicy`. A result with `retryable=True` is retried; when the attempts run out, the event goes to `dead_letter` if one is given. The script below shows a backend that recovers on its third attempt and one that exhausts its attempts and falls back to a dead-letter backend.

```python
from dataclasses import dataclass, field

from mixin_notifications import (
    CollectingBackend,
    DeliveryResult,
    Dispatcher,
    NotificationEvent,
    NotificationEventClient,
    RetryingBackend,
)
from mixin_retry import RetryPolicy


@dataclass
class FlakyBackend:
    failures_left: int
    attempts: list[int] = field(default_factory=list)

    @property
    def external_egress(self) -> bool:
        return False

    def send(self, event: NotificationEvent) -> DeliveryResult:
        self.attempts.append(len(self.attempts) + 1)
        if self.failures_left > 0:
            self.failures_left -= 1
            return DeliveryResult(
                delivered=False,
                backend_name="FlakyBackend",
                detail="throttled",
                retryable=True,
            )
        return DeliveryResult(delivered=True, backend_name="FlakyBackend", detail="ok", retryable=False)


policy = RetryPolicy(
    max_attempts=3,
    backoff_base_seconds=0.01,
    backoff_multiplier=2.0,
    backoff_max_seconds=0.05,
    jitter=False,
)
event = NotificationEventClient.create(
    category="alert",
    severity="CRITICAL",
    title="System Critical",
    body="System health critical",
    fingerprint="system-critical-001",
)

recovering = FlakyBackend(failures_left=2)
dispatcher = Dispatcher(backends=(RetryingBackend(inner=recovering, policy=policy),))
result = dispatcher.notify(event)
print("Recovering backend:")
print(f"  delivered: {result.results[0].delivered}")
print(f"  detail: {result.results[0].detail}")
print(f"  attempts: {len(recovering.attempts)}")

dead_letter = CollectingBackend()
failing = FlakyBackend(failures_left=10)
dispatcher = Dispatcher(
    backends=(RetryingBackend(inner=failing, policy=policy, dead_letter=dead_letter),)
)
result = dispatcher.notify(
    NotificationEventClient.create(
        category="alert",
        severity="CRITICAL",
        title="System Critical",
        body="System health critical",
        fingerprint="system-critical-002",
    )
)
print("Exhausted backend with dead letter:")
print(f"  delivered: {result.results[0].delivered}")
print(f"  backend_name: {result.results[0].backend_name}")
print(f"  detail: {result.results[0].detail}")
print(f"  attempts: {len(failing.attempts)}")
print(f"  dead-letter events: {len(dead_letter.events)}")
```

Output:

```
Recovering backend:
  delivered: True
  detail: ok
  attempts: 3
Exhausted backend with dead letter:
  delivered: True
  backend_name: RetryingBackend(dead_letter=CollectingBackend)
  detail: exhausted retries, dead_letter outcome: collected event system-critical-002
  attempts: 3
  dead-letter events: 1
```

## AWS Backends (SNS and SES)

`SNSBackend(sns_client=..., default_topic_arn=...)` publishes with the title as the subject, the body as the message, and category, severity, fingerprint and correlation_id as message attributes. A `topic_arn` entry in the event metadata overrides the default topic.

`SESBackend(ses_client=..., to_addresses=(...), from_address=...)` sends a MIME message through `send_raw_email`, including the attachments that passed the egress gate.

Both take an injected client, so tests and examples can use a fake. The example below uses a fake SNS client to show the topic override. It was executed on Python 3.14.

```python
from dataclasses import dataclass, field, replace

from mixin_notifications import Dispatcher, NotificationEventClient, SNSBackend


@dataclass
class FakeSNSClient:
    """Stands in for boto3.client("sns"); records each publish call."""

    calls: list[dict[str, object]] = field(default_factory=list)

    def publish(self, *, TopicArn, Subject, Message, MessageAttributes):
        self.calls.append({"TopicArn": TopicArn, "Subject": Subject})
        return {"MessageId": f"msg-{len(self.calls)}"}


sns_client = FakeSNSClient()
default_topic = "arn:aws:sns:us-east-1:123456789012:notifications"
critical_topic = "arn:aws:sns:us-east-1:123456789012:critical-alerts"

event = NotificationEventClient.create(
    category="alert",
    severity="CRITICAL",
    title="Alert",
    body="Pump pressure out of range",
    fingerprint="alert-001",
    metadata=(("topic_arn", critical_topic),),
)

backend = SNSBackend(sns_client=sns_client, default_topic_arn=default_topic)

direct = backend.send(event)
print("Direct send:")
print(f"  delivered: {direct.delivered}, detail: {direct.detail}")
print(f"  topic used: {sns_client.calls[-1]['TopicArn']}")

dispatcher = Dispatcher(backends=(backend,))
dispatched = dispatcher.notify(event)
print("Through Dispatcher (external_egress backend):")
print(f"  delivered: {dispatched.results[0].delivered}")
print(f"  topic used: {sns_client.calls[-1]['TopicArn']}")
```

Output:

```
Direct send:
  delivered: True, detail: message_id: msg-1
  topic used: arn:aws:sns:us-east-1:123456789012:critical-alerts
Through Dispatcher (external_egress backend):
  delivered: True
  topic used: arn:aws:sns:us-east-1:123456789012:notifications
```

### Limitation: metadata overrides through the egress gate

For backends with `external_egress=True`, `Dispatcher.notify` applies the egress gate before the backend sees the event. The gate replaces the metadata with a count of its entries (`sensitive_count_metadata`). A per-event `topic_arn` carried in metadata therefore does not reach `SNSBackend` through `Dispatcher.notify`, and the event goes to the default topic. The output above shows this.

Calling `SNSBackend.send` directly honours the override, as the first half of that run shows.

This is intended. The gate fails closed: metadata is not sent to an external service, so the topic override cannot be carried through it. To route per-event, call the backend directly or set the topic on the backend instance.

## Documentation

- [Flow Trace](architecture/flow-trace.md): dispatch flow and module map
- [Security Audit](audits/2026-07-29-0.6.0-delivery-security-audit.md): 0.6.0 delivery semantics audit
- [Architecture Review](reviews/2026-07-29-0.6.0-delivery-architecture-review.md): design and backward compatibility review
