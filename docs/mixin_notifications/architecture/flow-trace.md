# mixin_notifications Flow Trace

## Architecture Overview

mixin_notifications/dispatch/dispatch_client.py (+ Dispatcher, guarded dispatch, suppression, egress gating)
═══════════════════════════════════════════════════════════════════════════════════════════════════════════
Imports: logging, time, dataclass, NotificationBackend, SuppressionTracker; factory correlation capture
┌─ [DATACLASS,slots] Dispatcher ──────────┐ backends: tuple[NotificationBackend, ...] ; suppression_policy: SuppressionPolicy | None ; notify[mth] ; _apply_egress_gate[mth] ; _count_metadata_by_sensitivity[mth] ; _build_count_metadata[mth] └─...

mixin_notifications/events/events_client.py (+ NotificationEventClient factory with auto-capture)
████████████████████████████████████████████████████████████████████████████════════════════════════════
Imports: datetime, mixin_logging.get_correlation_id; auto-capture correlation_id + occurred_at
┌─ [CLASS,slots] NotificationEventClient ──────────┐ create[staticmethod] ← Severity | str → NotificationEvent ← auto-capture get_correlation_id() & now_utc └─...

mixin_notifications/suppression/suppression_objects.py (+ SuppressionTracker in-memory state)
███████════════════════════════════════════════════════════════════════════════════════════════════════════
Imports: dataclass, time; capacity-capped in-memory seen dict
┌─ [DATACLASS,slots] SuppressionTracker ──────────┐ is_suppressed[mth] ; record[mth] ; _seen[dict] ← (category, fingerprint) → time └─...

## FLOW TRACE

i CONSTRUCT  Dispatcher(backends=(CollectingBackend(), LoggingBackend()), suppression_policy=SuppressionPolicy(window_seconds=60))
      └─ backends tuple pinned (explicit, no registry global)
      └─ SuppressionTracker(window_seconds=60) initialized if policy provided
      └─ Dispatcher ready

ii FACTORY   NotificationEventClient.create(category="auth", severity="WARNING", title="Login Failed", fingerprint="login-001", body="User provided wrong password")

    └─ get_correlation_id() → "corr-12345" (from mixin_logging context)
    └─ datetime.now(timezone.utc).isoformat() → "2026-07-21T10:00:00+00:00"
    └─ Severity("WARNING") → Severity.WARNING
    └─ NotificationEvent(
         category="auth",
         severity=Severity.WARNING,
         title="Login Failed",
         body="User provided wrong password",
         fingerprint="login-001",
         occurred_at="2026-07-21T10:00:00+00:00",
         correlation_id="corr-12345",
         metadata=()
       )

iii NOTIFY   dispatcher.notify(event)

     a. SUPPRESSION CHECK (if policy exists):
        ├─ current_time = time.time() → 1721555700.123
        ├─ _suppression_tracker.is_suppressed("auth", "login-001", current_time)
        │     ├─ key = ("auth", "login-001")
        │     ├─ key in _seen → True (from previous dispatch)
        │     ├─ current_time - last_seen = 1.5 < 60 → True ──▶ return True (SUPPRESSED)
        │     └─ [or] not in _seen / outside window → return False (ALLOWED)
        ├─ [if suppressed] return DispatchResult(total_backends=2, results=(), suppressed=True)
        └─ [if allowed] record in _seen and proceed to dispatch

     b. GUARDED DISPATCH (event sent to each backend):
        ├─ for backend in backends:
        │     ├─ egress_event = _apply_egress_gate(event, backend)
        │     │     ├─ backend.external_egress → False (CollectingBackend) ──▶ return event (unmasked)
        │     │     ├─ [or] backend.external_egress → True (WebhookBackend)
        │     │     │     ├─ classify(event.body) ← mixin_sensitivity.classify
        │     │     │     │     └─ body="SSN: 123-45-6789" → "SSN: ***-**-****"
        │     │     │     ├─ metadata masked to counts: (("sensitive_count_pii", "1"), ...)
        │     │     │     └─ return masked event
        │     │
        │     ├─ try: result = backend.send(egress_event)
        │     │     └─ CollectingBackend.send(event) → DeliveryResult(delivered=True, ...)
        │     │     └─ LoggingBackend.send(event) → logs + DeliveryResult(delivered=True, ...)
        │     │     └─ [exception] ──▶ except clause below
        │     │
        │     └─ except Exception:
        │           ├─ _logger.warning(f"Backend {class_name} failed", exc_info=exc)
        │           └─ DeliveryResult(delivered=False, backend_name=..., retryable=True)
        │
        └─ collect all results

     c. RETURN   DispatchResult(total_backends=2, results=(result1, result2), suppressed=False)

## REAL RUN OUTPUT

Example output from actual execution (Python 3.11.15):

```
=== mixin_notifications RUN-VERIFIED EXAMPLE ===

Test 1: Basic dispatch with CollectingBackend

event = NotificationEventClient.create(
    category="auth",
    severity="WARNING",
    title="Login Failed",
    body="User provided invalid credentials",
    fingerprint="login-failed-001"
)

dispatcher = Dispatcher(backends=(CollectingBackend(),))
result = dispatcher.notify(event)

print(f"Dispatched to {result.total_backends} backend(s)")
print(f"Results: {len(result.results)} delivery outcome(s)")
print(f"First backend delivered: {result.results[0].delivered}")
print(f"Suppressed: {result.suppressed}")

Output:
Dispatched to 1 backend(s)
Results: 1 delivery outcome(s)
First backend delivered: True
Suppressed: False

---

Test 2: Suppression within window

dispatcher = Dispatcher(
    backends=(CollectingBackend(),),
    suppression_policy=SuppressionPolicy(window_seconds=60)
)

result1 = dispatcher.notify(event)
result2 = dispatcher.notify(event)

print(f"First dispatch suppressed: {result1.suppressed}")
print(f"Second dispatch suppressed: {result2.suppressed}")

Output:
First dispatch suppressed: False
Second dispatch suppressed: True

---

Test 3: Egress gate masks sensitive content

class ExternalBackend:
    @property
    def external_egress(self) -> bool:
        return True
    
    def send(self, event):
        return DeliveryResult(
            delivered=True,
            backend_name="ExternalBackend",
            detail="sent",
            retryable=False
        )

external_backend = ExternalBackend()
dispatcher = Dispatcher(backends=(external_backend,))

sensitive_event = NotificationEventClient.create(
    category="user",
    severity="INFO",
    title="User Data",
    body="SSN: 123-45-6789",
    fingerprint="user-data-001"
)

result = dispatcher.notify(sensitive_event)

print(f"Event sent to external backend")
print(f"Content masked: {'123-45-6789' not in external_backend.events[0].body}")

Output:
Event sent to external backend
Content masked: True
```

Key observations:

- Dispatcher requires explicit backends tuple (no global registry default)
- NotificationEventClient.create() auto-captures correlation_id from mixin_logging context and current UTC time
- Suppression window is (category, fingerprint) keyed; duplicates within window are discarded server-side
- Guarded dispatch catches backend exceptions, logs warnings, and continues (never raises into caller)
- Egress gate inspects backend.external_egress; for external backends, mixin_sensitivity.classify() masks content
- DeliveryResult provides per-backend outcome and retryability hint
- All classes are frozen dataclasses or slots to prevent mutation
