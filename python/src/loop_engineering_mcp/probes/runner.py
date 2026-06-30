"""Deterministic evidence probes (Bracket-style, no LLM)."""

from __future__ import annotations

import fnmatch
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from ..verification_runner import VerificationRunner


@dataclass
class ProbeResult:
    probe_type: str
    passed: bool
    message: str


class ProbeRunner:
    """Run configured probes against a worktree before the checker subagent."""

    def __init__(self, workspace_root: Path):
        self.workspace_root = workspace_root
        self.verification_runner = VerificationRunner(workspace_root)

    def _diff_line_count(self, workdir: str) -> int:
        try:
            result = subprocess.run(
                ["git", "diff", "--numstat", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workdir,
            )
            total = 0
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                    total += int(parts[0]) + int(parts[1])
            if total == 0:
                staged = subprocess.run(
                    ["git", "diff", "--numstat", "--cached"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=workdir,
                )
                for line in staged.stdout.splitlines():
                    parts = line.split("\t")
                    if len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit():
                        total += int(parts[0]) + int(parts[1])
            return total
        except Exception:
            return 0

    def _changed_files(self, workdir: str) -> list[str]:
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=workdir,
            )
            files = [ln.strip() for ln in result.stdout.splitlines() if ln.strip()]
            if not files:
                staged = subprocess.run(
                    ["git", "diff", "--name-only", "--cached"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    cwd=workdir,
                )
                files = [ln.strip() for ln in staged.stdout.splitlines() if ln.strip()]
            return files
        except Exception:
            return []

    async def run_probe(self, probe: dict[str, Any], workdir: str) -> ProbeResult:
        ptype = probe.get("type", "")
        work_path = Path(workdir)

        if ptype == "file_exists":
            rel = probe.get("path", "")
            target = work_path / rel if not Path(rel).is_absolute() else Path(rel)
            ok = target.exists()
            return ProbeResult(
                "file_exists",
                ok,
                f"{'Found' if ok else 'Missing'}: {rel}",
            )

        if ptype == "command":
            cmd = probe.get("cmd", "")
            expect = int(probe.get("expect_exit", 0))
            result = await self.verification_runner.run(cmd, cwd=work_path)
            ok = result.exit_code == expect
            return ProbeResult(
                "command",
                ok,
                f"exit {result.exit_code} (expected {expect}): {(result.stderr or result.stdout)[:300]}",
            )

        if ptype == "diff_max_lines":
            max_lines = int(probe.get("max", 200))
            count = self._diff_line_count(workdir)
            ok = count <= max_lines
            return ProbeResult(
                "diff_max_lines",
                ok,
                f"{count} lines changed (max {max_lines})",
            )

        if ptype == "forbidden_path":
            pattern = probe.get("pattern", "")
            hits = [f for f in self._changed_files(workdir) if fnmatch.fnmatch(f, pattern)]
            ok = not hits
            return ProbeResult(
                "forbidden_path",
                ok,
                f"Forbidden matches: {hits}" if hits else f"No forbidden paths ({pattern})",
            )

        return ProbeResult(ptype or "unknown", False, f"Unknown probe type: {ptype}")

    async def run_all(
        self, probes: list[dict[str, Any]], workdir: Optional[str] = None
    ) -> tuple[bool, list[ProbeResult]]:
        if not probes:
            return True, []
        cwd = workdir or str(self.workspace_root)
        results: list[ProbeResult] = []
        for probe in probes:
            results.append(await self.run_probe(probe, cwd))
        passed = all(r.passed for r in results)
        return passed, results

    def format_report(self, loop_name: str, results: list[ProbeResult]) -> str:
        if not results:
            return f"✅ **Probes: {loop_name}** — none configured"
        passed = all(r.passed for r in results)
        lines = [
            f"{'✅' if passed else '❌'} **Probes: {loop_name}** ({sum(1 for r in results if r.passed)}/{len(results)} passed)\n"
        ]
        for r in results:
            mark = "✅" if r.passed else "❌"
            lines.append(f"{mark} `{r.probe_type}` — {r.message}")
        return "\n".join(lines)
