"""Tests for policy gates."""

from loop_engineering_mcp.policy.manager import PolicyManager


def test_deny_forbidden_path():
    mgr = PolicyManager()
    decision, violations = mgr.check_diff(
        {"deny_paths": [".env"], "max_files_per_run": 50},
        [".env", "src/main.py"],
    )
    assert decision == "deny"
    assert violations


def test_check_action_denies_write():
    mgr = PolicyManager()
    decision, detail = mgr.check_action(
        {"deny_paths": ["package-lock.json"]},
        tool="write",
        args={"path": "package-lock.json"},
    )
    assert decision == "deny"
