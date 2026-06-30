"""Orchestrates loop runs via the host agent (Cursor/Kiro) — no external AI API calls.

This module implements the loop-engineering control system around the host agent:
isolation (git worktree), an independent maker/checker verification gate, an
iterate-until-goal cycle with explicit stop rules (max attempts + no-progress
detection), and budget caps. The host agent is the "maker"; the deterministic
verification + goal-check commands are the "checker" that owns the stop authority.
"""

import shutil
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles

from .checker.brief import CheckerBriefBuilder
from .checklist.manager import ChecklistManager
from .github_client import GitHubClient
from .hidden_verify import HiddenVerifyManager
from .logger import LoopLogger
from .loop_manager import LoopManager
from .policy.manager import PolicyManager
from .probes.runner import ProbeRunner
from .scoring.trajectory import TrajectoryScorer
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
        self.checklist = ChecklistManager(state_manager.state_dir, workspace_root)
        self.hidden_verify = HiddenVerifyManager(state_manager.state_dir, workspace_root)
        self.checker = CheckerBriefBuilder()
        self.probes = ProbeRunner(workspace_root)
        self.policy = PolicyManager()
        self.trajectory = TrajectoryScorer(logger.logs_dir)

    def _log_traj(self, run_id: str, event: str, **fields) -> None:
        from datetime import datetime, timezone

        self.trajectory.append_event(
            run_id,
            {"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **fields},
        )

    async def _read_skill(self, loop_name: str) -> str:
        skill_file = self.skill_manager.skills_dir / f"{loop_name}.md"
        if skill_file.exists():
            async with aiofiles.open(skill_file, "r") as f:
                return await f.read()
        loops = await self.loop_manager._load_loops()
        return loops.get(loop_name, {}).get("skill_instructions", "")

    async def _build_brief(
        self,
        loop_name: str,
        run_id: str,
        branch: Optional[str],
        worktree: Optional[str],
        max_attempts: int,
    ) -> str:
        loops = await self.loop_manager._load_loops()
        loop_config = loops[loop_name]
        state = await self.state_manager._load_state(loop_name)
        skill_content = await self._read_skill(loop_name)
        lessons = state.get("lessons_learned", [])
        lessons_text = "\n".join(f"- {ln}" for ln in lessons[-10:]) if lessons else "None yet."

        workdir = worktree or str(self.workspace_root)
        branch_line = f"**Branch:** `{branch}`\n" if branch else ""
        goal_check = loop_config.get("goal_check_command") or "(falls back to verification)"

        return f"""🔄 **Loop run started: {loop_name}** (run_id: `{run_id}`)

You (the host agent in Cursor/Kiro) are the **maker** in this loop — no external API keys needed.
A separate, deterministic **checker** (the commands below) decides whether the goal is met.

{branch_line}**Working directory (make ALL changes here):** `{workdir}`

**Goal:** {loop_config['goal']}

**Maker self-check (verification):** `{loop_config.get('verification_command', 'none')}`
**Checker gate (independent goal check):** `{goal_check}`

**Stop rule:** the loop escalates to a human after **{max_attempts} attempts** or if the
same failure repeats (no-progress detection). Do not loop on the same dead end.

---

## Skill Instructions

{skill_content}

---

## Lessons Learned (from previous runs)

{lessons_text}

---

## The loop (iterate until the goal is verifiably met)

1. Make the smallest change that moves toward the goal — in the working directory above.
2. Call `complete_loop_run` with `loop_name`, `run_id` (`{run_id}`), and a `summary`.
3. The checker runs automatically:
   - ✅ If verification **and** the goal check pass → a PR is opened and the loop ends.
   - 🔁 If they fail and attempts remain → you get the failure output; fix it and call
     `complete_loop_run` again with the **same** run_id (this is the next iteration).
   - 🚨 After {max_attempts} attempts or a repeated failure → the loop stops
     and escalates to a human instead of burning tokens.
"""

    # ------------------------------------------------------------------ #
    # Isolation: git worktree (preferred) with branch fallback
    # ------------------------------------------------------------------ #
    def _git(self, *args: str, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=cwd or str(self.workspace_root),
        )

    def _has_git_changes(self, cwd: Optional[str] = None) -> bool:
        try:
            result = self._git("status", "--porcelain", cwd=cwd)
            return bool(result.stdout.strip())
        except Exception:
            return False

    def _worktrees_root(self) -> Path:
        # Keep worktrees outside the repo to avoid polluting the tracked tree.
        return self.workspace_root.parent / ".loop-worktrees"

    def _create_isolation(self, loop_name: str, isolation: str) -> tuple[Optional[str], Optional[str], Optional[str]]:
        """Create an isolated workspace for the run.

        Returns (branch, worktree_path, error). When isolation == 'worktree' the
        host agent works inside a dedicated git worktree so parallel loops never
        collide. Falls back to a branch in the main tree if worktrees are unavailable.
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        branch = f"loop/{loop_name}-{timestamp}"

        if isolation == "worktree":
            wt_root = self._worktrees_root()
            wt_root.mkdir(parents=True, exist_ok=True)
            wt_path = wt_root / f"{loop_name}-{timestamp}"
            result = self._git("worktree", "add", "-b", branch, str(wt_path))
            if result.returncode == 0:
                return branch, str(wt_path), None
            self.logger.warning(
                "worktree_creation_failed", loop_name, error=result.stderr or result.stdout
            )
            # fall through to branch isolation

        result = self._git("checkout", "-b", branch)
        if result.returncode == 0:
            return branch, None, None
        return None, None, result.stderr or result.stdout

    def _cleanup_isolation(self, worktree: Optional[str]) -> None:
        if not worktree:
            return
        try:
            self._git("worktree", "remove", "--force", worktree)
        except Exception:
            pass
        # Best-effort directory cleanup if git left anything behind.
        try:
            p = Path(worktree)
            if p.exists():
                shutil.rmtree(p, ignore_errors=True)
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Run lifecycle
    # ------------------------------------------------------------------ #
    async def begin_run(self, loop_name: str, *, create_pr: bool = True) -> str:
        """Prepare a loop run and return instructions for the host agent to execute."""
        run_id = str(uuid.uuid4())[:8]
        self.logger.info("loop_run_started", loop_name, run_id=run_id)

        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."

        loop_config = loops[loop_name]
        state = await self.state_manager._load_state(loop_name)
        if state.get("active_run"):
            active = state["active_run"]
            return (
                f"⏳ Loop '{loop_name}' already has an active run "
                f"(run_id: `{active.get('run_id')}`, attempt "
                f"{active.get('attempt', 1)}/{active.get('max_attempts', 3)}). "
                f"Continue it with `complete_loop_run`, or it must finish first."
            )

        # Budget cap: daily run limit (stop unbounded spend).
        max_runs = int(loop_config.get("max_runs_per_day", 24) or 0)
        if max_runs and self.state_manager.runs_today(state) >= max_runs:
            self.logger.warning("budget_exceeded", loop_name, max_runs_per_day=max_runs)
            return (
                f"💸 Daily budget reached for '{loop_name}' "
                f"({max_runs} runs/day). Skipping until tomorrow or raise `max_runs_per_day`."
            )

        # Budget cap: cumulative cost ceiling.
        cost_budget = float(loop_config.get("cost_budget", 0) or 0)
        spent = float(state.get("metrics", {}).get("total_token_cost", 0.0))
        if cost_budget and spent >= cost_budget:
            self.logger.warning("cost_budget_exceeded", loop_name, cost_budget=cost_budget)
            return (
                f"💸 Cost budget reached for '{loop_name}' "
                f"(${spent:.2f} / ${cost_budget:.2f}). Raise `cost_budget` to continue."
            )

        max_attempts = int(loop_config.get("max_attempts", 3) or 3)
        isolation = loop_config.get("isolation", "worktree")

        branch = None
        worktree = None
        if create_pr:
            branch, worktree, err = self._create_isolation(loop_name, isolation)
            if err:
                self.logger.warning("isolation_failed", loop_name, error=err)

        await self.state_manager.set_active_run(
            loop_name,
            run_id=run_id,
            branch=branch,
            create_pr=create_pr,
            worktree=worktree,
            max_attempts=max_attempts,
        )
        await self.state_manager.remove_pending_run(loop_name)

        brief = await self._build_brief(loop_name, run_id, branch, worktree, max_attempts)
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

    async def _run_gate(self, command: str, cwd: Optional[str]):
        return await self.verification_runner.run(command, cwd=Path(cwd) if cwd else None)

    async def complete_run(
        self,
        loop_name: str,
        run_id: str,
        summary: str,
        *,
        create_pr: Optional[bool] = None,
        token_cost: float = 0.0,
        checker_verdict: Optional[str] = None,
    ) -> str:
        """Finalize (or iterate) a loop run after the host agent has made changes.

        This is the loop body: the host agent calls it after each attempt. It runs
        the maker self-check then the independent checker gate, and applies the
        stop rules — opening a PR on success, asking for another iteration on a
        fresh failure, or escalating to a human on repeated/exhausted failure.
        """
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
        worktree = active.get("worktree")
        workdir = worktree or str(self.workspace_root)
        attempt = active.get("attempt", 1)
        max_attempts = active.get("max_attempts", int(loop_config.get("max_attempts", 3) or 3))

        verification_passed = False
        goal_met = False
        hidden_passed: Optional[bool] = None
        pr_result = None
        status = "failed"
        error_msg: Optional[str] = None
        run_started = active.get("started_at")

        try:
            self._log_traj(run_id, "attempt", attempt=attempt, detail=summary[:200])

            # --- Maker self-check ------------------------------------------------
            verification_cmd = loop_config.get("verification_command", "")
            self.logger.info("verification_started", loop_name, command=verification_cmd)
            verification = await self._run_gate(verification_cmd, workdir)
            verification_passed = verification.success
            self._log_traj(
                run_id, "verification", passed=verification_passed,
                exit_code=verification.exit_code,
            )

            # --- Independent checker gate (maker/checker separation) -------------
            goal_check_cmd = (loop_config.get("goal_check_command") or "").strip()
            if verification_passed and goal_check_cmd:
                self.logger.info("goal_check_started", loop_name, command=goal_check_cmd)
                goal_check = await self._run_gate(goal_check_cmd, workdir)
                goal_met = goal_check.success
                gate_output = goal_check.stderr or goal_check.stdout
                self._log_traj(run_id, "goal_check", passed=goal_met)
            else:
                # No independent checker configured → the verification IS the gate.
                goal_met = verification_passed
                gate_output = verification.stderr or f"Exit code {verification.exit_code}"

            if not goal_met:
                # ---- Failure path: iterate or escalate (the stop rule) ----------
                signature = self.state_manager.failure_signature(gate_output)
                progress = await self.state_manager.bump_attempt(loop_name, signature)
                repeated = progress["repeated_failure"]
                next_attempt = progress["attempt"]

                exhausted = next_attempt > max_attempts
                if repeated or exhausted:
                    reason = (
                        "no progress (identical failure twice)"
                        if repeated
                        else f"exhausted {max_attempts} attempts"
                    )
                    status = "verification_failed" if not verification_passed else "goal_not_met"
                    error_msg = f"{reason}: {gate_output[:500]}"
                    await self.state_manager.record_escalation(
                        loop_name, f"Loop stopped — {reason}."
                    )
                    await self.state_manager.record_run(
                        loop_name,
                        summary=f"{summary} (escalated after attempt {attempt}: {reason})",
                        status="escalated",
                        token_cost=token_cost,
                        verification_passed=verification_passed,
                        goal_met=False,
                        attempts=attempt,
                    )
                    await self.state_manager.clear_active_run(loop_name)
                    self._cleanup_isolation(worktree)
                    self.logger.run_log(
                        loop_name, run_id,
                        {"status": "escalated", "reason": reason, "attempt": attempt},
                    )
                    return (
                        f"🚨 **Loop escalated to human: {loop_name}** (run_id: {run_id})\n"
                        f"**Reason:** {reason}\n"
                        f"**Last gate output:**\n```\n{gate_output[:1500]}\n```\n"
                        f"Record what you learned with `add_lesson` before retrying."
                    )

                # Attempts remain and it's a *new* failure → ask for another iteration.
                self.logger.info(
                    "loop_iteration", loop_name, run_id=run_id, attempt=next_attempt
                )
                gate_name = "Verification" if not verification_passed else "Goal check"
                return (
                    f"🔁 **Iterate: {loop_name}** (run_id: {run_id}) — "
                    f"attempt {next_attempt}/{max_attempts}\n"
                    f"**{gate_name} failed:**\n```\n{gate_output[:1500]}\n```\n"
                    f"Fix the cause in `{workdir}`, then call `complete_loop_run` again "
                    f"with the same run_id (`{run_id}`)."
                )

            # --- Success path: extended gates before PR --------------------------
            changed_files = self.checker.get_changed_files(workdir)

            # Policy gate on diff (BOUND-style)
            policy = loop_config.get("policy") or {}
            decision, detail = self.policy.check_action(
                policy, tool="diff", args={}, changed_files=changed_files
            )
            self._log_traj(run_id, "policy", decision=decision, detail=detail)
            if decision == "deny":
                await self.state_manager.record_policy_violation(loop_name, detail)
                progress = await self.state_manager.bump_attempt(
                    loop_name, self.state_manager.failure_signature(detail)
                )
                return (
                    f"🚫 **Policy denied: {loop_name}** (run_id: {run_id})\n"
                    f"{detail}\n\n"
                    f"Attempt {progress['attempt']}/{max_attempts}. Fix and retry."
                )
            if decision == "escalate":
                await self.state_manager.record_policy_violation(loop_name, detail)
                await self.state_manager.record_escalation(loop_name, f"Policy: {detail}")
                await self.state_manager.clear_active_run(loop_name)
                return f"🚨 **Policy escalated: {loop_name}**\n{detail}"

            # Deterministic evidence probes (before checker — no tokens)
            probe_defs = loop_config.get("probes") or []
            if probe_defs:
                probes_ok, probe_results = await self.probes.run_all(probe_defs, workdir)
                self._log_traj(
                    run_id, "probes", passed=probes_ok,
                    detail=",".join(r.probe_type for r in probe_results),
                )
                if not probes_ok:
                    report = self.probes.format_report(loop_name, probe_results)
                    progress = await self.state_manager.bump_attempt(
                        loop_name,
                        self.state_manager.failure_signature(report),
                    )
                    if progress["attempt"] > max_attempts or progress["repeated_failure"]:
                        await self.state_manager.record_escalation(
                            loop_name, "Probes failed repeatedly"
                        )
                        await self.state_manager.clear_active_run(loop_name)
                        return f"🚨 **Probes failed: {loop_name}**\n\n{report}"
                    return (
                        f"🔁 **Probes failed** — attempt {progress['attempt']}/{max_attempts}\n\n"
                        f"{report}\n\nFix in `{workdir}` and call `complete_loop_run` again."
                    )

            # Hidden out-of-sample validation (never shown to maker)
            hidden_cmd = (loop_config.get("hidden_verify_command") or "").strip()
            if hidden_cmd:
                hidden_passed, hidden_out = await self.hidden_verify.run(
                    loop_name, hidden_cmd, workdir=workdir
                )
                if not hidden_passed:
                    gate_output = hidden_out
                    signature = self.state_manager.failure_signature(gate_output)
                    progress = await self.state_manager.bump_attempt(loop_name, signature)
                    if progress["attempt"] > max_attempts or progress["repeated_failure"]:
                        await self.state_manager.record_escalation(
                            loop_name, "Hidden verify failed repeatedly"
                        )
                        await self.state_manager.clear_active_run(loop_name)
                        return (
                            f"🚨 **Hidden verify failed: {loop_name}** (run_id: {run_id})\n"
                            f"```\n{hidden_out[:1500]}\n```"
                        )
                    return (
                        f"🔁 **Hidden verify failed** — attempt {progress['attempt']}/{max_attempts}\n"
                        f"```\n{hidden_out[:1500]}\n```\n"
                        f"Fix in `{workdir}` and call `complete_loop_run` again."
                    )

            # Feature checklist gate
            if not await self.checklist.all_complete(loop_name):
                pending = await self.checklist.incomplete_message(loop_name)
                return (
                    f"📋 **Checklist incomplete for '{loop_name}'**\n"
                    f"{pending}\n\n"
                    "Call `mark_feature` for each completed feature, then `complete_loop_run` again."
                )

            # LLM checker subagent gate
            verdict = (checker_verdict or active.get("checker_verdict") or "").upper()
            if self.checker.should_spawn_checker(loop_config, attempt, changed_files):
                if verdict == "ESCALATE":
                    await self.state_manager.record_escalation(
                        loop_name, f"Checker escalated run {run_id}"
                    )
                    await self.state_manager.clear_active_run(loop_name)
                    self._cleanup_isolation(worktree)
                    return f"🚨 Checker escalated run `{run_id}` — human review required."
                if verdict == "REJECT":
                    progress = await self.state_manager.bump_attempt(
                        loop_name, self.state_manager.failure_signature("checker_reject")
                    )
                    active["checker_verdict"] = None
                    state["active_run"] = active
                    await self.state_manager._save_state(loop_name, state)
                    return (
                        f"🔁 **Checker REJECT** — attempt {progress['attempt']}/{max_attempts}\n"
                        "Fix issues, then call `complete_loop_run` and `submit_checker_verdict`."
                    )
                if verdict != "PASS":
                    skill = await self._read_skill(loop_name)
                    return self.checker.build_brief(
                        loop_name=loop_name,
                        run_id=run_id,
                        goal=loop_config.get("goal", ""),
                        workdir=workdir,
                        verification_command=loop_config.get("verification_command", ""),
                        skill_excerpt=skill,
                        changed_files=changed_files,
                        forbidden_paths=loop_config.get("forbidden_paths"),
                    )

            has_changes = self._has_git_changes(cwd=workdir)
            if should_create_pr and has_changes and branch:
                self._git("add", "-A", cwd=workdir)
                self._git(
                    "commit", "-m", f"loop({loop_name}): automated changes", cwd=workdir
                )
                push_ok, push_msg = await self.github_client.push_branch(branch, cwd=workdir)
                if push_ok:
                    pr_result = await self.github_client.create_pull_request(
                        title=f"[loop] {loop_name}: {loop_config['description'][:60]}",
                        body=(
                            f"Automated loop run (goal verified by independent checker).\n\n"
                            f"**Goal:** {loop_config['goal']}\n\n"
                            f"**Attempts:** {attempt}\n\n"
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

        duration = None
        if run_started:
            try:
                started = datetime.fromisoformat(run_started)
                duration = (datetime.now() - started).total_seconds()
            except ValueError:
                pass

        await self.state_manager.record_run(
            loop_name,
            summary=final_summary,
            status=status,
            token_cost=token_cost,
            verification_passed=verification_passed,
            goal_met=goal_met,
            attempts=attempt,
            pr_url=pr_result.pr_url if pr_result and pr_result.success else None,
            run_id=run_id,
            checker_verdict=active.get("checker_verdict"),
            hidden_verify_passed=hidden_passed,
            used_worktree=bool(worktree),
            duration_seconds=duration,
        )
        await self.state_manager.clear_active_run(loop_name)
        self._cleanup_isolation(worktree)

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
                "goal_met": goal_met,
                "attempts": attempt,
                "pr_url": pr_result.pr_url if pr_result else None,
                "error": error_msg,
            },
        )

        output = [
            f"✅ **Loop run complete: {loop_name}** (run_id: {run_id})",
            f"**Status:** {status}",
            f"**Attempts:** {attempt}/{max_attempts}",
            f"**Verification:** {'✅ Passed' if verification_passed else '❌ Failed'}",
            f"**Goal met (checker):** {'✅ Yes' if goal_met else '❌ No'}",
        ]
        if hidden_passed is not None:
            output.append(f"**Hidden verify:** {'✅ Passed' if hidden_passed else '❌ Failed'}")
        if active.get("checker_verdict"):
            output.append(f"**Checker:** {active['checker_verdict']}")
        if pr_result and pr_result.success:
            output.append(f"**PR:** {pr_result.pr_url}")
        if error_msg:
            output.append(f"**Error:** {error_msg}")

        return "\n".join(output)

    # Backward-compatible alias: begin_run (not full autonomous execution)
    async def run(self, loop_name: str, *, create_pr: bool = True) -> str:
        return await self.begin_run(loop_name, create_pr=create_pr)
