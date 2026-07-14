# mixin_retry Flow Trace

## Architecture Overview

mixin_retry/decorators/retried/retried_client.py (+ RetryContainer, constants)
═══════════════════════════════════════════════════════════════════════════════
Imports: functools, time, asyncio, random, inspect; dataclass RetryContainer
┌─ [DATACLASS,frozen,slots] RetryContainer ──────────┐ max_attempts: int ; base_delay_s: float ; max_delay_s: float ; jitter: bool └─...
┌─ [CLASS,slots] RetryClient ──────────┐ container: RetryContainer ; retry_on: callable ; __call__[mth] ; _wrap_callable[mth] ; _execute_sync[mth] ; _execute_async[mth] ; _calculate_delay[mth] ; _decorate_class[mth] └─...

## FLOW TRACE

i CONSTRUCT  retried(max_attempts=4, base_delay_s=0.1, max_delay_s=0.5, jitter=True)
      └─ RetryContainer(max_attempts=4, base_delay_s=0.1, ...)
      └─ RetryClient(container=..., retry_on=_default_retry_on)
      └─ return RetryClient (acts as decorator callable)

ii DECORATE   @retried(...) on a class

    a. CLASS path (target is a class):
       ├─ __call__(target=MyService)
       ├─ inspect.isclass(target) → True ──▶ _decorate_class(target)
       │     └─ for name, value in cls.__dict__.items():
       │           ├─ _should_skip_member(name, value)
       │           │     ├─ name.startswith("_") → True ──▶ skip
       │           │     ├─ isinstance(value, property) → True ──▶ skip
       │           │     └─ inspect.isclass(value) → True ──▶ skip
       │           ├─ hasattr(value, "__retried_decorated__") ──▶ skip if already wrapped
       │           ├─ isinstance(value, classmethod):
       │           │     ├─ wrapped = _wrap_callable(value.__func__, for_static_or_class=True)
       │           │     ├─ setattr(cls, name, classmethod(wrapped))
       │           │     └─ setattr(wrapped, "__retried_decorated__", True)
       │           ├─ isinstance(value, staticmethod):
       │           │     ├─ wrapped = _wrap_callable(value.__func__, for_static_or_class=True)
       │           │     ├─ setattr(cls, name, staticmethod(wrapped))
       │           │     └─ setattr(wrapped, "__retried_decorated__", True)
       │           └─ callable(value) ── instance methods:
       │                 ├─ wrapped = _wrap_callable(value)  ← no for_static_or_class
       │                 ├─ setattr(cls, name, wrapped)
       │                 └─ setattr(wrapped, "__retried_decorated__", True)
       └─ return target (class now has wrapped methods)

    b. CALLABLE path (target is a single function):
       ├─ __call__(target=some_func)
       ├─ callable(target) → True ──▶ _wrap_callable(target)
       └─ return wrapper

iii CALL-TIME (instance method example)

     a. Instance method with retries (for_static_or_class=False):
        ├─ service.fetch_item(123) ──▶ wrapper(instance=service, item_id=123)
        │     └─ _execute_sync(fetch_item, service, item_id=123)
        │           ├─ for attempt in range(4):  ← max_attempts=4
        │           │     ├─ attempt=0:
        │           │     │     ├─ try: return fetch_item(service, 123)
        │           │     │     │           raises IOError("Network timeout")
        │           │     │     └─ except BaseException as exc:
        │           │     │           ├─ _should_retry_exception(exc) → True
        │           │     │           ├─ retry_on(IOError) → True (default)
        │           │     │           ├─ attempt < max_attempts-1 → True (0 < 3)
        │           │     │           ├─ delay = _calculate_delay(0)
        │           │     │           │     ├─ exponential = 0.1 * (2 ** 0) = 0.1
        │           │     │           │     ├─ capped = min(0.1, 0.5) = 0.1
        │           │     │           │     └─ jittered = random.uniform(0, 0.1)
        │           │     │           └─ time.sleep(jittered)
        │           │     ├─ attempt=1:
        │           │     │     ├─ try: return fetch_item(service, 123)
        │           │     │     │           raises IOError("Network timeout")
        │           │     │     └─ except: [same as above]
        │           │     │           ├─ delay = _calculate_delay(1)
        │           │     │           │     ├─ exponential = 0.1 * (2 ** 1) = 0.2
        │           │     │           │     ├─ capped = min(0.2, 0.5) = 0.2
        │           │     │           │     └─ jittered = random.uniform(0, 0.2)
        │           │     │           └─ time.sleep(jittered)
        │           │     └─ attempt=2:
        │           │           ├─ try: return fetch_item(service, 123)
        │           │           │           returns "Item#123:data=OK"
        │           │           └─ return result
        └─ returns "Item#123:data=OK"

     b. Async method with retries (for_static_or_class=False, is_coroutine=True):
        ├─ await service.fetch_async() ──▶ async_wrapper(instance=service)
        │     └─ _execute_async(fetch_async, service)
        │           ├─ for attempt in range(max_attempts):
        │           │     ├─ attempt=0:
        │           │     │     ├─ try: return await fetch_async(service)
        │           │     │     │           raises IOError
        │           │     │     └─ except: [retry logic]
        │           │     │           ├─ delay = _calculate_delay(0)
        │           │     │           └─ await asyncio.sleep(delay)
        │           │     └─ [more attempts...]
        └─ returns awaited result

     c. Classmethod with retries (for_static_or_class=True):
        ├─ MyService.create() ──▶ static_wrapper(...)
        │     └─ _execute_sync(create, ...)
        │           ├─ [retry loop as above]
        └─ returns created instance

## REAL RUN OUTPUT

Example output from actual execution (Python 3.11.15):

```
=== mixin_retry RUN-VERIFIED EXAMPLE ===

Test 1: Decorator on service method with exponential backoff

[Attempt 1] Fetching item 123...
[Attempt 2] Fetching item 123...
[Attempt 3] Fetching item 123...
Result: Item#123:data=OK

Test 2: Decorator on service method without jitter

Result: cached_item_42

Test 3: Exhausted retries after max_attempts

[Attempt 1]
[Attempt 2]
Failed after max_attempts: Permanent error
```

Key observations:

- Decorator wraps methods and preserves their behavior (function signature, return type)
- Retry loop executes synchronously (time.sleep) or asynchronously (asyncio.sleep)
- Each failed attempt checks: _should_retry_exception → retry_on predicate → attempt limit
- _calculate_delay applies exponential backoff with optional jitter
- After max_attempts exhausted, final exception is re-raised (never swallowed)
- Class decoration fan-out wraps instance methods, classmethods, and staticmethods individually
- Private methods and properties are skipped during class decoration
- setattr(wrapper, "__retried_decorated__", True) marks methods to prevent double wrapping
