"""State tracking and metrics for loops."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import aiofiles


class StateManager:
    """Manages loop state and execution history."""
    
    def __init__(self, state_dir: Path):
        """Initialize the state manager."""
        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)
    
    async def initialize_state(self, loop_name: str) -> str:
        """Initialize state for a new loop."""
        state_file = self.state_dir / f"{loop_name}.json"
        
        if state_file.exists():
            return f"⚠️ State for '{loop_name}' already exists"
        
        initial_state = {
            "loop_name": loop_name,
            "created_at": datetime.now().isoformat(),
            "last_run": None,
            "status": "initialized",
            "runs": [],
            "metrics": {
                "total_runs": 0,
                "prs_opened": 0,
                "prs_merged": 0,
                "acceptance_rate": 0.0,
                "total_token_cost": 0.0
            },
            "lessons_learned": [],
            "escalations": [],
            "pending_runs": [],
            "active_run": None,
        }
        
        async with aiofiles.open(state_file, 'w') as f:
            await f.write(json.dumps(initial_state, indent=2))
        
        return f"✅ State initialized for '{loop_name}'"
    
    async def _load_state(self, loop_name: str) -> dict:
        """Load state for a loop."""
        state_file = self.state_dir / f"{loop_name}.json"
        
        if not state_file.exists():
            # Initialize if doesn't exist
            await self.initialize_state(loop_name)
        
        async with aiofiles.open(state_file, 'r') as f:
            content = await f.read()
            return json.loads(content)
    
    async def _save_state(self, loop_name: str, state: dict):
        """Save state for a loop."""
        state_file = self.state_dir / f"{loop_name}.json"
        async with aiofiles.open(state_file, 'w') as f:
            await f.write(json.dumps(state, indent=2))
    
    async def get_state(self, loop_name: str) -> str:
        """Get formatted state information for a loop."""
        try:
            state = await self._load_state(loop_name)
        except Exception as e:
            return f"❌ Error loading state for '{loop_name}': {str(e)}"
        
        metrics = state.get("metrics", {})
        runs = state.get("runs", [])
        lessons = state.get("lessons_learned", [])
        escalations = state.get("escalations", [])
        
        output = [
            f"📊 **State for loop: {loop_name}**\n",
            f"**Last Run:** {state.get('last_run', 'Never')}",
            f"**Status:** {state.get('status', 'Unknown')}\n",
            "**Metrics:**",
            f"- Total runs: {metrics.get('total_runs', 0)}",
            f"- PRs opened: {metrics.get('prs_opened', 0)}",
            f"- PRs merged: {metrics.get('prs_merged', 0)}",
            f"- Acceptance rate: {metrics.get('acceptance_rate', 0):.1%}",
            f"- Token cost: ${metrics.get('total_token_cost', 0):.2f}\n"
        ]
        
        if runs:
            output.append("**Recent Runs (last 5):**")
            for run in runs[-5:]:
                timestamp = run.get('timestamp', 'Unknown')
                output.append(f"- {timestamp}: {run.get('summary', 'No summary')}")
            output.append("")
        
        if lessons:
            output.append("**Lessons Learned:**")
            for lesson in lessons[-5:]:  # Show last 5
                output.append(f"- {lesson}")
            output.append("")
        
        if escalations:
            output.append("**Recent Escalations:**")
            for escalation in escalations[-3:]:  # Show last 3
                output.append(f"- {escalation.get('timestamp', 'Unknown')}: {escalation.get('reason', 'No reason')}")
        
        return "\n".join(output)
    
    async def add_lesson(self, loop_name: str, lesson: str) -> str:
        """Add a lesson learned to the loop state."""
        state = await self._load_state(loop_name)
        
        timestamp = datetime.now().isoformat()
        lesson_entry = f"[{timestamp}] {lesson}"
        
        if "lessons_learned" not in state:
            state["lessons_learned"] = []
        
        state["lessons_learned"].append(lesson_entry)
        
        await self._save_state(loop_name, state)
        
        return f"""✅ Lesson added to '{loop_name}'

