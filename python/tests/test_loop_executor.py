"""Tests for the loop-engineering control system: maker/checker gate,
iterate-until-goal stop rules, no-progress detection, and budget caps."""

import pytest
from unittest.mock import AsyncMock

from loop_engineering_mcp.loop_manager import LoopManager
from loop_engineering_mcp.skill_manager import SkillManager
from loop_engineering_mcp.state_manager import StateManager
from loop_engineering_mcp.logger import LoopLogger
from loop_engineering_mcp.loop_executor import LoopExecutor
from loop_engineering_mcp.verification_runner import VerificationResult


@pytest.fixture
async def executor(tmp_path):
    loop_dir = tmp_path / ".loop"
    loop_manager = LoopManager(loop_dir)
    skill_manager = SkillManager(loop_dir / "skills")
    state_manager = StateManager(loop_dir / "state")
    logger = LoopLogger(loop_dir / "logs")
    ex = LoopExecutor(tmp_path, loop_manager, skill_manager, state_manager, logger)
    await loop_manager.create_loop(
        name="demo",
        description="demo loop",
        schedule="* * * * *",
        skill_instructions="do the thing",
        goal="thing is done",
        verification_command="echo ok",
        max_attempts=3,
        max_runs_per_day=24,
    )
    await state_manager.initialize_state("demo")
    return ex


def _gate(success: bool, output: str = "boom"):
    return VerificationResult(
        success=success, exit_code=0 if success else 1, stdout="", stderr=output
    )


@pytest.mark.asyncio
async def test_success_path_records_goal_met(executor):
    await executor.begin_run("demo", create_pr=False)
    executor.verification_runner.run = AsyncMock(return_value=_gate(True))

    state = await executor.state_manager._load_state("demo")
    run_id = state["active_run"]["run_id"]

    result = await executor.complete_run("demo", run_id, "did it", create_pr=False)
    assert "Goal met (checker):** ✅ Yes" in result

    state = await executor.state_manager._load_state("demo")
    assert state["active_run"] is None
    assert state["metrics"]["goals_met"] == 1


@pytest.mark.asyncio
async def test_fresh_failure_asks_for_iteration(executor):
    await executor.begin_run("demo", create_pr=False)
    executor.verification_runner.run = AsyncMock(return_value=_gate(False, "err-A"))

    state = await executor.state_manager._load_state("demo")
    run_id = state["active_run"]["run_id"]

    result = await executor.complete_run("demo", run_id, "attempt 1", create_pr=False)
    assert "Iterate" in result
    assert "attempt 2/3" in result

    # Active run stays open so the agent can iterate with the same run_id.
    state = await executor.state_manager._load_state("demo")
    assert state["active_run"] is not None
    assert state["active_run"]["attempt"] == 2


@pytest.mark.asyncio
async def test_repeated_failure_escalates(executor):
    await executor.begin_run("demo", create_pr=False)
    executor.verification_runner.run = AsyncMock(return_value=_gate(False, "same-error"))

    state = await executor.state_manager._load_state("demo")
    run_id = state["active_run"]["run_id"]

    first = await executor.complete_run("demo", run_id, "attempt 1", create_pr=False)
    assert "Iterate" in first

    # Identical failure twice → no-progress → escalate before exhausting attempts.
    second = await executor.complete_run("demo", run_id, "attempt 2", create_pr=False)
    assert "escalated" in second.lower()

    state = await executor.state_manager._load_state("demo")
    assert state["active_run"] is None
    assert len(state["escalations"]) == 1


@pytest.mark.asyncio
async def test_daily_budget_blocks_new_run(executor):
    # Tighten the budget to a single run/day, then consume it.
    loops = await executor.loop_manager._load_loops()
    loops["demo"]["max_runs_per_day"] = 1
    await executor.loop_manager._save_loops(loops)

    await executor.state_manager.record_run(
        "demo", summary="used budget", status="success", goal_met=True
    )

    result = await executor.begin_run("demo", create_pr=False)
    assert "budget" in result.lower()
