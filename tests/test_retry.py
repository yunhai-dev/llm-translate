from __future__ import annotations

import asyncio

import pytest

from llm_translate.retry import retry_async, retry_sync


class RateLimitError(Exception):
    pass


def test_retry_sync_retries_transient_errors() -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RateLimitError("slow down")
        return "ok"

    assert retry_sync(operation, max_retries=3, initial_delay=0, max_delay=0) == "ok"
    assert attempts == 3


def test_retry_sync_does_not_retry_non_transient_errors() -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise ValueError("bad input")

    with pytest.raises(ValueError):
        retry_sync(operation, max_retries=3, initial_delay=0, max_delay=0)
    assert attempts == 1


def test_retry_sync_raises_after_exhaustion() -> None:
    attempts = 0

    def operation() -> str:
        nonlocal attempts
        attempts += 1
        raise RateLimitError("still slow")

    with pytest.raises(RateLimitError):
        retry_sync(operation, max_retries=2, initial_delay=0, max_delay=0)
    assert attempts == 3


def test_retry_async_retries_transient_errors() -> None:
    async def run() -> tuple[str, int]:
        attempts = 0

        async def operation() -> str:
            nonlocal attempts
            attempts += 1
            if attempts < 2:
                raise RateLimitError("slow down")
            return "ok"

        return await retry_async(operation, max_retries=2, initial_delay=0, max_delay=0), attempts

    result, attempts = asyncio.run(run())

    assert result == "ok"
    assert attempts == 2
