"""Trajectory scoring from per-run JSONL event logs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class TrajectoryScore:
    iterations: int
    regression_count: int
    wasted_attempts: int
    convergence_rate: float
    first_failure_step: Optional[int]
    events: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "iterations": self.iterations,
            "regression_count": self.regression_count,
            "wasted_attempts": self.wasted_attempts,
            "convergence_rate": round(self.convergence_rate, 3),
            "first_failure_step": self.first_failure_step,
        }


class TrajectoryScorer:
    """Score how efficiently a loop run converged toward its goal."""

    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def trajectory_path(self, run_id: str) -> Path:
        return self.logs_dir / f"{run_id}.jsonl"

    def append_event(self, run_id: str, event: dict[str, Any]) -> None:
        path = self.trajectory_path(run_id)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")

    def load_events(self, run_id: str) -> list[dict[str, Any]]:
        path = self.trajectory_path(run_id)
        if not path.exists():
            return []
        events = []
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    events.append(json.loads(line))
        return events

    def score(self, run_id: str) -> TrajectoryScore:
        events = self.load_events(run_id)
        attempts = [e for e in events if e.get("event") == "attempt"]
        iterations = len(attempts) or len([e for e in events if e.get("event")])

        outcomes = []
        for e in events:
            if e.get("event") in ("verification", "goal_check", "probes", "attempt"):
                if "passed" in e:
                    outcomes.append(bool(e["passed"]))

        regression_count = 0
        for i in range(1, len(outcomes)):
            if outcomes[i - 1] and not outcomes[i]:
                regression_count += 1

        first_failure_step = None
        for i, ok in enumerate(outcomes, start=1):
            if not ok:
                first_failure_step = i
                break

        wasted = sum(1 for e in events if e.get("event") == "attempt" and not e.get("progress", True))

        if len(outcomes) >= 2:
            convergence = (outcomes[-1] - outcomes[0]) / (len(outcomes) - 1) if outcomes[0] != outcomes[-1] else (1.0 if outcomes[-1] else 0.0)
        elif outcomes:
            convergence = 1.0 if outcomes[-1] else 0.0
        else:
            convergence = 0.0

        return TrajectoryScore(
            iterations=iterations,
            regression_count=regression_count,
            wasted_attempts=wasted,
            convergence_rate=max(-1.0, min(1.0, convergence)),
            first_failure_step=first_failure_step,
            events=events,
        )

    def format_report(self, loop_name: str, run_id: str, score: TrajectoryScore) -> str:
        data = score.to_dict()
        lines = [
            f"📈 **Trajectory: {loop_name}** (run_id: `{run_id}`)\n",
            f"- **Iterations:** {data['iterations']}",
            f"- **Regression count:** {data['regression_count']}",
            f"- **Wasted attempts:** {data['wasted_attempts']}",
            f"- **Convergence rate:** {data['convergence_rate']:.2f}",
            f"- **First failure step:** {data['first_failure_step'] or 'none'}",
        ]
        if score.events:
            lines.append("\n**Recent events:**")
            for e in score.events[-5:]:
                lines.append(f"- {e.get('event', '?')}: {e.get('detail', e.get('passed', ''))}")
        return "\n".join(lines)
