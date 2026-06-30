"""Propose skill patches from repeated escalation patterns."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import aiofiles


class SkillPatchManager:
    """Draft skill additions from escalation evidence — human approves before apply."""

    def __init__(self, state_dir: Path, skills_dir: Path):
        self.state_dir = state_dir
        self.skills_dir = skills_dir
        self.patches_file = state_dir / "skill-patches.json"

    async def _load_patches(self) -> dict:
        if not self.patches_file.exists():
            return {"patches": []}
        async with aiofiles.open(self.patches_file, "r") as f:
            return json.loads(await f.read())

    async def _save_patches(self, data: dict) -> None:
        async with aiofiles.open(self.patches_file, "w") as f:
            await f.write(json.dumps(data, indent=2))

    def _group_escalations(self, state: dict, days: int = 7) -> dict[str, int]:
        cutoff = datetime.now() - timedelta(days=days)
        counts: dict[str, int] = {}
        for esc in state.get("escalations", []):
            ts = esc.get("timestamp")
            reason = esc.get("reason", "unknown")
            if not ts:
                continue
            try:
                if datetime.fromisoformat(ts) < cutoff:
                    continue
            except ValueError:
                continue
            sig = reason[:120]
            counts[sig] = counts.get(sig, 0) + 1
        return counts

    def _draft_addition(self, loop_name: str, signature: str, count: int) -> str:
        return (
            f"\n\n## Lesson from automated analysis ({datetime.now().strftime('%Y-%m-%d')})\n"
            f"Escalation pattern ({count}x in 7d): {signature}\n\n"
            "**Add to every run:**\n"
            f"- Before marking done for `{loop_name}`, verify this failure mode cannot recur.\n"
            f"- If you see: `{signature[:200]}` → stop and escalate with `add_lesson`.\n"
        )

    async def propose(
        self,
        loop_name: str,
        state: dict,
        *,
        min_escalations: int = 3,
        days: int = 7,
    ) -> str:
        groups = self._group_escalations(state, days=days)
        hot = [(sig, cnt) for sig, cnt in groups.items() if cnt >= min_escalations]

        if not hot:
            return (
                f"ℹ️ **No skill patch proposed for '{loop_name}'**\n"
                f"Need ≥{min_escalations} escalations with the same signature in {days}d."
            )

        sig, count = max(hot, key=lambda x: x[1])
        patch_id = str(uuid.uuid4())[:8]
        addition = self._draft_addition(loop_name, sig, count)

        data = await self._load_patches()
        entry = {
            "patch_id": patch_id,
            "loop_name": loop_name,
            "signature": sig,
            "escalation_count": count,
            "addition": addition,
            "status": "proposed",
            "proposed_at": datetime.now().isoformat(),
        }
        data.setdefault("patches", []).append(entry)
        await self._save_patches(data)

        return (
            f"📝 **Skill patch proposed: `{patch_id}`** for '{loop_name}'\n"
            f"**Trigger:** {count} escalations matching:\n> {sig[:300]}\n\n"
            f"**Draft addition:**\n```markdown\n{addition.strip()}\n```\n\n"
            f"Call `apply_skill_patch` with patch_id after human review."
        )

    async def apply(self, loop_name: str, patch_id: str) -> str:
        data = await self._load_patches()
        patch: Optional[dict[str, Any]] = None
        for p in data.get("patches", []):
            if p.get("patch_id") == patch_id and p.get("loop_name") == loop_name:
                patch = p
                break

        if not patch:
            return f"❌ Patch `{patch_id}` not found for loop '{loop_name}'."

        if patch.get("status") == "applied":
            return f"⚠️ Patch `{patch_id}` already applied."

        skill_file = self.skills_dir / f"{loop_name}.md"
        if not skill_file.exists():
            return f"❌ Skill file not found: {skill_file}"

        content = skill_file.read_text(encoding="utf-8")
        addition = patch.get("addition", "")
        if addition.strip() in content:
            return "⚠️ Patch content already present in skill."

        skill_file.write_text(content.rstrip() + addition, encoding="utf-8")
        patch["status"] = "applied"
        patch["applied_at"] = datetime.now().isoformat()
        await self._save_patches(data)

        return (
            f"✅ **Patch `{patch_id}` applied** to `.loop/skills/{loop_name}.md`\n"
            "Future runs will include the new guidance."
        )

    async def list_proposals(self, loop_name: Optional[str] = None) -> str:
        data = await self._load_patches()
        patches = data.get("patches", [])
        if loop_name:
            patches = [p for p in patches if p.get("loop_name") == loop_name]
        if not patches:
            return "📝 No skill patches on file."
        lines = ["📝 **Skill patches**\n"]
        for p in patches[-10:]:
            lines.append(
                f"- `{p['patch_id']}` **{p['loop_name']}** — {p['status']} "
                f"({p.get('escalation_count', '?')} escalations)"
            )
        return "\n".join(lines)
