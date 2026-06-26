"""Orchestrates loop runs via the host agent (Cursor/Kiro) — no external AI API calls."""

import json
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from .github_client import GitHubClient
from .logger import LoopLogger
from .loop_manager import LoopManager
from .skill_manager import SkillManager
from .state_manager import StateManager
from .verification_runner import VerificationRunner


class LoopExecutor:
    """Prepares loop runs for the host agent and finalizes them after execution."""

    def __init__(
        self,
        workspace_root: Path,
        loop_manager: LoopManager,
        skill_manager: SkillManager,
        state_manager: StateManager,
        logger: LoopLogger,
    ):
        self.workspace_root = workspace_root
        self.loop_manager = loop_manager
        self.skill_manager = skill_manager
        self.state_manager = state_manager
        self.logger = logger
        self.verification_runner = VerificationRunner(workspace_root)
        self.github_client = GitHubClient()

    async def _read_skill(self, loop_name: str) -> str:
        skill_file = self.skill_manager.skills_dir / f"{loop_name}.md"
        if skill_file.exists():
            async with aiofiles.open(skill_file, "r") as f:
                return await f.read()
        loops = await self.loop_manager._load_loops()
        return loops.get(loop_name, {}).get("skill_instructions", "")

    async def _build_brief(self, loop_name: str, run_id: str, branch: Optional[str]) -> str:
        loops = await self.loop_manager._load_loops()
        loop_config = loops[loop_name]
        state = await self.state_manager._load_state(loop_name)
        skill_content = await self._read_skill(loop_name)
        lessons = state.get("lessons_learned", [])
        lessons_text = "\n".join(f"- {l}" for l in lessons[-10:]) if lessons else "None yet."

        branch_line = f"**Branch:** `{branch}`\n" if branch else ""
        return f"""🔄 **Loop run started: {loop_name}** (run_id: `{run_id}`)

You (the host agent in Cursor/Kiro) execute this loop — no external API keys needed.
Make the code changes in the workspace, then call `complete_loop_run` with this run_id.

{branch_line}**Goal:** {loop_config['goal']}

**Verification command:** `{loop_config.get('verification_command', 'none')}`

---

## Skill Instructions

{skill_content}

---

## Lessons Learned (from previous runs)

{lessons_text}

---

## When done

1. Make all required code changes in the workspace
2. Call `complete_loop_run` with:
   - `loop_name`: "{loop_name}"
   - `run_id`: "{run_id}"
   - `summary`: brief description of what you changed
"""

    def _has_git_changes(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace_root),
            )
            return bool(result.stdout.strip())
        except Exception:
            return False

    def _create_branch(self, loop_name: str) -> tuple[bool, str]:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch = f"loop/{loop_name}-{timestamp}"
        try:
            subprocess.run(
                ["git", "checkout", "-b", branch],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.workspace_root),
                check=True,
            )
            return True, branch
        except subprocess.CalledProcessError as e:
            return False, e.stderr or str(e)

    async def begin_run(self, loop_name: str, *, create_pr: bool = True) -> str:
        """Prepare a loop run and return instructions for the host agent to execute."""
        run_id = str(uuid.uuid4())[:8]
        self.logger.info("loop_run_started", loop_name, run_id=run_id)

        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."

        state = await self.state_manager._load_state(loop_name)
        if state.get("active_run"):
            active = state["active_run"]
            return (
                f"⏳ Loop '{loop_name}' already has an active run "
                f"(run_id: `{active.get('run_id')}`). "
                f"Complete it with `complete_loop_run` first."
            )

        branch = None
        if create_pr:
            ok, branch_or_err = self._create_branch(loop_name)
            if ok:
                branch = branch_or_err
            else:
                self.logger.warning("branch_creation_failed", loop_name, error=branch_or_err)

        await self.state_manager.set_active_run(
            loop_name, run_id=run_id, branch=branch, create_pr=create_pr
        )
        await self.state_manager.remove_pending_run(loop_name)

        brief = await self._build_brief(loop_name, run_id, branch)
        self.logger.info("loop_brief_ready", loop_name, run_id=run_id)
        return brief

    async def queue_run(self, loop_name: str) -> str:
        """Queue a loop for the next host agent session (used by scheduler)."""
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."

        state = await self.state_manager._load_state(loop_name)
        if state.get("active_run"):
            return f"⏳ Loop '{loop_name}' already has an active run — skipping queue."

        run_id = str(uuid.uuid4())[:8]
        await self.state_manager.queue_pending_run(loop_name, run_id, source="schedule")
        self.logger.info("loop_queued", loop_name, run_id=run_id)

        return (
            f"📋 Loop '{loop_name}' queued (run_id: `{run_id}`).\n"
            f"Call `list_pending_runs` then `run_loop_now` when a host agent session is active."
        )

    async def complete_run(
        self,
        loop_name: str,
        run_id: str,
        summary: str,
        *,
        create_pr: Optional[bool] = None,
    ) -> str:
        """Finalize a loop run after the host agent has made changes."""
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."

        state = await self.state_manager._load_state(loop_name)
        active = state.get("active_run")
        if not active or active.get("run_id") != run_id:
            return f"❌ No active run with run_id `{run_id}` for loop '{loop_name}'."

        loop_config = loops[loop_name]
        should_create_pr = create_pr if create_pr is not None else active.get("create_pr", True)
        branch = active.get("branch")

        verification_passed = False
        pr_result = None
        status = "failed"
        error_msg: Optional[str] = None

        try:
            verification_cmd = loop_config.get("verification_command", "")
            self.logger.info("verification_started", loop_name, command=verification_cmd)
            verification = await self.verification_runner.run(verification_cmd)
            verification_passed = verification.success

            if not verification_passed:
                status = "verification_failed"
                error_msg = verification.stderr or f"Exit code {verification.exit_code}"
                await self.state_manager.record_escalation(
                    loop_name, f"Verification failed: {error_msg}"
                )
            else:
                has_changes = self._has_git_changes()
                if should_create_pr and has_changes and branch:
                    subprocess.run(
                        ["git", "add", "-A"],
                        cwd=str(self.workspace_root),
                        capture_output=True,
                        timeout=30,
                    )
                    subprocess.run(
                        ["git", "commit", "-m", f"loop({loop_name}): automated changes"],
                        cwd=str(self.workspace_root),
                        capture_output=True,
                        timeout=30,
                    )
                    push_ok, push_msg = await self.github_client.push_branch(
                        branch, cwd=str(self.workspace_root)
                    )
                    if push_ok:
                        pr_result = await self.github_client.create_pull_request(
                            title=f"[loop] {loop_name}: {loop_config['description'][:60]}",
                            body=(
                                f"Automated loop run.\n\n**Goal:** {loop_config['goal']}\n\n"
                                f"**Summary:**\n{summary[:2000]}"
                            ),
                            branch=branch,
                        )
                        status = "success" if pr_result.success else "pr_failed"
                        if not pr_result.success:
                            error_msg = pr_result.error
                    else:
                        status = "push_failed"
                        error_msg = push_msg
                elif has_changes:
                    status = "success"
                else:
                    status = "success_no_changes"

        except Exception as e:
            status = "error"
            error_msg = str(e)
            self.logger.error("loop_run_failed", loop_name, run_id=run_id, error=error_msg)
            await self.state_manager.record_escalation(loop_name, f"Run error: {error_msg}")

        final_summary = summary
        if error_msg:
            final_summary = f"{summary} ({status}: {error_msg})"

        await self.state_manager.record_run(
            loop_name,
            summary=final_summary,
            status=status,
            verification_passed=verification_passed,
            pr_url=pr_result.pr_url if pr_result and pr_result.success else None,
        )
        await self.state_manager.clear_active_run(loop_name)

        loops = await self.loop_manager._load_loops()
        if loop_name in loops:
            loops[loop_name]["last_run"] = datetime.now().isoformat()
            await self.loop_manager._save_loops(loops)

        self.logger.run_log(
            loop_name,
            run_id,
            {
                "status": status,
                "verification_passed": verification_passed,
                "pr_url": pr_result.pr_url if pr_result else None,
                "error": error_msg,
            },
        )

        output = [
            f"✅ **Loop run complete: {loop_name}** (run_id: {run_id})",
            f"**Status:** {status}",
            f"**Verification:** {'✅ Passed' if verification_passed else '❌ Failed'}",
        ]
        if pr_result and pr_result.success:
            output.append(f"**PR:** {pr_result.pr_url}")
        if error_msg:
            output.append(f"**Error:** {error_msg}")

        return "\n".join(output)

    # Backward-compatible alias: begin_run (not full autonomous execution)
    async def run(self, loop_name: str, *, create_pr: bool = True) -> str:
        return await self.begin_run(loop_name, create_pr=create_pr)
