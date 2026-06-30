"""Tests for loop simulation."""

from loop_engineering_mcp.meta.simulator import LoopSimulator


def test_simulate_auth_fixture():
    sim = LoopSimulator()
    result = sim.simulate(
        {"max_attempts": 3, "verification_command": "pytest -q", "checker_enabled": True},
        "ci-failure-auth-test",
    )
    assert result.classification_match
    report = sim.format_report("demo", result)
    assert "dry run" in report.lower()
