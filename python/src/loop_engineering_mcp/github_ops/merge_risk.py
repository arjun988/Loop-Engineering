"""Risk-scored auto-merge for loop PRs."""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass

from ..scoring.les import LESScorer


@dataclass
class MergeRiskResult:
    score: float
    factors: dict[str, float]
    passed: bool
    blockers: list[str]


class MergeRiskEvaluator:
    """Deterministic merge risk scoring (no LLM)."""

    WEIGHTS = {
        "ci_status": 0.30,
        "diff_size": 0.15,
        "path_risk": 0.25,
        "review_comments": 0.15,
        "flake_history": 0.10,
        "test_delta": 0.05,
    }

    def __init__(self, les_scorer: LESScorer):
        self.les_scorer = les_scorer

    def evaluate(
        self,
        *,
        loop_config: dict,
        state: dict,
        pr_data: dict,
        checks: list[dict],
        files: list[dict],
        comments: list[dict],
        min_score: float = 85.0,
    ) -> MergeRiskResult:
        blockers: list[str] = []
        factors: dict[str, float] = {}

        ci_ok = all(
            c.get("conclusion") == "success"
            for c in checks
            if c.get("conclusion") not in ("skipped", "neutral")
        ) and bool(checks)
        factors["ci_status"] = 1.0 if ci_ok else 0.0
        if not ci_ok:
            blockers.append("CI not green")

        total_lines = sum(
            (f.get("additions", 0) + f.get("deletions", 0)) for f in files
        )
        max_lines = int(loop_config.get("max_diff_lines", 500) or 500)
        factors["diff_size"] = 1.0 if total_lines <= max_lines else max(
            0.0, 1.0 - (total_lines - max_lines) / max_lines
        )
        if total_lines > max_lines:
            blockers.append(f"Diff too large ({total_lines} > {max_lines} lines)")

        forbidden = loop_config.get("forbidden_paths") or []
        touched_forbidden = []
        for f in files:
            path = f.get("filename", "")
            for pattern in forbidden:
                if fnmatch.fnmatch(path, pattern) or pattern in path:
                    touched_forbidden.append(path)
        factors["path_risk"] = 0.0 if touched_forbidden else 1.0
        if touched_forbidden:
            blockers.append(f"Forbidden paths: {', '.join(touched_forbidden[:3])}")

        human_comments = [
            c for c in comments
            if c.get("user", {}).get("type") != "Bot"
        ]
        factors["review_comments"] = 1.0 if not human_comments else 0.3
        if human_comments:
            blockers.append(f"{len(human_comments)} human review comment(s)")

        branch_retries = state.get("branch_retry_count", 0)
        factors["flake_history"] = 1.0 if branch_retries <= 2 else 0.4
        if branch_retries > 2:
            blockers.append("Branch retried too many times")

        test_files = [f for f in files if "test" in f.get("filename", "").lower()]
        factors["test_delta"] = 1.0 if test_files or total_lines < 50 else 0.6

        checker = state.get("last_checker_verdict")
        if checker and checker != "PASS":
            blockers.append(f"Checker verdict: {checker}")

        safety = self.les_scorer.safety_score(loop_config, state)
        if safety < 0.8:
            blockers.append(f"LES safety {safety:.0%} < 80%")

        weighted = sum(factors[k] * self.WEIGHTS[k] for k in self.WEIGHTS) * 100
        score = round(weighted, 1)
        passed = score >= min_score and not blockers

        return MergeRiskResult(
            score=score,
            factors={k: round(v, 2) for k, v in factors.items()},
            passed=passed,
            blockers=blockers,
        )

    def format_report(self, result: MergeRiskResult, pr_number: int) -> str:
        lines = [
            f"⚖️ **Merge risk: PR #{pr_number}** — **{result.score}/100**",
            f"**Auto-merge eligible:** {'✅ Yes' if result.passed else '❌ No'}\n",
            "**Factors:**",
        ]
        for name, val in result.factors.items():
            lines.append(f"- {name}: {val:.0%}")
        if result.blockers:
            lines.append("\n**Blockers:**")
            for b in result.blockers:
                lines.append(f"- {b}")
        return "\n".join(lines)
