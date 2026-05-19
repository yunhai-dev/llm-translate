from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


TRANSIENT_ERROR_NAMES = {
    "APIConnectionError",
    "APITimeoutError",
    "InternalServerError",
    "RateLimitError",
    "TimeoutError",
}


def is_transient_error(error: Exception) -> bool:
    return error.__class__.__name__ in TRANSIENT_ERROR_NAMES


def retry_sync(
    operation: Callable[[], T],
    *,
    max_retries: int,
    initial_delay: float,
    max_delay: float,
) -> T:
    attempt = 0
    while True:
        try:
            return operation()
        except Exception as error:
            if attempt >= max_retries or not is_transient_error(error):
                raise
            delay = min(max_delay, initial_delay * (2**attempt))
            time.sleep(delay)
            attempt += 1


async def retry_async(
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    initial_delay: float,
    max_delay: float,
) -> T:
    attempt = 0
    while True:
        try:
            return await operation()
        except Exception as error:
            if attempt >= max_retries or not is_transient_error(error):
                raise
            delay = min(max_delay, initial_delay * (2**attempt))
            await asyncio.sleep(delay)
            attempt += 1
