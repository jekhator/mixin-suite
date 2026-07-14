# mixin_retry

Composable decorator for exponential backoff retry with full jitter. Apply @retried to functions, methods, or entire classes to automatically retry on transient failures.

## Features

- Exponential backoff with configurable base delay and maximum delay cap
- Full jitter to prevent thundering herd in distributed systems
- Custom retry predicate to decide which exceptions trigger retry
- Works on functions, methods, classmethods, staticmethods, and classes
- Supports both sync and async (coroutines and async methods)

## Installation

Base mixin-suite includes mixin_retry:

```
uv add mixin-suite
```

Or as a standalone:

```
uv add mixin-retry
```

## Quick Start

### Decorator on a Service Method

```python
from mixin_retry import retried

class MyService:
    @retried(max_attempts=4, base_delay_s=1.0, max_delay_s=60.0, jitter=True)
    def fetch_item(self, item_id: int) -> str:
        """Fetches an item; automatically retries with exponential backoff."""
        result = api_call(item_id)  # May raise IOError on network timeout
        return result
```

### Decorator on a Function

```python
@retried(max_attempts=3, base_delay_s=0.5, retry_on=lambda e: isinstance(e, IOError))
def unreliable_operation():
    """Retry only on IOError."""
    return perform_operation()
```

### Decorator on a Class

```python
@retried(max_attempts=5)
class DataFetcher:
    """All public methods in the class get automatic retry."""

    def fetch(self, url: str) -> str:
        return requests.get(url).text

    def parse(self, data: str) -> dict:
        return json.loads(data)

    @staticmethod
    def validate(obj: dict) -> bool:
        return "id" in obj
```

## Parameters

- max_attempts (int, default 3): Maximum number of attempts (must be >= 1)
- base_delay_s (float, default 1.0): Base delay in seconds for exponential backoff
- max_delay_s (float, default 60.0): Maximum delay in seconds (capped backoff)
- jitter (bool, default True): Enable full jitter to randomize backoff
- retry_on (callable, optional): Predicate function(exception) -> bool. Default retries on any Exception (not BaseException)

## Backoff Strategy

On each failed attempt n (0-indexed):

- Exponential: base_delay_s * (2 ** n)
- Capped: min(exponential, max_delay_s)
- Jittered (if enabled): random.uniform(0, capped)

Example with base_delay_s=1.0, max_delay_s=60.0, jitter=True:

- Attempt 0: Fails, delay = random(0, 1s)
- Attempt 1: Fails, delay = random(0, 2s)
- Attempt 2: Fails, delay = random(0, 4s)
- Attempt 3: Succeeds, no further delay

## RUN-VERIFIED Example

This example was executed with Python 3.11.15:

```
uv run python your_script.py
```

### Service Class with Retry

```python
from mixin_retry import retried

class MyService:
    attempt_count = 0

    @retried(max_attempts=4, base_delay_s=0.1, max_delay_s=0.5, jitter=True)
    def fetch_item(self, item_id: int) -> str:
        self.attempt_count += 1
        print(f"[Attempt {self.attempt_count}] Fetching item {item_id}...")

        if self.attempt_count < 3:
            raise IOError(f"Network timeout (attempt {self.attempt_count})")

        return f"Item#{item_id}:data=OK"
```

Output:

```
[Attempt 1] Fetching item 123...
[Attempt 2] Fetching item 123...
[Attempt 3] Fetching item 123...
Result: Item#123:data=OK
```

Explanation: The decorator automatically retried twice after network failures before succeeding on the third attempt.

## Behavior Details

### Exceptions Handled

- Retries on Exception and its subclasses
- Never retries on BaseException-only types: KeyboardInterrupt, SystemExit, asyncio.CancelledError
- Custom retry_on predicate can narrow or widen retry scope

### Class Decoration

When decorating a class, @retried wraps all public methods:

- Instance methods: self._logger bound per instance
- Classmethods and staticmethods: module-level logger fallback
- Methods starting with _ (private) are skipped
- Properties and nested classes are skipped
- Methods already decorated with @retried are skipped to avoid double wrapping

### Async Support

Both sync and async callables are supported. The decorator detects coroutine functions and wraps them with asyncio.sleep instead of time.sleep.

```python
import asyncio

class AsyncService:
    @retried(max_attempts=3)
    async def fetch_async(self, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                return await resp.text()

await service.fetch_async("https://example.com")
```

## See Also

- Architecture and flow trace: docs/mixin_retry/architecture/flow-trace.md
- mixin-suite: https://github.com/jekhator/mixin-suite
