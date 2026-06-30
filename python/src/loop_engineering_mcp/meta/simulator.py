"""Dry-run loop simulation against recorded fixtures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..github_ops.ci_ingest import CIFailureIngester


FIXTURES: dict[str, dict[str, Any]] = {
    "ci-failure-auth-test": {
        "description": "Auth test assertion failure — expect bug classification",
        "log": "FAIL tests/auth/test_login.py::test_token AssertionError: 401 != 200",
        "check_name": "unit-tests",
        "expected_classification": "bug",
        "verification_hint": "pytest tests/auth -q",
    },
    "flaky-test": {
        "description": "Intermittent timeout — expect flake classification",
        "log": "FAILED test_checkout — flaky timeout after 30s, retry passed on second run",
        "check_name": "e2e",
        "expected_classification": "flake",
        "verification_hint": "pytest tests/e2e --maxfail=1",
    },
    "env-missing": {
        "description": "Missing env var — expect env classification",
        "log": "Error: environment variable AUTH_SECRET is not set. ECONNREFUSED database",
        "check_name": "integration",
        "expected_classification": "env",
        "verification_hint": "export AUTH_SECRET=test && pytest tests/integration",
    },
    "dependency-conflict": {
        "description": "Lockfile conflict — expect dependency classification",
        "log": "npm ERR! ERESOLVE could not resolve peer dependency lockfile conflict",
        "check_name": "npm-ci",
        "expected_classification": "dependency",
        "verification_hint": "npm ci",
    },
}


@dataclass
class SimulationResult:
    fixture: str
    classification: str
    expected_classification: str
    classification_match: bool
    predicted_outcome: str
    recommended_verification: str
    would_escalate: bool
    notes: list[str]


class LoopSimulator:
    """Simulate a loop run without writes."""

    def __init__(self):
        self.ingester = CIFailureIngester()

    def list_fixtures(self) -> list[str]:
        return list(FIXTURES.keys())

    def simulate(
        self,
        loop_config: dict[str, Any],
        fixture_name: str,
    ) -> SimulationResult:
        fixture = FIXTURES.get(fixture_name)
        if not fixture:
            available = ", ".join(self.list_fixtures())
            raise ValueError(f"Unknown fixture '{fixture_name}'. Available: {available}")

        failure = self.ingester.classify_failure(
            fixture["log"], check_name=fixture["check_name"]
        )
        match = failure.classification == fixture["expected_classification"]

        max_attempts = int(loop_config.get("max_attempts", 3) or 3)
        has_verify = bool(
            (loop_config.get("verification_command") or "").strip()
            and "No verification" not in loop_config.get("verification_command", "")
        )

        notes: list[str] = []
        if not has_verify:
            notes.append("No verification_command — loop would rely on LLM self-report (high risk)")
        if loop_config.get("checker_enabled", True):
            notes.append(f"Checker spawns on attempt ≥{loop_config.get('checker_on_attempt', 2)}")
        if loop_config.get("hidden_verify_command"):
            notes.append("Hidden verify configured — maker cannot overfit visible tests")

        if failure.classification == "flake":
            predicted = "retry_once_then_escalate"
            would_escalate = max_attempts < 2
        elif failure.classification == "env":
            predicted = "escalate_without_code_change"
            would_escalate = True
        elif failure.classification == "dependency":
            predicted = "attempt_fix_with_verification"
            would_escalate = not has_verify
        else:
            predicted = "iterate_until_goal_or_max_attempts"
            would_escalate = not has_verify

        verify = loop_config.get("verification_command") or fixture["verification_hint"]

        return SimulationResult(
            fixture=fixture_name,
            classification=failure.classification,
            expected_classification=fixture["expected_classification"],
            classification_match=match,
            predicted_outcome=predicted,
            recommended_verification=verify,
            would_escalate=would_escalate,
            notes=notes,
        )

    def format_report(self, loop_name: str, result: SimulationResult) -> str:
        match = "✅" if result.classification_match else "⚠️"
        esc = "yes" if result.would_escalate else "no"
        lines = [
            f"🧪 **Simulation: {loop_name}** (fixture: `{result.fixture}`)\n",
            f"**Classification:** `{result.classification}` {match} "
            f"(expected `{result.expected_classification}`)",
            f"**Predicted outcome:** {result.predicted_outcome}",
            f"**Would escalate:** {esc}",
            f"**Recommended verification:** `{result.recommended_verification}`",
        ]
        if result.notes:
            lines.append("\n**Notes:**")
            for n in result.notes:
                lines.append(f"- {n}")
        lines.append("\n*No files were written — this was a dry run.*")
        return "\n".join(lines)
