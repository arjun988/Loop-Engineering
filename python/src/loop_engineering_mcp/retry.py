"""Retry utilities with exponential backoff."""

import asyncio
from typing import Callable, TypeVar

T = TypeVar("T")


async def retry_async(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    retryable: Callable[[Exception], bool] | None = None,
) -> T:
    """Retry an async callable with exponential backoff."""
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = fn()
            if asyncio.iscoroutine(result):
                return await result
            return result
        except Exception as e:
            last_error = e
            if attempt == max_attempts:
                break
            if retryable and not retryable(e):
                raise
            delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
            await asyncio.sleep(delay)

    assert last_error is not None
    raise last_error
