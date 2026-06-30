"""Tests for LES scoring."""

import pytest

from loop_engineering_mcp.scoring.les import LESScorer


@pytest.fixture
def scorer(tmp_path):
    return LESScorer(tmp_path / "state")


def test_composite_perfect_score(scorer):
    state = {
        "metrics": {
            "total_runs": 10,
            "goals_met": 10,
            "prs_opened": 8,
            "prs_merged": 8,
            "escalations": 0,
            "total_token_cost": 1.0,
        },
        "runs": [{"status": "success", "goal_met": True, "duration_seconds": 30}],
        "lessons_learned": ["a"],
        "policy_violations": [],
    }
    cats = scorer.compute_categories({"isolation": "worktree"}, state)
    assert cats["autonomy"] == 1.0
    les = scorer.composite(cats)
    assert les > 70


def test_autonomy_drops_with_escalations(scorer):
    state = {
        "metrics": {"total_runs": 4, "goals_met": 2, "escalations": 2, "prs_opened": 0, "prs_merged": 0, "total_token_cost": 0},
        "runs": [],
        "lessons_learned": [],
    }
    cats = scorer.compute_categories({}, state)
    assert cats["autonomy"] == 0.5
