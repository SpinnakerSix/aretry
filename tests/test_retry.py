from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from aretry import RetryExhausted, retry


# --- Sync ---

class TestSyncRetry:
    def test_succeeds_first_attempt(self):
        calls = []

        @retry
        def fn():
            calls.append(1)
            return "ok"

        assert fn() == "ok"
        assert len(calls) == 1

    def test_succeeds_on_nth_attempt(self):
        calls = []

        @retry(times=3, delay=0)
        def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "ok"

        with patch("time.sleep"):
            assert fn() == "ok"
        assert len(calls) == 3

    def test_exhausts_all_retries(self):
        @retry(times=3, delay=0)
        def fn():
            raise RuntimeError("always fails")

        with patch("time.sleep"), pytest.raises(RetryExhausted) as exc_info:
            fn()

        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exc, RuntimeError)

    def test_retry_exhausted_is_exception(self):
        @retry(times=2, delay=0)
        def fn():
            raise ValueError("x")

        with patch("time.sleep"), pytest.raises(Exception):
            fn()

    def test_only_retries_on_matched_exception(self):
        calls = []

        @retry(times=3, on=ValueError, delay=0)
        def fn():
            calls.append(1)
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            fn()

        assert len(calls) == 1  # no retries

    def test_retries_on_tuple_of_exceptions(self):
        calls = []

        @retry(times=3, on=(ValueError, IOError), delay=0)
        def fn():
            calls.append(1)
            if len(calls) == 1:
                raise ValueError("first")
            raise IOError("second")

        with patch("time.sleep"), pytest.raises(RetryExhausted):
            fn()

        assert len(calls) == 3

    def test_exponential_backoff(self):
        @retry(times=3, delay=1.0, backoff=2.0)
        def fn():
            raise ValueError("fail")

        with patch("time.sleep") as mock_sleep, pytest.raises(RetryExhausted):
            fn()

        assert mock_sleep.call_args_list == [call(1.0), call(2.0)]

    def test_times_one_means_no_retry(self):
        calls = []

        @retry(times=1)
        def fn():
            calls.append(1)
            raise ValueError("fail")

        with pytest.raises(RetryExhausted):
            fn()

        assert len(calls) == 1

    def test_times_zero_raises_at_decoration(self):
        with pytest.raises(ValueError):
            @retry(times=0)
            def fn():
                pass

    def test_before_retry_hook_called(self):
        hook = MagicMock()

        @retry(times=3, delay=0, before_retry=hook)
        def fn():
            raise ValueError("fail")

        with patch("time.sleep"), pytest.raises(RetryExhausted):
            fn()

        assert hook.call_count == 2  # before attempt 2 and 3, not after final failure

    def test_before_retry_receives_exc_attempt_delay(self):
        received = []

        def hook(exc, attempt, delay):
            received.append((type(exc), attempt, delay))

        @retry(times=3, delay=1.0, backoff=2.0, before_retry=hook)
        def fn():
            raise ValueError("x")

        with patch("time.sleep"), pytest.raises(RetryExhausted):
            fn()

        assert received[0] == (ValueError, 1, 1.0)
        assert received[1] == (ValueError, 2, 2.0)

    def test_preserves_function_metadata(self):
        @retry
        def my_function():
            """My docstring."""

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_passes_args_and_kwargs(self):
        @retry
        def fn(a, b, *, c=0):
            return a + b + c

        assert fn(1, 2, c=3) == 6

    def test_jitter_stays_within_range(self):
        delays = []

        def hook(exc, attempt, delay):
            delays.append(delay)

        @retry(times=4, delay=1.0, backoff=1.0, jitter=True, before_retry=hook)
        def fn():
            raise ValueError()

        with patch("time.sleep"), pytest.raises(RetryExhausted):
            fn()

        for d in delays:
            assert 0.8 <= d <= 1.2


# --- Async ---

class TestAsyncRetry:
    @pytest.mark.asyncio
    async def test_succeeds_first_attempt(self):
        @retry
        async def fn():
            return "ok"

        assert await fn() == "ok"

    @pytest.mark.asyncio
    async def test_succeeds_on_nth_attempt(self):
        calls = []

        @retry(times=3, delay=0)
        async def fn():
            calls.append(1)
            if len(calls) < 3:
                raise ValueError("not yet")
            return "done"

        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await fn()

        assert result == "done"
        assert len(calls) == 3

    @pytest.mark.asyncio
    async def test_exhausts_all_retries(self):
        @retry(times=3, delay=0)
        async def fn():
            raise RuntimeError("always fails")

        with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(RetryExhausted) as exc_info:
            await fn()

        assert exc_info.value.attempts == 3
        assert isinstance(exc_info.value.last_exc, RuntimeError)

    @pytest.mark.asyncio
    async def test_only_retries_matched_exception(self):
        calls = []

        @retry(times=3, on=ValueError, delay=0)
        async def fn():
            calls.append(1)
            raise TypeError("nope")

        with pytest.raises(TypeError):
            await fn()

        assert len(calls) == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff(self):
        @retry(times=3, delay=1.0, backoff=2.0)
        async def fn():
            raise ValueError()

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep, pytest.raises(RetryExhausted):
            await fn()

        assert mock_sleep.call_args_list == [call(1.0), call(2.0)]

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        @retry
        async def my_async_fn():
            """Async docstring."""

        assert my_async_fn.__name__ == "my_async_fn"
        assert my_async_fn.__doc__ == "Async docstring."
