"""Tests for trajectory scoring."""

from loop_engineering_mcp.scoring.trajectory import TrajectoryScorer


def test_trajectory_score(tmp_path):
    scorer = TrajectoryScorer(tmp_path / "logs")
    run_id = "abc123"
    scorer.append_event(run_id, {"event": "attempt", "attempt": 1, "progress": True})
    scorer.append_event(run_id, {"event": "verification", "passed": False})
    scorer.append_event(run_id, {"event": "attempt", "attempt": 2, "progress": True})
    scorer.append_event(run_id, {"event": "verification", "passed": True})

    score = scorer.score(run_id)
    assert score.iterations >= 1
    assert score.first_failure_step == 1
    report = scorer.format_report("demo", run_id, score)
    assert "Trajectory" in report
