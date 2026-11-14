# mixin_retry Flow Trace

This trace follows the code in `mixin_retry/executor.py` and `mixin_retry/policy.py` as shipped in 0.7.0.

## Components

```
RetryPolicy (frozen, slots dataclass; policy.py)
  fields: max_attempts, backoff_base_seconds, backoff_multiplier,
          backoff_max_seconds, jitter, should_retry, retry_on
  __post_init__: validates the bounds above

RetryExecutor (executor.py)
  wrap(operation, policy)      -> sync wrapper or async wrapper
  _wrap_sync / _wrap_async     -> retry loops
  call(operation, *a, policy)  -> wrap() then invoke once
  _should_retry(error, policy) -> predicate, else retry_on, else False
  _calculate_backoff(n, policy)-> capped exponential, optional jitter
```

## Construction

1. `RetryPolicy(...)` runs `__post_init__`. Invalid bounds raise `ValueError` with the messages in `common/constants/errors.py`.
2. `RetryExecutor()` holds no state. One executor can wrap many callables.

## wrap() on a sync function

1. `inspect.iscoroutinefunction(operation)` is False, so `_wrap_sync` builds the wrapper with `functools.wraps`.
2. Each call to the wrapper runs the loop `for attempt in range(max_attempts - 1)`:
   - `operation(*args, **kwargs)` returns: the result is returned to the caller.
   - It raises: `_should_retry(error, policy)` is checked. False re-raises the original exception.
   - True: `time.sleep(_calculate_backoff(attempt, policy))`, then the loop continues.
3. After the loop, one direct call `operation(*args, **kwargs)` runs. Its exception, if any, propagates unchanged.

So a policy with `max_attempts=4` makes at most four calls: three guarded calls and one final unguarded call.

## wrap() on a coroutine function

Same loop as above, using `await operation(...)` and `await asyncio.sleep(...)`.

## _should_retry

1. If `policy.should_retry` is set, its return value decides. The predicate receives the exception as raised and handles any `__cause__` unwrapping itself.
2. Otherwise, if `policy.retry_on` is non-empty, `isinstance(error, retry_on)` decides.
3. Otherwise the answer is False, so the exception propagates on the first failure.

## _calculate_backoff

1. `exponential = backoff_base_seconds * backoff_multiplier ** attempt`. If the power overflows float range, the result is treated as infinity when the base is positive and as 0.0 when it is zero.
2. `backoff = min(exponential, backoff_max_seconds)`.
3. If `jitter` is True, `backoff *= random.uniform(0.9, 1.1)`.

## call()

1. `policy is None` raises `ValueError("policy is required for call()")`.
2. Otherwise `wrap(operation, policy)` is built and invoked once with the given arguments.

## REAL RUN OUTPUT

The output below is from running the README example (`uv run --all-extras python` on Python 3.14, 0.7.0 tree). The script is embedded in the README.

```
[Attempt 1] Fetching item 123...
[Attempt 2] Fetching item 123...
[Attempt 3] Fetching item 123...
Result: Item#123:data=OK
[Attempt 1] Fetching item 456...
[Attempt 2] Fetching item 456...
[Attempt 3] Fetching item 456...
Per-call result: Item#456:data=OK
Missing policy: policy is required for call()
Exhausted after max_attempts: permanent failure
Predicate result: recovered
Async result: fetched https://example.com
```

## Invariants

- The attempt count never exceeds `max_attempts`.
- The exception that finally reaches the caller is the original one.
- Retry decisions are made per exception, after the call that raised it.
