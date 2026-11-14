# mixin_retry

Composable retry capability: exponential backoff with optional jitter, driven by a frozen `RetryPolicy` and a `RetryExecutor`. Works with sync functions and coroutines.

## Features

- `RetryPolicy` frozen dataclass: attempt limit, exponential backoff with a cap, jitter flag, and a retry predicate
- `RetryExecutor.wrap(fn, policy)` returns a wrapper that preserves the signature of `fn` (rebind once, call many)
- `RetryExecutor.call(fn, *args, policy=..., **kwargs)` runs one call with retry
- Supports sync functions and async functions (coroutines)
- Retry scope is either an exception-type tuple (`retry_on`) or a predicate (`should_retry`) that can unwrap `__cause__`

## Requirements

Python 3.12 or newer. The package has no runtime dependencies.

## Installation

mixin_retry ships in the mixin-suite distribution:

```
uv add mixin-suite
```

## RetryPolicy

```python
RetryPolicy(
    max_attempts: int,
    backoff_base_seconds: float,
    backoff_multiplier: float,
    backoff_max_seconds: float,
    jitter: bool,
    should_retry: Callable[[BaseException], bool] | None = None,
    retry_on: tuple[type[BaseException], ...] = (),
)
```

- `max_attempts`: total attempts, must be >= 1
- `backoff_base_seconds`: delay before the first retry, must be >= 0
- `backoff_multiplier`: growth factor per retry, must be > 0
- `backoff_max_seconds`: cap on any single delay, must be >= 0
- `jitter`: when True, each delay is multiplied by a random factor between 0.9 and 1.1
- `should_retry`: predicate that receives the caught exception and decides whether to retry. It takes precedence over `retry_on`.
- `retry_on`: exception types to retry on, used when `should_retry` is None. With neither set, nothing is retried.

## Backoff

After failed attempt n (0-indexed), the delay before the next attempt is:

- exponential: `backoff_base_seconds * backoff_multiplier ** n`
- capped: `min(exponential, backoff_max_seconds)`
- jittered (if enabled): capped delay times a uniform factor in [0.9, 1.1]

With `backoff_base_seconds=1.0`, `backoff_multiplier=2.0`, `backoff_max_seconds=60.0` and jitter off, the delays are 1, 2, 4, 8, ... seconds, never more than 60.

## Usage

### Wrap a method (rebind once, call many)

```python
from mixin_retry import RetryExecutor, RetryPolicy

policy = RetryPolicy(
    max_attempts=4,
    backoff_base_seconds=1.0,
    backoff_multiplier=2.0,
    backoff_max_seconds=60.0,
    jitter=True,
    retry_on=(IOError,),
)
executor = RetryExecutor()
fetch_item = executor.wrap(service.fetch_item, policy)
result = fetch_item(123)
```

### Per-call convenience

```python
result = executor.call(service.fetch_item, 123, policy=policy)
```

`call()` requires `policy`; calling it without one raises `ValueError`.

### Async callables

`wrap()` detects coroutine functions and returns an async wrapper that sleeps with `asyncio.sleep`:

```python
fetch = executor.wrap(async_fetch, policy)
body = await fetch("https://example.com")
```

## RUN-VERIFIED Example

The script below is the example used to check this page. It was executed with `uv run --all-extras python` on Python 3.14 against the 0.7.0 tree. The output is pasted from that run.

```python
import asyncio

from mixin_retry import RetryExecutor, RetryPolicy


class FlakyService:
    def __init__(self) -> None:
        self.attempts = 0

    def fetch_item(self, item_id: int) -> str:
        self.attempts += 1
        print(f"[Attempt {self.attempts}] Fetching item {item_id}...")
        if self.attempts < 3:
            raise IOError(f"Network timeout (attempt {self.attempts})")
        return f"Item#{item_id}:data=OK"


policy = RetryPolicy(
    max_attempts=4,
    backoff_base_seconds=0.01,
    backoff_multiplier=2.0,
    backoff_max_seconds=0.05,
    jitter=False,
    retry_on=(IOError,),
)
executor = RetryExecutor()

service = FlakyService()
fetch_item = executor.wrap(service.fetch_item, policy)
print("Result:", fetch_item(123))

service.attempts = 0
print("Per-call result:", executor.call(service.fetch_item, 456, policy=policy))

try:
    executor.call(service.fetch_item, 789)
except ValueError as error:
    print("Missing policy:", error)


def always_fails() -> None:
    raise IOError("permanent failure")


try:
    executor.wrap(always_fails, policy)()
except IOError as error:
    print("Exhausted after max_attempts:", error)


def unwrap_cause(error: BaseException) -> bool:
    cause = error.__cause__ or error
    return isinstance(cause, ConnectionError)


class Wrapped(Exception):
    pass


calls = {"count": 0}


def fails_with_wrapped_cause() -> str:
    calls["count"] += 1
    if calls["count"] < 2:
        try:
            raise ConnectionError("reset by peer")
        except ConnectionError as inner:
            raise Wrapped("request failed") from inner
    return "recovered"


predicate_policy = RetryPolicy(
    max_attempts=3,
    backoff_base_seconds=0.01,
    backoff_multiplier=1.0,
    backoff_max_seconds=0.01,
    jitter=False,
    should_retry=unwrap_cause,
)
print("Predicate result:", executor.call(fails_with_wrapped_cause, policy=predicate_policy))


async def fetch_async(url: str) -> str:
    calls_async["count"] += 1
    if calls_async["count"] < 2:
        raise TimeoutError("slow upstream")
    return f"fetched {url}"


calls_async = {"count": 0}
async_policy = RetryPolicy(
    max_attempts=3,
    backoff_base_seconds=0.01,
    backoff_multiplier=2.0,
    backoff_max_seconds=0.05,
    jitter=True,
    retry_on=(TimeoutError,),
)
print("Async result:", asyncio.run(executor.wrap(fetch_async, async_policy)("https://example.com")))
```

Output:

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

The first two runs show the flaky method succeeding on its third attempt, with the delays kept short by a 0.01 second base. The missing-policy call fails before any attempt is made. The exhausted run re-raises the last `IOError` after four attempts. The predicate run retries because the wrapped `ConnectionError` is found through `__cause__`.

## Exceptions

- Retries only on the exception types selected by `should_retry` or `retry_on`
- `BaseException`-only types such as `KeyboardInterrupt`, `SystemExit` and `asyncio.CancelledError` are retried only when the policy names them explicitly (through `should_retry` or `retry_on`)
- After the last attempt, the original exception is re-raised unchanged

## See Also

- Architecture and flow trace: [architecture/flow-trace.md](architecture/flow-trace.md)
- Repository: https://github.com/jekhator/mixin-suite
