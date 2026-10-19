# mixin_notifications Flow Trace

This trace follows the 0.7.0 modules:

- `mixin_notifications/events/_client.py` and `_objects.py`: event factory and frozen event type
- `mixin_notifications/dispatch/_client.py` and `_objects.py`: Dispatcher, egress gate, result type
- `mixin_notifications/suppression/_objects.py`: in-memory suppression tracker
- `mixin_notifications/backends/_client.py`: CollectingBackend, LoggingBackend, NullBackend, RetryingBackend
- `mixin_notifications/backends/sns.py`, `ses.py`, `aws_errors.py`: AWS backends and the shared error classifier

## Construction

1. `Dispatcher(backends=..., suppression_policy=...)` stores the backend tuple. When a suppression policy is given, a `SuppressionTracker` with the policy window is created.
2. `NotificationEventClient.create(...)` reads the correlation ID from mixin_logging, stamps `occurred_at` in UTC, converts a string severity to `Severity`, and returns a `NotificationEvent`. The event has no attachments unless they are added afterwards with `dataclasses.replace`.

## notify(event)

1. The time is read once for the call.
2. Suppression, if configured: when the (category, fingerprint) key was recorded inside the window, the call returns `DispatchResult(suppressed=True, results=())` and no backend runs.
3. Otherwise the key is recorded with the current time.
4. For each backend in order:
   - `_apply_egress_gate(event, backend)`:
     - `backend.external_egress` is False: the event is passed unchanged.
     - True: the event is replaced by a derived title (`"{category}: {severity} notification"`), a fixed body (`"[content redacted for external delivery]"`), a metadata tuple holding only `sensitive_count_metadata` with the number of original entries, and an attachment tuple containing only attachments with `egress_safe=True`.
   - `backend.send(egress_event)` runs. An exception is logged as a warning and recorded as a failed `DeliveryResult` with `retryable=True`. The loop continues with the next backend.
5. `DispatchResult(total_backends, results, suppressed=False)` is returned.

Because of step 4, an external backend never sees the original metadata. See the limitation in the README: a per-event `topic_arn` does not reach `SNSBackend` through `notify()`.

## RetryingBackend.send(event)

1. `RetryExecutor().call(attempt_send, policy=replace(policy, should_retry=...))` runs the inner backend.
2. A result with `retryable=True` is raised as an internal error; the retry predicate treats it as retryable. Other results are returned as they are.
3. When attempts run out:
   - a retryable result: the fallback detail reports exhaustion with the inner detail.
   - an exception that the predicate accepts: the same exhaustion detail with the exception class name.
   - any other exception: the non-retryable detail.
4. `_fallback` sends the event to `dead_letter` when one is set. If the dead-letter backend raises, a warning is logged and a failed result is returned. Without a dead letter, a failed result is returned.

`external_egress` of the wrapper is True when either the inner backend or the dead-letter backend is external.

## SNSBackend.send(event)

1. The topic is the default topic, unless a `topic_arn` metadata entry is present. Direct sends see that entry; sends through `Dispatcher.notify` do not, because of the egress gate.
2. `sns_client.publish(TopicArn, Subject=title, Message=body, MessageAttributes=...)` is called.
3. A response gives `DeliveryResult(delivered=True, detail="message_id: ...")`. An exception goes through `AwsErrorClassifier.failure`, which marks throttling, service-unavailable and internal errors as retryable.

## Output of a run

The fake-client run in the README shows both halves of the topic behaviour: the direct send uses `critical-alerts`, and the dispatched send uses the default topic.

## Invariants

- An `Exception` raised by a backend never propagates out of `notify()`.
- The egress gate runs before every external backend, on every dispatch.
- Suppression is checked before any backend runs.
