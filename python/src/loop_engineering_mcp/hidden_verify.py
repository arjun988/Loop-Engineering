"""Hidden out-of-sample validation (never exposed to the agent)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from .verification_runner import VerificationRunner


class HiddenVerifyManager:
    """Orchestrator-only hidden verification gate."""

    def __init__(self, state_dir: Path, workspace_root: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.verification_runner = VerificationRunner(workspace_root)

    def _metrics_path(self, loop_name: str) -> Path:
        return self.state_dir / f"{loop_name}-hidden.json"

    async def configure(self, loop_name: str, command: str, loops_save) -> str:
        """Persist command in loops.json via callback; never in skills."""
        await loops_save(loop_name, {"hidden_verify_command": command})
        metrics = await self._load_metrics(loop_name)
        metrics["configured_at"] = datetime.now().isoformat()
        await self._save_metrics(loop_name, metrics)
        return (
            f"✅ Hidden verify configured for '{loop_name}'.\n"
            f"**Command:** `{command}`\n"
            "This command is **never** shown to the maker agent."
        )

    async def _load_metrics(self, loop_name: str) -> dict:
        path = self._metrics_path(loop_name)
        if not path.exists():
            return {"loop_name": loop_name, "runs": []}
        async with aiofiles.open(path, "r") as f:
            return json.loads(await f.read())

    async def _save_metrics(self, loop_name: str, data: dict) -> None:
        async with aiofiles.open(self._metrics_path(loop_name), "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def run(
        self,
        loop_name: str,
        command: str,
        *,
        workdir: Optional[str] = None,
    ) -> tuple[bool, str]:
        if not command or not command.strip():
            return True, "No hidden verify configured — skipped"

        result = await self.verification_runner.run(
            command, cwd=Path(workdir) if workdir else None
        )
        passed = result.success
        output = result.stderr or result.stdout or f"exit {result.exit_code}"

        metrics = await self._load_metrics(loop_name)
        metrics.setdefault("runs", []).append({
            "timestamp": datetime.now().isoformat(),
            "passed": passed,
            "exit_code": result.exit_code,
            "duration_seconds": result.duration_seconds,
        })
        metrics["last_passed"] = passed
        metrics["last_run"] = datetime.now().isoformat()
        await self._save_metrics(loop_name, metrics)

        return passed, output

    async def view_metrics(self, loop_name: str) -> str:
        metrics = await self._load_metrics(loop_name)
        runs = metrics.get("runs", [])
        if not runs:
            return f"📊 **Hidden metrics: {loop_name}** — no runs yet."

        passed = sum(1 for r in runs if r.get("passed"))
        lines = [
            f"📊 **Hidden metrics: {loop_name}** (ops dashboard only)\n",
            f"**Runs:** {len(runs)} | **Passed:** {passed} | "
            f"**Rate:** {passed / len(runs):.0%}\n",
            "**Recent:**",
        ]
        for run in runs[-5:]:
            mark = "✅" if run.get("passed") else "❌"
            lines.append(f"- {run.get('timestamp', '?')}: {mark}")
        return "\n".join(lines)
