"""Tests for feature checklist."""

import pytest

from loop_engineering_mcp.checklist.manager import ChecklistManager


@pytest.fixture
def checklist(tmp_path):
    return ChecklistManager(tmp_path / "state", tmp_path)


@pytest.mark.asyncio
async def test_init_and_status(checklist):
    await checklist.init_checklist("demo", [
        {"id": "auth", "description": "Auth works", "verify_command": ""},
        {"id": "ui", "description": "UI loads"},
    ])
    status = await checklist.status("demo")
    assert "0/2" in status
    assert not await checklist.all_complete("demo")


@pytest.mark.asyncio
async def test_mark_without_verify(checklist):
    await checklist.init_checklist("demo", [{"id": "a", "description": "x"}])
    await checklist.mark_feature("demo", "a", passes=True)
    assert await checklist.all_complete("demo")