**Lesson:** {lesson}

This will be included in future loop runs to avoid repeating mistakes."""
    
    async def delete_state(self, loop_name: str) -> str:
        """Delete state for a loop."""
        state_file = self.state_dir / f"{loop_name}.json"
        
        if not state_file.exists():
            return f"⚠️ State for '{loop_name}' not found (already deleted)"
        
        state_file.unlink()
        return f"✅ State for '{loop_name}' deleted"
    
    async def record_run(
        self,
        loop_name: str,
        *,
        summary: str,
        status: str,
        token_cost: float = 0.0,
        verification_passed: bool = False,
        pr_url: Optional[str] = None,
    ) -> None:
        """Record a completed loop run and update metrics."""
        state = await self._load_state(loop_name)
        timestamp = datetime.now().isoformat()

        run_entry = {
            "timestamp": timestamp,
            "summary": summary,
            "status": status,
            "verification_passed": verification_passed,
            "pr_url": pr_url,
        }
        state.setdefault("runs", []).append(run_entry)
        state["last_run"] = timestamp
        state["status"] = status

        metrics = state.setdefault("metrics", {})
        metrics["total_runs"] = metrics.get("total_runs", 0) + 1
        metrics["total_token_cost"] = metrics.get("total_token_cost", 0.0) + token_cost

        if pr_url:
            metrics["prs_opened"] = metrics.get("prs_opened", 0) + 1
            opened = metrics["prs_opened"]
            merged = metrics.get("prs_merged", 0)
            metrics["acceptance_rate"] = merged / opened if opened > 0 else 0.0

        await self._save_state(loop_name, state)

    async def record_pr(self, loop_name: str, pr_url: str) -> None:
        """Record that a PR was opened for a loop run."""
        state = await self._load_state(loop_name)
        metrics = state.setdefault("metrics", {})
        if not any(r.get("pr_url") == pr_url for r in state.get("runs", [])):
            metrics["prs_opened"] = metrics.get("prs_opened", 0) + 1
        opened = metrics.get("prs_opened", 0)
        merged = metrics.get("prs_merged", 0)
        metrics["acceptance_rate"] = merged / opened if opened > 0 else 0.0
        await self._save_state(loop_name, state)

    async def record_escalation(self, loop_name: str, reason: str) -> None:
        """Record an escalation for a loop."""
        state = await self._load_state(loop_name)
        state.setdefault("escalations", []).append({
            "timestamp": datetime.now().isoformat(),
            "reason": reason,
        })
        state["status"] = "escalated"
        await self._save_state(loop_name, state)

    async def queue_pending_run(
        self, loop_name: str, run_id: str, source: str = "schedule"
    ) -> None:
        """Queue a loop run for the host agent to pick up."""
        state = await self._load_state(loop_name)
        pending = state.setdefault("pending_runs", [])
        if not any(p.get("run_id") == run_id for p in pending):
            pending.append({
                "run_id": run_id,
                "queued_at": datetime.now().isoformat(),
                "source": source,
            })
        await self._save_state(loop_name, state)

    async def remove_pending_run(self, loop_name: str) -> None:
        """Clear pending runs when a run begins."""
        state = await self._load_state(loop_name)
        state["pending_runs"] = []
        await self._save_state(loop_name, state)

    async def set_active_run(
        self,
        loop_name: str,
        *,
        run_id: str,
        branch: Optional[str],
        create_pr: bool,
    ) -> None:
        """Track an in-progress run started by the host agent."""
        state = await self._load_state(loop_name)
        state["active_run"] = {
            "run_id": run_id,
            "started_at": datetime.now().isoformat(),
            "branch": branch,
            "create_pr": create_pr,
        }
        state["status"] = "running"
        await self._save_state(loop_name, state)

    async def clear_active_run(self, loop_name: str) -> None:
        """Clear active run after completion."""
        state = await self._load_state(loop_name)
        state["active_run"] = None
        await self._save_state(loop_name, state)

    async def list_pending_runs(self) -> str:
        """List all loops queued for host agent execution."""
        state_files = list(self.state_dir.glob("*.json"))
        pending_items = []

        for state_file in state_files:
            async with aiofiles.open(state_file, "r") as f:
                state = json.loads(await f.read())
            loop_name = state.get("loop_name", state_file.stem)
            for item in state.get("pending_runs", []):
                pending_items.append((loop_name, item))
            if state.get("active_run") and not state.get("pending_runs"):
                active = state["active_run"]
                pending_items.append((
                    loop_name,
                    {"run_id": active["run_id"], "queued_at": active.get("started_at"), "source": "active"},
                ))

        if not pending_items:
            return (
                "📋 **No pending loop runs**\n\n"
                "Scheduled loops are queued here until a host agent (Cursor/Kiro) "
                "calls `run_loop_now` to begin execution."
            )

        output = ["📋 **Pending Loop Runs**\n"]
        for loop_name, item in pending_items:
            output.append(f"- **{loop_name}** (run_id: `{item.get('run_id')}`)")
            output.append(f"  Source: {item.get('source', 'unknown')}")
            output.append(f"  Queued: {item.get('queued_at', 'unknown')}\n")
        output.append("Call `run_loop_now(\"<name>\")` to begin execution in this session.")
        return "\n".join(output)

    async def get_metrics(self) -> str:
        """Get aggregated metrics across all loops."""
        state_files = list(self.state_dir.glob("*.json"))
        
        if not state_files:
            return """📊 **No loops with metrics yet**

