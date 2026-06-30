"""Tests for cron scheduler."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from loop_engineering_mcp.scheduler import LoopScheduler


@pytest.fixture
def scheduler(tmp_path):
    loop_manager = MagicMock()
    loop_manager._load_loops = AsyncMock(return_value={
        "active-loop": {
            "status": "active",
            "schedule": "* * * * *",
        },
        "stopped-loop": {
            "status": "stopped",
            "schedule": "* * * * *",
        },
    })
    logger = MagicMock()
    run_callback = AsyncMock(return_value="done")
    return LoopScheduler(loop_manager, logger, run_callback=run_callback, poll_interval=1)


def test_is_due_first_run(scheduler):
    assert scheduler._is_due("* * * * *", "new-loop") is True


def test_is_due_invalid_cron(scheduler):
    assert scheduler._is_due("invalid cron", "bad-loop") is False


@pytest.mark.asyncio
async def test_run_now(scheduler):
    result = await scheduler.run_now("active-loop", create_pr=False)
    assert result == "done"
    scheduler.run_callback.assert_called_once_with("active-loop", create_pr=False)


@pytest.mark.asyncio
async def test_run_now_prevents_concurrent(scheduler):
    scheduler._in_progress.add("active-loop")
    result = await scheduler.run_now("active-loop")
    assert "already running" in result
    scheduler.run_callback.assert_not_called()
