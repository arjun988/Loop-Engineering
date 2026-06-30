"""CI failure classification and ingestion."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ClassifiedFailure:
    check: str
    log_snippet: str
    classification: str
    confidence: float


class CIFailureIngester:
    """Classify CI logs and structure failures for loop creation."""

    FLAKE_PATTERNS = [
        r"flaky",
        r"intermittent",
        r"retry.*passed",
        r"timed out",
    ]
    ENV_PATTERNS = [
        r"ECONNREFUSED",
        r"connection refused",
        r"ENV.*not set",
        r"environment variable",
        r"service unavailable",
        r"could not connect",
    ]
    DEP_PATTERNS = [
        r"ERESOLVE",
        r"peer dep",
        r"lockfile",
        r"npm ERR!",
        r"version conflict",
        r"incompatible",
    ]
    BUG_PATTERNS = [
        r"AssertionError",
        r"assert.*failed",
        r"Expected.*but got",
        r"FAIL:",
        r"Test.*failed",
        r"error TS\d+",
    ]

    def classify_failure(self, log: str, *, check_name: str = "unknown") -> ClassifiedFailure:
        log_lower = log.lower()
        snippet = log.strip()[:1500]

        scores = {
            "flake": self._score(log_lower, self.FLAKE_PATTERNS),
            "env": self._score(log_lower, self.ENV_PATTERNS),
            "dependency": self._score(log_lower, self.DEP_PATTERNS),
            "bug": self._score(log_lower, self.BUG_PATTERNS),
        }
        best = max(scores, key=scores.get)
        confidence = scores[best]
        if confidence < 0.3:
            best = "bug"
            confidence = 0.5

        return ClassifiedFailure(
            check=check_name,
            log_snippet=snippet,
            classification=best,
            confidence=confidence,
        )

    @staticmethod
    def _score(text: str, patterns: list[str]) -> float:
        hits = sum(1 for p in patterns if re.search(p, text, re.I))
        return min(hits / max(len(patterns), 1) * 2, 1.0)

    def format_classification(self, failure: ClassifiedFailure) -> str:
        return (
            f"**{failure.check}** → `{failure.classification}` "
            f"(confidence {failure.confidence:.0%})\n"
            f"```\n{failure.log_snippet[:800]}\n```"
        )

    async def ingest_from_checks(
        self,
        github_client,
        *,
        branch: str,
        repo: Optional[str] = None,
    ) -> list[ClassifiedFailure]:
        checks = await github_client.get_check_runs_for_ref(branch, repo=repo)
        failures: list[ClassifiedFailure] = []
        for check in checks:
            if check.get("conclusion") in ("success", "skipped", "neutral", None):
                continue
            log = check.get("output", {}).get("summary", "") or check.get("name", "")
            failures.append(
                self.classify_failure(log, check_name=check.get("name", "check"))
            )
        return failures

    def format_ingest_report(self, failures: list[ClassifiedFailure], branch: str) -> str:
        if not failures:
            return f"✅ **CI ingest:** No failing checks on `{branch}`."
        lines = [f"🔴 **CI failures on `{branch}`** ({len(failures)})\n"]
        for f in failures:
            lines.append(self.format_classification(f))
            lines.append("")
        return "\n".join(lines)

    def suggest_loop_config(self, failure: ClassifiedFailure, branch: str) -> dict[str, Any]:
        name = f"ci-fix-{failure.classification}-{failure.check[:20].lower().replace(' ', '-')}"
        name = re.sub(r"[^a-z0-9-]", "", name)[:40]
        return {
            "name": name,
            "description": f"Fix CI failure: {failure.check} ({failure.classification})",
            "schedule": "0 */6 * * *",
            "goal": f"CI check '{failure.check}' passes on {branch}",
            "verification_command": "echo 'Set project test command'",
            "skill_instructions": (
                f"Fix the CI failure classified as **{failure.classification}**.\n\n"
                f"**Check:** {failure.check}\n\n"
                f"**Log excerpt:**\n```\n{failure.log_snippet[:1000]}\n```\n\n"
                "Make the smallest fix. Do not disable tests."
            ),
            "max_attempts": 3,
            "isolation": "worktree",
        }