Metrics will appear here once loops start running:
- Total runs
- PRs opened/merged
- Acceptance rates
- Token costs
- Time saved estimates"""
        
        total_runs = 0
        total_prs_opened = 0
        total_prs_merged = 0
        total_token_cost = 0.0
        loop_metrics = []
        
        for state_file in state_files:
            async with aiofiles.open(state_file, 'r') as f:
                state = json.loads(await f.read())
                metrics = state.get("metrics", {})
                
                loop_name = state.get("loop_name", state_file.stem)
                total_runs += metrics.get("total_runs", 0)
                total_prs_opened += metrics.get("prs_opened", 0)
                total_prs_merged += metrics.get("prs_merged", 0)
                total_token_cost += metrics.get("total_token_cost", 0.0)
                
                loop_metrics.append({
                    "name": loop_name,
                    "runs": metrics.get("total_runs", 0),
                    "acceptance_rate": metrics.get("acceptance_rate", 0.0)
                })
        
        overall_acceptance = (total_prs_merged / total_prs_opened * 100) if total_prs_opened > 0 else 0
        
        # Estimate time saved (assume 30 min per PR)
        time_saved_hours = (total_prs_merged * 0.5)
        
        output = [
            "📊 **Overall Loop Metrics**\n",
            "**Summary:**",
            f"- Total runs: {total_runs}",
            f"- PRs opened: {total_prs_opened}",
            f"- PRs merged: {total_prs_merged}",
            f"- Overall acceptance rate: {overall_acceptance:.1f}%",
            f"- Total token cost: ${total_token_cost:.2f}",
            f"- Estimated time saved: ~{time_saved_hours:.1f} hours\n",
            "**Per Loop:**"
        ]
        
        for loop in sorted(loop_metrics, key=lambda x: x["runs"], reverse=True):
            output.append(f"- {loop['name']}: {loop['runs']} runs, {loop['acceptance_rate']:.1%} acceptance")
        
        if overall_acceptance >= 50:
            output.append("\n✅ **Status:** Healthy (acceptance rate >50%)")
        else:
            output.append("\n⚠️ **Warning:** Acceptance rate below 50% - loops may need adjustment")
        
        return "\n".join(output)
