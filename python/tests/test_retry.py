"""Tests for retry utility."""

import pytest

from loop_engineering_mcp.retry import retry_async


@pytest.mark.asyncio
async def test_retry_succeeds_first_try():
    calls = {"count": 0}

    async def fn():
        calls["count"] += 1
        return "ok"

    result = await retry_async(fn, max_attempts=3)
    assert result == "ok"
    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():
    calls = {"count": 0}

    async def fn():
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("not yet")
        return "ok"

    result = await retry_async(fn, max_attempts=3, base_delay=0.01)
    assert result == "ok"
    assert calls["count"] == 3


@pytest.mark.asyncio
async def test_retry_exhausted():
    async def fn():
        raise RuntimeError("always fails")

    with pytest.raises(RuntimeError, match="always fails"):
        await retry_async(fn, max_attempts=2, base_delay=0.01)
