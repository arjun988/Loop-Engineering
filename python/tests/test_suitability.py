"""Tests for the 4-condition loop suitability test."""

from loop_engineering_mcp.suitability import check_suitability


def test_all_conditions_pass():
    result = check_suitability(
        "CI triage",
        repeats=True,
        automated_verification=True,
        agent_tools=True,
        token_budget=True,
    )
    assert result.score == 4
    assert result.passed is True
    assert "Build the loop" in result.report


def test_missing_verification_fails():
    result = check_suitability(
        "Vague product work",
        repeats=True,
        automated_verification=False,
        agent_tools=True,
        token_budget=True,
    )
    assert result.score == 3
    assert result.passed is False
    assert "manual prompt" in result.report
    assert "automated_verification" in result.report
