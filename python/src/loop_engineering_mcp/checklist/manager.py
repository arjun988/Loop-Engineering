"""Feature checklist state (Anthropic long-running agent pattern)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import aiofiles

from ..verification_runner import VerificationRunner


class ChecklistManager:
    """Manages per-loop feature checklists with orchestrator-enforced verification."""

    def __init__(self, state_dir: Path, workspace_root: Path):
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.verification_runner = VerificationRunner(workspace_root)

    def _path(self, loop_name: str) -> Path:
        return self.state_dir / f"{loop_name}-checklist.json"

    async def _load(self, loop_name: str) -> Optional[dict]:
        path = self._path(loop_name)
        if not path.exists():
            return None
        async with aiofiles.open(path, "r") as f:
            return json.loads(await f.read())

    async def _save(self, loop_name: str, data: dict) -> None:
        async with aiofiles.open(self._path(loop_name), "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def init_checklist(
        self, loop_name: str, features: list[dict[str, Any]]
    ) -> str:
        items = []
        for feat in features:
            fid = feat.get("id") or feat.get("feature_id")
            if not fid:
                continue
            items.append({
                "id": fid,
                "description": feat.get("description", ""),
                "verify_command": feat.get("verify_command", ""),
                "passes": False,
                "evidence": None,
                "updated_at": None,
            })
        if not items:
            return "❌ No valid features (each needs an `id`)."

        data = {
            "loop_name": loop_name,
            "created_at": datetime.now().isoformat(),
            "features": items,
        }
        await self._save(loop_name, data)
        return (
            f"✅ Checklist initialized for '{loop_name}' with {len(items)} features.\n"
            f"File: `.loop/state/{loop_name}-checklist.json`"
        )

    async def mark_feature(
        self,
        loop_name: str,
        feature_id: str,
        *,
        passes: bool,
        evidence: str = "",
        workdir: Optional[str] = None,
    ) -> str:
        data = await self._load(loop_name)
        if not data:
            return f"❌ No checklist for '{loop_name}'. Call init_checklist first."

        feature = next((f for f in data["features"] if f["id"] == feature_id), None)
        if not feature:
            return f"❌ Feature '{feature_id}' not found."

        if passes:
            cmd = (feature.get("verify_command") or "").strip()
            if cmd:
                result = await self.verification_runner.run(
                    cmd, cwd=Path(workdir) if workdir else None
                )
                if not result.success:
                    return (
                        f"❌ Cannot mark `{feature_id}` as passed — verify_command failed.\n"
                        f"```\n{result.stderr or result.stdout}\n```"
                    )
                evidence = evidence or (result.stdout or "verify_command passed")[:500]

        feature["passes"] = passes
        feature["evidence"] = evidence
        feature["updated_at"] = datetime.now().isoformat()
        await self._save(loop_name, data)

        status = "✅ passed" if passes else "⏸️ reset"
        return f"**Feature `{feature_id}`** marked {status}."

    async def status(self, loop_name: str) -> str:
        data = await self._load(loop_name)
        if not data:
            return f"📋 No checklist for '{loop_name}'."

        features = data["features"]
        passed = sum(1 for f in features if f.get("passes"))
        total = len(features)
        pct = (passed / total * 100) if total else 0

        lines = [
            f"📋 **Checklist: {loop_name}** — {passed}/{total} ({pct:.0f}%)\n",
        ]
        for feat in features:
            mark = "✅" if feat.get("passes") else "⬜"
            lines.append(f"{mark} **{feat['id']}** — {feat.get('description', '')[:80]}")
        if passed < total:
            lines.append("\n⚠️ PR blocked until all features pass.")
        else:
            lines.append("\n✅ All features pass — PR may proceed.")
        return "\n".join(lines)

    async def all_complete(self, loop_name: str) -> bool:
        data = await self._load(loop_name)
        if not data:
            return True
        return all(f.get("passes") for f in data.get("features", []))

    async def incomplete_message(self, loop_name: str) -> str:
        data = await self._load(loop_name)
        if not data:
            return ""
        pending = [f["id"] for f in data["features"] if not f.get("passes")]
        if not pending:
            return ""
        return f"Checklist incomplete: {', '.join(pending)}"
