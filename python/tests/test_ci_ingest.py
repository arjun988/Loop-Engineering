"""Tests for CI failure classification."""

from loop_engineering_mcp.github_ops.ci_ingest import CIFailureIngester


def test_classify_env():
    ingester = CIFailureIngester()
    f = ingester.classify_failure("ECONNREFUSED connection refused to database", check_name="e2e")
    assert f.classification == "env"


def test_classify_bug():
    ingester = CIFailureIngester()
    f = ingester.classify_failure("AssertionError: expected 200 but got 404", check_name="unit")
    assert f.classification == "bug"


def test_suggest_loop_config():
    ingester = CIFailureIngester()
    f = ingester.classify_failure("FAIL: test_auth", check_name="ci")
    cfg = ingester.suggest_loop_config(f, "main")
    assert cfg["name"].startswith("ci-fix-")
    assert "skill_instructions" in cfg
