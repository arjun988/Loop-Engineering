"""Autonomy service — Tier 1 & 2 MCP tool implementations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .checker.brief import CheckerBriefBuilder
from .checklist.manager import ChecklistManager
from .deploy_verify import DeployVerifier
from .github_client import GitHubClient
from .github_ops.ci_ingest import CIFailureIngester
from .github_ops.merge_risk import MergeRiskEvaluator
from .github_ops.pr_review import PRReviewManager
from .hidden_verify import HiddenVerifyManager
from .loop_manager import LoopManager
from .meta.simulator import LoopSimulator
from .meta.skill_patch import SkillPatchManager
from .policy.manager import PolicyManager
from .probes.runner import ProbeRunner
from .scoring.les import LESScorer
from .scoring.trajectory import TrajectoryScorer
from .skill_manager import SkillManager
from .state_manager import StateManager


class AutonomyService:
    """Wires scoring, checker, checklist, GitHub ops, and deploy verification."""

    def __init__(
        self,
        workspace_root: Path,
        loop_dir: Path,
        loop_manager: LoopManager,
        skill_manager: SkillManager,
        state_manager: StateManager,
        github_client: Optional[GitHubClient] = None,
    ):
        self.workspace_root = workspace_root
        self.loop_manager = loop_manager
        self.skill_manager = skill_manager
        self.state_manager = state_manager
        self.github = github_client or GitHubClient()

        state_dir = loop_dir / "state"
        self.les = LESScorer(state_dir)
        self.checker = CheckerBriefBuilder()
        self.checklist = ChecklistManager(state_dir, workspace_root)
        self.hidden = HiddenVerifyManager(state_dir, workspace_root)
        self.ci = CIFailureIngester()
        self.merge_risk = MergeRiskEvaluator(self.les)
        self.pr_review = PRReviewManager(state_dir)
        self.deploy = DeployVerifier()
        self.probes = ProbeRunner(workspace_root)
        self.policy = PolicyManager()
        self.trajectory = TrajectoryScorer(loop_dir / "logs")
        self.skill_patches = SkillPatchManager(state_dir, skill_manager.skills_dir)
        self.simulator = LoopSimulator()

    async def score_loop(self, name: str) -> str:
        loops = await self.loop_manager._load_loops()
        if name not in loops:
            return f"❌ Loop '{name}' not found."
        state = await self.state_manager._load_state(name)
        return self.les.format_loop_report(name, loops[name], state)

    async def score_run(self, loop_name: str, run_id: str) -> str:
        state = await self.state_manager._load_state(loop_name)
        return self.les.format_run_report(loop_name, run_id, state)

    async def get_autonomy_report(self, days: int = 7) -> str:
        return await self.les.autonomy_report(days=days)

    async def spawn_checker(self, loop_name: str, run_id: str) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        state = await self.state_manager._load_state(loop_name)
        active = state.get("active_run")
        if not active or active.get("run_id") != run_id:
            return f"❌ No active run `{run_id}` for '{loop_name}'."

        cfg = loops[loop_name]
        workdir = active.get("worktree") or str(self.workspace_root)
        changed = self.checker.get_changed_files(workdir)
        skill = await self._read_skill(loop_name)

        return self.checker.build_brief(
            loop_name=loop_name,
            run_id=run_id,
            goal=cfg.get("goal", ""),
            workdir=workdir,
            verification_command=cfg.get("verification_command", ""),
            skill_excerpt=skill,
            changed_files=changed,
            forbidden_paths=cfg.get("forbidden_paths"),
        )

    async def submit_checker_verdict(
        self,
        loop_name: str,
        run_id: str,
        verdict: str,
        checks_json: str = "",
    ) -> str:
        state = await self.state_manager._load_state(loop_name)
        active = state.get("active_run")
        if not active or active.get("run_id") != run_id:
            return f"❌ No active run `{run_id}` for '{loop_name}'."

        if checks_json:
            parsed, _ = self.checker.parse_verdict(checks_json)
            verdict = parsed

        verdict = verdict.upper()
        if verdict not in ("PASS", "REJECT", "ESCALATE"):
            verdict = "REJECT"

        active["checker_verdict"] = verdict
        state["last_checker_verdict"] = verdict
        state["active_run"] = active
        await self.state_manager._save_state(loop_name, state)

        if verdict == "PASS":
            return (
                f"✅ Checker verdict **PASS** recorded for `{run_id}`.\n"
                "Call `complete_loop_run` again to continue PR flow."
            )
        if verdict == "ESCALATE":
            await self.state_manager.record_escalation(
                loop_name, f"Checker escalated run {run_id}"
            )
            return f"🚨 Checker **ESCALATE** — human review required for `{run_id}`."
        return (
            f"❌ Checker **REJECT** for `{run_id}`.\n"
            "Fix issues and call `complete_loop_run` then `submit_checker_verdict` again."
        )

    async def configure_hidden_verify(self, loop_name: str, command: str) -> str:
        async def save(name: str, patch: dict):
            loops = await self.loop_manager._load_loops()
            loops[name].update(patch)
            await self.loop_manager._save_loops(loops)

        return await self.hidden.configure(loop_name, command, save)

    async def run_hidden_verify(self, loop_name: str, workdir: Optional[str] = None) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        cmd = loops[loop_name].get("hidden_verify_command", "")
        passed, output = await self.hidden.run(loop_name, cmd, workdir=workdir)
        mark = "✅" if passed else "❌"
        return f"{mark} **Hidden verify: {loop_name}**\n```\n{output[:2000]}\n```"

    async def view_hidden_metrics(self, loop_name: str) -> str:
        return await self.hidden.view_metrics(loop_name)

    async def init_checklist(self, loop_name: str, features: list) -> str:
        return await self.checklist.init_checklist(loop_name, features)

    async def mark_feature(
        self, loop_name: str, feature_id: str, passes: bool, evidence: str = ""
    ) -> str:
        state = await self.state_manager._load_state(loop_name)
        workdir = None
        if state.get("active_run"):
            workdir = state["active_run"].get("worktree")
        return await self.checklist.mark_feature(
            loop_name, feature_id, passes=passes, evidence=evidence, workdir=workdir
        )

    async def checklist_status(self, loop_name: str) -> str:
        return await self.checklist.status(loop_name)

    async def evaluate_merge_risk(
        self, loop_name: str, pr_number: int, min_risk_score: float = 85.0
    ) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        if not self.github.token:
            return "❌ GITHUB_TOKEN required for merge risk evaluation."

        state = await self.state_manager._load_state(loop_name)
        pr = await self.github.get_pull_request(pr_number)
        files = await self.github.get_pr_files(pr_number)
        comments = await self.github.get_pr_comments(pr_number)
        checks = await self.github.get_check_runs_for_ref(pr.get("head", {}).get("ref", ""))

        result = self.merge_risk.evaluate(
            loop_config=loops[loop_name],
            state=state,
            pr_data=pr,
            checks=checks,
            files=files,
            comments=comments,
            min_score=min_risk_score,
        )
        return self.merge_risk.format_report(result, pr_number)

    async def auto_merge(
        self, loop_name: str, pr_number: int, min_risk_score: float = 85.0
    ) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."

        policy = loops[loop_name].get("merge_policy", "human")
        if policy != "auto_low_risk":
            return (
                f"❌ Auto-merge disabled for '{loop_name}' (merge_policy={policy}).\n"
                "Set merge_policy to `auto_low_risk` to enable."
            )

        threshold = float(loops[loop_name].get("merge_risk_threshold", min_risk_score))
        state = await self.state_manager._load_state(loop_name)
        pr = await self.github.get_pull_request(pr_number)
        files = await self.github.get_pr_files(pr_number)
        comments = await self.github.get_pr_comments(pr_number)
        checks = await self.github.get_check_runs_for_ref(pr.get("head", {}).get("ref", ""))
        risk = self.merge_risk.evaluate(
            loop_config=loops[loop_name],
            state=state,
            pr_data=pr,
            checks=checks,
            files=files,
            comments=comments,
            min_score=threshold,
        )
        report = self.merge_risk.format_report(risk, pr_number)
        if not risk.passed:
            return report + "\n\n❌ Merge blocked by risk score."

        ok, msg = await self.github.merge_pull_request(pr_number)
        if ok:
            state = await self.state_manager._load_state(loop_name)
            metrics = state.setdefault("metrics", {})
            metrics["prs_merged"] = metrics.get("prs_merged", 0) + 1
            opened = metrics.get("prs_opened", 0)
            metrics["acceptance_rate"] = metrics["prs_merged"] / opened if opened else 0.0
            await self.state_manager._save_state(loop_name, state)

            deploy_check = loops[loop_name].get("deploy_check")
            if deploy_check:
                deploy_result = await self.verify_deploy(loop_name)
                return f"{report}\n\n✅ **Merged.**\n{msg}\n\n{deploy_result}"
            return f"{report}\n\n✅ **Merged.**\n{msg}"
        return f"{report}\n\n❌ Merge failed: {msg}"

    async def ingest_ci_failures(
        self, branch: str, repo: Optional[str] = None
    ) -> str:
        if not self.github.token:
            return "❌ GITHUB_TOKEN required for CI ingestion."
        failures = await self.ci.ingest_from_checks(self.github, branch=branch, repo=repo)
        return self.ci.format_ingest_report(failures, branch)

    async def classify_failure(self, log: str, check_name: str = "unknown") -> str:
        failure = self.ci.classify_failure(log, check_name=check_name)
        return self.ci.format_classification(failure)

    async def create_loop_from_failure(
        self,
        check: str,
        log: str,
        branch: str = "main",
    ) -> str:
        failure = self.ci.classify_failure(log, check_name=check)
        config = self.ci.suggest_loop_config(failure, branch)
        result = await self.loop_manager.create_loop(**config)
        await self.skill_manager.create_skill(
            name=config["name"],
            description=config["description"],
            instructions=config["skill_instructions"],
        )
        await self.state_manager.initialize_state(config["name"])
        return result + f"\n\n**Classification:** `{failure.classification}`"

    async def review_pr(self, pr_number: int) -> str:
        if not self.github.token:
            return "❌ GITHUB_TOKEN required for PR review."
        pr = await self.github.get_pull_request(pr_number)
        files = await self.github.get_pr_files(pr_number)
        stats = await self.github.get_pr_diff_stats(pr_number)
        return self.pr_review.build_review_brief(
            pr_number=pr_number,
            title=pr.get("title", ""),
            body=pr.get("body", "") or "",
            files=files,
            diff_stats=stats,
        )

    async def post_review_verdict(
        self,
        pr_number: int,
        verdict: str,
        confidence: float,
        comments: list[str],
        loop_name: Optional[str] = None,
    ) -> str:
        return await self.pr_review.post_verdict(
            pr_number=pr_number,
            verdict=verdict,
            confidence=confidence,
            comments=comments,
            loop_name=loop_name,
            github_client=self.github,
        )

    async def configure_deploy_check(
        self, loop_name: str, url: str, markers: list[str], timeout: float = 30.0
    ) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        loops[loop_name]["deploy_check"] = {
            "url": url,
            "markers": markers,
            "timeout": timeout,
        }
        await self.loop_manager._save_loops(loops)
        return (
            f"✅ Deploy check configured for '{loop_name}'.\n"
            f"**URL:** {url}\n**Markers:** {markers}"
        )

    async def verify_deploy(self, loop_name: str) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        deploy_check = loops[loop_name].get("deploy_check")
        if not deploy_check:
            return f"⚠️ No deploy check configured for '{loop_name}'."
        passed, detail = await self.deploy.verify(deploy_check)
        return self.deploy.format_result(loop_name, passed, detail)

    async def _read_skill(self, loop_name: str) -> str:
        skill_file = self.skill_manager.skills_dir / f"{loop_name}.md"
        if skill_file.exists():
            return skill_file.read_text(encoding="utf-8")
        loops = await self.loop_manager._load_loops()
        return loops.get(loop_name, {}).get("skill_instructions", "")

    async def update_loop_config(self, loop_name: str, **kwargs: Any) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        loops[loop_name].update(kwargs)
        await self.loop_manager._save_loops(loops)
        return f"✅ Updated config for '{loop_name}': {', '.join(kwargs.keys())}"

    # --- Tier 3: Probes ---
    async def define_probes(self, loop_name: str, probes: list[dict]) -> str:
        await self.update_loop_config(loop_name, probes=probes)
        types = ", ".join(p.get("type", "?") for p in probes)
        return (
            f"✅ **Probes configured for '{loop_name}'** ({len(probes)} probes)\n"
            f"Types: {types}\n"
            "Runs automatically in `complete_loop_run` before the checker."
        )

    async def run_probes(self, loop_name: str, workdir: Optional[str] = None) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        state = await self.state_manager._load_state(loop_name)
        active = state.get("active_run") or {}
        cwd = workdir or active.get("worktree") or str(self.workspace_root)
        probes = loops[loop_name].get("probes") or []
        ok, results = await self.probes.run_all(probes, cwd)
        report = self.probes.format_report(loop_name, results)
        return report

    # --- Tier 3: Policy ---
    async def define_policy(self, loop_name: str, policy: dict) -> str:
        normalized = self.policy.normalize_policy(policy)
        await self.update_loop_config(loop_name, policy=normalized)
        return (
            f"✅ **Policy configured for '{loop_name}'**\n"
            f"- deny_paths: {normalized.get('deny_paths')}\n"
            f"- deny_commands: {len(normalized.get('deny_commands', []))} patterns\n"
            f"- max_files_per_run: {normalized.get('max_files_per_run')}"
        )

    async def check_action(
        self,
        loop_name: str,
        tool: str,
        args: dict,
        changed_files: Optional[list[str]] = None,
    ) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        files = changed_files
        if files is None:
            state = await self.state_manager._load_state(loop_name)
            workdir = (state.get("active_run") or {}).get("worktree") or str(
                self.workspace_root
            )
            files = self.checker.get_changed_files(workdir)
        decision, detail = self.policy.check_action(
            loops[loop_name].get("policy") or {},
            tool=tool,
            args=args,
            changed_files=files,
        )
        if decision in ("deny", "escalate"):
            await self.state_manager.record_policy_violation(loop_name, detail)
        return self.policy.format_decision(loop_name, decision, detail)

    async def record_policy_violation(self, loop_name: str, detail: str) -> str:
        await self.state_manager.record_policy_violation(loop_name, detail)
        return f"📝 Policy violation recorded for '{loop_name}': {detail}"

    # --- Tier 4: Trajectory ---
    async def score_trajectory(self, loop_name: str, run_id: str) -> str:
        score = self.trajectory.score(run_id)
        if not score.events:
            return (
                f"ℹ️ No trajectory events for run `{run_id}`.\n"
                f"Events are logged during `complete_loop_run` iterations."
            )
        return self.trajectory.format_report(loop_name, run_id, score)

    # --- Tier 4: Skill patches ---
    async def propose_skill_patch(
        self, loop_name: str, min_escalations: int = 3, days: int = 7
    ) -> str:
        state = await self.state_manager._load_state(loop_name)
        return await self.skill_patches.propose(
            loop_name, state, min_escalations=min_escalations, days=days
        )

    async def apply_skill_patch(self, loop_name: str, patch_id: str) -> str:
        return await self.skill_patches.apply(loop_name, patch_id)

    async def list_skill_patches(self, loop_name: Optional[str] = None) -> str:
        return await self.skill_patches.list_proposals(loop_name)

    # --- Tier 4: Simulation ---
    async def simulate_loop(self, loop_name: str, fixture: str) -> str:
        loops = await self.loop_manager._load_loops()
        if loop_name not in loops:
            return f"❌ Loop '{loop_name}' not found."
        try:
            result = self.simulator.simulate(loops[loop_name], fixture)
        except ValueError as e:
            fixtures = ", ".join(self.simulator.list_fixtures())
            return f"❌ {e}\n\n**Available fixtures:** {fixtures}"
        return self.simulator.format_report(loop_name, result)

    async def list_simulation_fixtures(self) -> str:
        from .meta.simulator import FIXTURES

        lines = ["🧪 **Simulation fixtures**\n"]
        for name, meta in FIXTURES.items():
            lines.append(f"- `{name}` — {meta['description']}")
        return "\n".join(lines)
