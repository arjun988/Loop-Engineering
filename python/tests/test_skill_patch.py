"""Tests for skill patch meta-loop."""

import pytest

from loop_engineering_mcp.meta.skill_patch import SkillPatchManager
from loop_engineering_mcp.state_manager import StateManager


@pytest.fixture
def patch_mgr(tmp_path):
    state_dir = tmp_path / "state"
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    mgr = SkillPatchManager(state_dir, skills_dir)
    state_mgr = StateManager(state_dir)
    return mgr, state_mgr, skills_dir


@pytest.mark.asyncio
async def test_propose_after_escalations(patch_mgr):
    mgr, state_mgr, _ = patch_mgr
    await state_mgr.initialize_state("demo")
    for _ in range(3):
        await state_mgr.record_escalation("demo", "Verification failed: auth test")

    state = await state_mgr._load_state("demo")
    result = await mgr.propose("demo", state, min_escalations=3)
    assert "proposed" in result.lower()


@pytest.mark.asyncio
async def test_apply_patch(patch_mgr):
    mgr, state_mgr, skills_dir = patch_mgr
    await state_mgr.initialize_state("demo")
    skill = skills_dir / "demo.md"
    skill.write_text("# Demo\n", encoding="utf-8")

    for _ in range(3):
        await state_mgr.record_escalation("demo", "same failure")
    state = await state_mgr._load_state("demo")
    await mgr.propose("demo", state, min_escalations=3)

    patches = await mgr._load_patches()
    patch_id = patches["patches"][-1]["patch_id"]
    applied = await mgr.apply("demo", patch_id)
    assert "applied" in applied.lower()
    assert "automated analysis" in skill.read_text(encoding="utf-8")
