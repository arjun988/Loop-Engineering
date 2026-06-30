"""Tests for state manager run recording."""

import pytest

from loop_engineering_mcp.state_manager import StateManager


@pytest.fixture
def state_manager(tmp_path):
    return StateManager(tmp_path / "state")


@pytest.mark.asyncio
async def test_initialize_state(state_manager):
    result = await state_manager.initialize_state("test-loop")
    assert "initialized" in result
    state = await state_manager._load_state("test-loop")
    assert state["metrics"]["total_runs"] == 0


@pytest.mark.asyncio
async def test_record_run(state_manager):
    await state_manager.initialize_state("test-loop")
    await state_manager.record_run(
        "test-loop",
        summary="Test run completed",
        status="success",
        token_cost=0.05,
        verification_passed=True,
        pr_url="https://github.com/org/repo/pull/1",
    )
    state = await state_manager._load_state("test-loop")
    assert state["metrics"]["total_runs"] == 1
    assert state["metrics"]["prs_opened"] == 1
    assert state["metrics"]["total_token_cost"] == 0.05
    assert len(state["runs"]) == 1


@pytest.mark.asyncio
async def test_record_escalation(state_manager):
    await state_manager.initialize_state("test-loop")
    await state_manager.record_escalation("test-loop", "Verification failed")
    state = await state_manager._load_state("test-loop")
    assert len(state["escalations"]) == 1
    assert state["status"] == "escalated"


@pytest.mark.asyncio
async def test_add_lesson(state_manager):
    await state_manager.initialize_state("test-loop")
    await state_manager.add_lesson("test-loop", "Always run tests first")
    state = await state_manager._load_state("test-loop")
    assert len(state["lessons_learned"]) == 1


@pytest.mark.asyncio
async def test_record_run_counts_goal_and_daily(state_manager):
    await state_manager.initialize_state("test-loop")
    await state_manager.record_run(
        "test-loop", summary="done", status="success", goal_met=True, attempts=2
    )
    state = await state_manager._load_state("test-loop")
    assert state["metrics"]["goals_met"] == 1
    assert state_manager.runs_today(state) == 1
    assert state["runs"][0]["attempts"] == 2


@pytest.mark.asyncio
async def test_schema_backfilled_for_old_state(state_manager, tmp_path):
    import json

    # Simulate an older state file missing the new keys.
    legacy = {
        "loop_name": "legacy",
        "metrics": {"total_runs": 5},
        "runs": [],
    }
    state_file = state_manager.state_dir / "legacy.json"
    state_file.write_text(json.dumps(legacy))

    state = await state_manager._load_state("legacy")
    assert state["daily_runs"] == {}
    assert state["last_failure_signature"] is None
    assert state["metrics"]["goals_met"] == 0
    assert state["metrics"]["total_runs"] == 5


@pytest.mark.asyncio
async def test_bump_attempt_detects_no_progress(state_manager):
    await state_manager.initialize_state("test-loop")
    await state_manager.set_active_run(
        "test-loop", run_id="abc", branch=None, create_pr=False, max_attempts=3
    )
    sig = state_manager.failure_signature("the same error")

    first = await state_manager.bump_attempt("test-loop", sig)
    assert first["attempt"] == 2
    assert first["repeated_failure"] is False

    second = await state_manager.bump_attempt("test-loop", sig)
    assert second["attempt"] == 3
    assert second["repeated_failure"] is True
