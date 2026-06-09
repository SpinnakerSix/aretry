from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import random
import time
from collections.abc import Callable
from typing import Any

log = logging.getLogger(__name__)


class RetryExhausted(Exception):
    """Raised when all retry attempts are exhausted. `last_exc` holds the final failure."""

    def __init__(self, attempts: int, last_exc: BaseException) -> None:
        self.attempts = attempts
        self.last_exc = last_exc
        super().__init__(f"Failed after {attempts} attempt(s): {last_exc}")
        self.__cause__ = last_exc


def retry(
    fn: Callable | None = None,
    *,
    times: int = 3,
    on: type[BaseException] | tuple[type[BaseException], ...] = Exception,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: bool = False,
    before_retry: Callable[[BaseException, int, float], None] | None = None,
) -> Callable:
    """Retry decorator for sync and async functions. Zero dependencies.

    Args:
        times:        Total attempts (1 = try once, no retry). Default 3.
        on:           Exception type or tuple of types to catch. Default Exception.
        delay:        Initial wait in seconds before first retry. Default 1.0.
        backoff:      Multiply delay by this after each attempt. Default 2.0.
        jitter:       Add +-20% random noise to delay to avoid thundering herd.
        before_retry: Optional callback(exc, attempt, delay) called before each retry.

    Usage:
        @retry
        def fetch(): ...

        @retry(times=5, on=(Timeout, ConnectionError), backoff=1.5, jitter=True)
        async def fetch_async(): ...
    """
    if times < 1:
        raise ValueError(f"times must be >= 1, got {times!r}")

    def decorator(func: Callable) -> Callable:
        if inspect.iscoroutinefunction(func):
            @functools.wraps(func)
            async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                current_delay = delay
                last_exc: BaseException | None = None
                for attempt in range(1, times + 1):
                    try:
                        return await func(*args, **kwargs)
                    except on as exc:
                        last_exc = exc
                        if attempt == times:
                            break
                        sleep = current_delay * (random.uniform(0.8, 1.2) if jitter else 1.0)
                        log.warning(
                            "%s: attempt %d/%d failed (%s), retrying in %.2fs",
                            func.__qualname__, attempt, times, exc, sleep,
                        )
                        if before_retry is not None:
                            before_retry(exc, attempt, sleep)
                        await asyncio.sleep(sleep)
                        current_delay *= backoff
                raise RetryExhausted(times, last_exc)
            return async_wrapper
        else:
            @functools.wraps(func)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                current_delay = delay
                last_exc: BaseException | None = None
                for attempt in range(1, times + 1):
                    try:
                        return func(*args, **kwargs)
                    except on as exc:
                        last_exc = exc
                        if attempt == times:
                            break
                        sleep = current_delay * (random.uniform(0.8, 1.2) if jitter else 1.0)
                        log.warning(
                            "%s: attempt %d/%d failed (%s), retrying in %.2fs",
                            func.__qualname__, attempt, times, exc, sleep,
                        )
                        if before_retry is not None:
                            before_retry(exc, attempt, sleep)
                        time.sleep(sleep)
                        current_delay *= backoff
                raise RetryExhausted(times, last_exc)
            return sync_wrapper

    # Support @retry without parentheses
    if fn is not None:
        return decorator(fn)
    return decorator
