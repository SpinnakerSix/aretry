# async-retry

Lightweight retry decorator for sync and async Python functions. Zero dependencies.

`invl/retry` — the most popular Python retry library — gets 8M+ weekly downloads but hasn't
shipped a release since 2018 and has no async support. This is the modern replacement.

## Install

```
pip install async-retry
```

## Usage

```python
from aretry import retry

# Works on sync functions
@retry(times=3, on=requests.Timeout, backoff=2.0)
def fetch():
    return requests.get(url, timeout=5)

# Works on async functions — same decorator, no changes needed
@retry(times=3, on=aiohttp.ClientError, backoff=2.0, jitter=True)
async def fetch_async():
    async with session.get(url) as r:
        return await r.json()

# @retry with no parens uses all defaults (3 attempts, 1s delay, 2x backoff)
@retry
def simple():
    ...
```

## Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `times` | `3` | Total attempts (1 = try once, no retry) |
| `on` | `Exception` | Exception type or tuple of types to catch |
| `delay` | `1.0` | Initial wait in seconds before first retry |
| `backoff` | `2.0` | Multiply delay by this after each attempt |
| `jitter` | `False` | Add ±20% random noise to avoid thundering herd |
| `before_retry` | `None` | Callback `(exc, attempt, delay)` called before each retry |

## Backoff example

With `times=4, delay=1.0, backoff=2.0`:

| Attempt | Wait before next |
|---------|-----------------|
| 1 (fail) | 1s |
| 2 (fail) | 2s |
| 3 (fail) | 4s |
| 4 (fail) | raises `RetryExhausted` |

## Error handling

```python
from aretry import RetryExhausted

try:
    fetch()
except RetryExhausted as e:
    print(f"Gave up after {e.attempts} attempts. Last error: {e.last_exc}")
```

`RetryExhausted` is a subclass of `Exception`. The original exception is also accessible
via standard `__cause__` chaining.

## License

MIT
