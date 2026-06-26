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
