"""Checker subagent brief builder (maker/checker separation)."""

from __future__ import annotations

import fnmatch
import json
import subprocess
from typing import Optional


class CheckerBriefBuilder:
    """Build read-only checker briefs for the host agent."""

    def get_changed_files(self, workdir: str, base: str = "HEAD") -> list[str]:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", base],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workdir,
            )
            if result.returncode != 0:
                staged = subprocess.run(
                    ["git", "diff", "--name-only", "--cached"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=workdir,
                )
                return [ln.strip() for ln in staged.stdout.splitlines() if ln.strip()]
            return [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
        except Exception:
            return []

    def touches_risk_path(self, files: list[str], risk_paths: list[str]) -> bool:
        for path in files:
            for pattern in risk_paths:
                if fnmatch.fnmatch(path, pattern) or pattern in path:
                    return True
        return False

    def should_spawn_checker(
        self,
        loop_config: dict,
        attempt: int,
        changed_files: list[str],
    ) -> bool:
        if not loop_config.get("checker_enabled", True):
            return False
        min_attempt = int(loop_config.get("checker_on_attempt", 2) or 2)
        risk_paths = loop_config.get("risk_paths") or []
        if attempt >= min_attempt:
            return True
        if risk_paths and self.touches_risk_path(changed_files, risk_paths):
            return True
        return False

    def build_brief(
        self,
        *,
        loop_name: str,
        run_id: str,
        goal: str,
        workdir: str,
        verification_command: str,
        skill_excerpt: str,
        changed_files: list[str],
        forbidden_paths: Optional[list[str]] = None,
    ) -> str:
        files_text = "\n".join(f"- `{f}`" for f in changed_files) or "- (no diff detected)"
        forbidden = forbidden_paths or []
        forbidden_text = ", ".join(forbidden) if forbidden else "none configured"

        return f"""🔍 **Checker subagent required: {loop_name}** (run_id: `{run_id}`)

You are the **checker** in a maker/checker split. The maker already passed shell gates.
Your job is to **default REJECT** unless evidence is strong.

**Working directory:** `{workdir}`
**Goal:** {goal}
**Maker verification command (re-run yourself):** `{verification_command}`

## Changed files
{files_text}

## Forbidden paths (must not be touched)
{forbidden_text}

## Rubric (from skill)
{skill_excerpt[:3000]}

## Checks (run independently — read-only tools + shell tests only)
1. **Scope:** Only relevant files changed; no forbidden paths; no unrelated edits.
2. **Intent:** Change addresses the stated goal — not a different problem.
3. **Tests:** Re-run verification yourself; report pass/fail with output snippet.
4. **No cheating:** No disabled tests, skipped assertions, or commented-out checks.
5. **Risk:** Recommend ESCALATE if medium+ risk even when tests pass.

## Required output
Return JSON only:
```json
{{
  "verdict": "PASS" | "REJECT" | "ESCALATE",
  "checks": [
    {{"name": "scope", "status": "PASS|FAIL", "evidence": "..."}},
    {{"name": "intent", "status": "PASS|FAIL", "evidence": "..."}},
    {{"name": "tests", "status": "PASS|FAIL", "evidence": "..."}},
    {{"name": "no_cheating", "status": "PASS|FAIL", "evidence": "..."}}
  ],
  "summary": "one paragraph"
}}
```

Then call `submit_checker_verdict` with the same loop_name, run_id, and verdict.
"""

    @staticmethod
    def parse_verdict(checks_json: str) -> tuple[str, list[dict]]:
        try:
            data = json.loads(checks_json)
            verdict = str(data.get("verdict", "REJECT")).upper()
            if verdict not in ("PASS", "REJECT", "ESCALATE"):
                verdict = "REJECT"
            return verdict, list(data.get("checks", []))
        except (json.JSONDecodeError, TypeError):
            return "REJECT", []
