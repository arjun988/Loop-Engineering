"""Tests for checker brief and hidden verify."""

import pytest

from loop_engineering_mcp.checker.brief import CheckerBriefBuilder
from loop_engineering_mcp.hidden_verify import HiddenVerifyManager


def test_should_spawn_on_attempt():
    builder = CheckerBriefBuilder()
    cfg = {"checker_enabled": True, "checker_on_attempt": 2, "risk_paths": []}
    assert not builder.should_spawn_checker(cfg, 1, [])
    assert builder.should_spawn_checker(cfg, 2, [])


def test_should_spawn_on_risk_path():
    builder = CheckerBriefBuilder()
    cfg = {"checker_enabled": True, "checker_on_attempt": 5, "risk_paths": ["src/auth/**"]}
    assert builder.should_spawn_checker(cfg, 1, ["src/auth/login.py"])


@pytest.mark.asyncio
async def test_hidden_verify_skips_empty(tmp_path):
    mgr = HiddenVerifyManager(tmp_path / "state", tmp_path)
    passed, msg = await mgr.run("demo", "")
    assert passed is True


@pytest.mark.asyncio
async def test_hidden_metrics(tmp_path):
    mgr = HiddenVerifyManager(tmp_path / "state", tmp_path)
    await mgr.run("demo", "echo ok")
    report = await mgr.view_metrics("demo")
    assert "Hidden metrics" in report
