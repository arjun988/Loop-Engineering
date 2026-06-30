"""Loop Engineering Score (LES) 1.0 calculator."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import aiofiles

LES_WEIGHTS: dict[str, float] = {
    "effectiveness": 0.20,
    "speed": 0.15,
    "cost": 0.12,
    "robustness": 0.13,
    "safety": 0.12,
    "scalability": 0.10,
    "adaptability": 0.10,
    "autonomy": 0.08,
}

CATEGORY_LABELS = {
    "effectiveness": "Effectiveness",
    "speed": "Speed",
    "cost": "Cost efficiency",
    "robustness": "Robustness",
    "safety": "Safety",
    "scalability": "Scalability",
    "adaptability": "Adaptability",
    "autonomy": "Autonomy",
}


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _median(values: list[float]) -> float:
    if not values:
        return 0.5
    ordered = sorted(values)
    mid = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[mid]
    return (ordered[mid - 1] + ordered[mid]) / 2


class LESScorer:
    """Compute LES from loop configuration and state history."""

    def __init__(self, state_dir: Path):
        self.state_dir = state_dir

    def compute_categories(self, loop_config: dict, state: dict) -> dict[str, float]:
        metrics = state.get("metrics", {})
        runs = state.get("runs", [])
        total = metrics.get("total_runs", 0) or len(runs)
        goals_met = metrics.get("goals_met", 0)
        escalations = metrics.get("escalations", 0)
        opened = metrics.get("prs_opened", 0)
        merged = metrics.get("prs_merged", 0)
        token_cost = float(metrics.get("total_token_cost", 0.0))

        if total == 0:
            return {cat: 0.5 for cat in LES_WEIGHTS}

        acceptance = merged / opened if opened else 0.0
        effectiveness = _clamp(0.6 * (goals_met / total) + 0.4 * acceptance)

        durations = [
            float(r.get("duration_seconds", 0))
            for r in runs
            if r.get("duration_seconds")
        ]
        if durations:
            med = _median(durations)
            # Faster is better: 60s → 1.0, 600s → ~0.5, 3600s → ~0.17
            speed = _clamp(60.0 / max(med, 1.0))
        else:
            speed = 0.7

        if goals_met > 0:
            cost_per_goal = token_cost / goals_met
            cost = _clamp(1.0 - min(cost_per_goal / 5.0, 1.0))
        else:
            cost = 0.3 if token_cost > 0 else 0.7

        successes = sum(1 for r in runs if r.get("status") in ("success", "success_no_changes"))
        multi_attempt_success = sum(
            1 for r in runs if r.get("attempts", 1) > 1 and r.get("goal_met")
        )
        robustness = _clamp(
            0.7 * (successes / total) + 0.3 * (multi_attempt_success / max(total, 1))
        )

        policy_violations = len(state.get("policy_violations", []))
        safety = _clamp(1.0 - policy_violations / max(total, 1))

        worktree_runs = sum(1 for r in runs if r.get("used_worktree"))
        scalability = _clamp(
            0.5 + 0.5 * (worktree_runs / total if loop_config.get("isolation") == "worktree" else 0.5)
        )

        lessons = len(state.get("lessons_learned", []))
        repeat_sigs = len(
            {state.get("last_failure_signature")}
            - {None}
        )
        adaptability = _clamp(min(lessons / 10.0, 1.0) * (1.0 - repeat_sigs * 0.1))

        autonomy = _clamp(1.0 - escalations / total)

        return {
            "effectiveness": effectiveness,
            "speed": speed,
            "cost": cost,
            "robustness": robustness,
            "safety": safety,
            "scalability": scalability,
            "adaptability": adaptability,
            "autonomy": autonomy,
        }

    def composite(self, categories: dict[str, float]) -> float:
        return round(sum(LES_WEIGHTS[k] * categories[k] for k in LES_WEIGHTS) * 100, 1)

    def format_loop_report(self, loop_name: str, loop_config: dict, state: dict) -> str:
        categories = self.compute_categories(loop_config, state)
        les = self.composite(categories)
        lines = [
            f"📊 **LES Report: {loop_name}** — **{les}/100**\n",
            "| Category | Score | Weight |",
            "|----------|-------|--------|",
        ]
        for cat, weight in LES_WEIGHTS.items():
            score = categories[cat]
            lines.append(
                f"| {CATEGORY_LABELS[cat]} | {score:.0%} | {weight:.0%} |"
            )
        metrics = state.get("metrics", {})
        lines.extend([
            "",
            f"**Runs:** {metrics.get('total_runs', 0)} | "
            f"**Goals met:** {metrics.get('goals_met', 0)} | "
            f"**Escalations:** {metrics.get('escalations', 0)} | "
            f"**Autonomy:** {categories['autonomy']:.0%}",
        ])
        return "\n".join(lines)

    def format_run_report(self, loop_name: str, run_id: str, state: dict) -> str:
        active = state.get("active_run") or {}
        matching = [r for r in state.get("runs", []) if r.get("run_id") == run_id]
        if not matching and active.get("run_id") != run_id:
            return f"❌ No run found with run_id `{run_id}` for loop '{loop_name}'."
        run = matching[-1] if matching else {}
        lines = [
            f"📋 **Run score: {loop_name}** (run_id: `{run_id}`)\n",
            f"**Status:** {run.get('status', active.get('status', 'active'))}",
            f"**Attempts:** {run.get('attempts', active.get('attempt', 1))}",
            f"**Goal met:** {'✅' if run.get('goal_met') else '❌'}",
            f"**Verification:** {'✅' if run.get('verification_passed') else '❌'}",
            f"**Token cost:** ${run.get('token_cost', 0):.4f}",
        ]
        if run.get("checker_verdict"):
            lines.append(f"**Checker verdict:** {run['checker_verdict']}")
        if run.get("hidden_verify_passed") is not None:
            lines.append(
                f"**Hidden verify:** {'✅' if run['hidden_verify_passed'] else '❌'}"
            )
        if run.get("pr_url"):
            lines.append(f"**PR:** {run['pr_url']}")
        return "\n".join(lines)

    async def autonomy_report(self, days: int = 7) -> str:
        cutoff = datetime.now() - timedelta(days=days)
        per_loop: list[tuple[str, int, int, float]] = []

        for state_file in self.state_dir.glob("*.json"):
            if state_file.name.endswith("-checklist.json"):
                continue
            if state_file.name.endswith("-hidden.json"):
                continue
            async with aiofiles.open(state_file, "r") as f:
                state = json.loads(await f.read())
            loop_name = state.get("loop_name", state_file.stem)
            recent = []
            for run in state.get("runs", []):
                ts = run.get("timestamp")
                if not ts:
                    continue
                try:
                    if datetime.fromisoformat(ts) >= cutoff:
                        recent.append(run)
                except ValueError:
                    continue
            if not recent:
                continue
            total = len(recent)
            escalated = sum(1 for r in recent if r.get("status") == "escalated")
            autonomy = 1.0 - escalated / total if total else 0.0
            per_loop.append((loop_name, total, escalated, autonomy))

        if not per_loop:
            return f"📈 **Autonomy report ({days}d):** No runs in window."

        overall_runs = sum(p[1] for p in per_loop)
        overall_esc = sum(p[2] for p in per_loop)
        overall_auto = 1.0 - overall_esc / overall_runs if overall_runs else 0.0

        lines = [
            f"📈 **Autonomy report (last {days} days)**\n",
            f"**Overall:** {overall_auto:.0%} autonomous "
            f"({overall_esc}/{overall_runs} escalations)\n",
            "**Per loop:**",
        ]
        for name, total, esc, auto in sorted(per_loop, key=lambda x: x[3], reverse=True):
            lines.append(f"- **{name}:** {auto:.0%} ({esc}/{total} escalated)")
        target = 0.85
        if overall_auto >= target:
            lines.append(f"\n✅ Meets autonomy target (≥{target:.0%})")
        else:
            lines.append(f"\n⚠️ Below autonomy target ({target:.0%}) — tune stop rules or skills")
        return "\n".join(lines)

    def safety_score(self, loop_config: dict, state: dict) -> float:
        return self.compute_categories(loop_config, state)["safety"]
