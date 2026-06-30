"""MCP Server implementation for Loop Engineering."""

import os
from pathlib import Path
from typing import Any, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from .loop_manager import LoopManager
from .skill_manager import SkillManager
from .state_manager import StateManager
from .logger import LoopLogger
from .loop_executor import LoopExecutor
from .scheduler import LoopScheduler
from .verification_runner import VerificationRunner
from .suitability import check_suitability
from .autonomy import AutonomyService


def create_server(start_scheduler: bool = True) -> Server:
    """Create and configure the Loop Engineering MCP server."""
    server = Server("loop-engineering")

    # Initialize managers
    workspace_root = Path(os.getcwd())
    loop_dir = workspace_root / ".loop"

    loop_manager = LoopManager(loop_dir)
    skill_manager = SkillManager(loop_dir / "skills")
    state_manager = StateManager(loop_dir / "state")
    logger = LoopLogger(loop_dir / "logs")
    executor = LoopExecutor(
        workspace_root, loop_manager, skill_manager, state_manager, logger
    )
    verification_runner = VerificationRunner(workspace_root)
    autonomy = AutonomyService(
        workspace_root, loop_dir, loop_manager, skill_manager, state_manager
    )

    scheduler: Optional[LoopScheduler] = None
    if start_scheduler:
        scheduler = LoopScheduler(
            loop_manager,
            logger,
            run_callback=executor.queue_run,
        )

    # Ensure directories exist
    loop_dir.mkdir(exist_ok=True)
    (loop_dir / "skills").mkdir(exist_ok=True)
    (loop_dir / "state").mkdir(exist_ok=True)
    (loop_dir / "logs").mkdir(exist_ok=True)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available Loop Engineering tools."""
        return [
            Tool(
                name="create_loop",
                description="Create a new automated loop with skill template, state tracking, an independent checker gate, stop rules, and budget caps",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Loop identifier (e.g., 'ci-triage')",
                        },
                        "description": {
                            "type": "string",
                            "description": "What this loop does",
                        },
                        "schedule": {
                            "type": "string",
                            "description": "Cron expression (e.g., '0 */6 * * *' for every 6 hours)",
                        },
                        "skill_instructions": {
                            "type": "string",
                            "description": "Detailed instructions for the AI agent",
                        },
                        "verification_command": {
                            "type": "string",
                            "description": "Maker self-check command run after changes (e.g., 'npm test')",
                        },
                        "goal_check_command": {
                            "type": "string",
                            "description": "Independent checker gate that decides if the GOAL is met (maker/checker separation). Runs only after verification passes. Defaults to the verification command.",
                        },
                        "goal": {
                            "type": "string",
                            "description": "Success criteria for each run",
                        },
                        "max_attempts": {
                            "type": "integer",
                            "description": "Stop rule: escalate to a human after this many failed attempts (default 3)",
                        },
                        "max_runs_per_day": {
                            "type": "integer",
                            "description": "Budget cap: maximum loop runs per day (default 24)",
                        },
                        "cost_budget": {
                            "type": "number",
                            "description": "Budget cap: cumulative token-cost ceiling in USD; 0 = unlimited (default 0)",
                        },
                        "isolation": {
                            "type": "string",
                            "enum": ["worktree", "branch"],
                            "description": "How to isolate the run. 'worktree' (default) gives each run a dedicated git worktree so parallel loops never collide; 'branch' uses a branch in the main tree.",
                        },
                    },
                    "required": ["name", "description", "schedule", "skill_instructions", "goal"],
                },
            ),
            Tool(
                name="start_loop",
                description="Start or resume a loop (activates cron scheduler)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Loop name to start"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="stop_loop",
                description="Stop a running loop (doesn't delete it)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Loop name to stop"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="run_loop_now",
                description=(
                    "Begin a loop run — returns skill instructions for YOU (the host agent) to execute. "
                    "No API keys needed. After making changes, call complete_loop_run."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Loop name to run"},
                        "create_pr": {
                            "type": "boolean",
                            "description": "Whether to create a PR when complete (default: true)",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="complete_loop_run",
                description=(
                    "Submit an attempt for a loop run (the loop body). Runs the maker self-check "
                    "then the independent checker gate. On success opens a PR; on a fresh failure "
                    "asks you to iterate with the same run_id; after max_attempts or a repeated "
                    "failure it escalates to a human."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string", "description": "Loop name"},
                        "run_id": {"type": "string", "description": "Run ID from run_loop_now"},
                        "summary": {"type": "string", "description": "What you changed"},
                        "create_pr": {
                            "type": "boolean",
                            "description": "Override PR creation (default: from begin_run)",
                        },
                        "token_cost": {
                            "type": "number",
                            "description": "Optional USD token cost of this attempt, recorded against the budget",
                        },
                    },
                    "required": ["loop_name", "run_id", "summary"],
                },
            ),
            Tool(
                name="check_loop_suitability",
                description=(
                    "Run the 4-condition loop suitability test BEFORE building a loop: does the "
                    "task repeat, is verification automated, does the agent have real tools, and "
                    "can the budget absorb iterations?"
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string", "description": "The task you're considering automating"},
                        "repeats": {"type": "boolean", "description": "Does the task repeat at least weekly?"},
                        "automated_verification": {"type": "boolean", "description": "Is there an automated test/lint/build/check?"},
                        "agent_tools": {"type": "boolean", "description": "Does the agent have CLI/repro/test tools?"},
                        "token_budget": {"type": "boolean", "description": "Can the token budget absorb repeated iterations?"},
                    },
                    "required": [
                        "task_description",
                        "repeats",
                        "automated_verification",
                        "agent_tools",
                        "token_budget",
                    ],
                },
            ),
            Tool(
                name="set_goal_check",
                description=(
                    "Set or update the independent checker gate (goal_check_command) for a loop. "
                    "This is the command that objectively decides whether the goal is met, separate "
                    "from the maker's self-check."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string", "description": "Loop to configure"},
                        "command": {"type": "string", "description": "Independent goal-check command"},
                    },
                    "required": ["loop_name", "command"],
                },
            ),
            Tool(
                name="list_pending_runs",
                description="Show loops queued by the scheduler waiting for a host agent session",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="run_verification",
                description="Run the verification command for a loop",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string", "description": "Loop name"},
                    },
                    "required": ["loop_name"],
                },
            ),
            Tool(
                name="list_loops",
                description="Show all loops with status, metrics, and recent activity",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="delete_loop",
                description="Permanently delete a loop and its state",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Loop name to delete"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="add_skill",
                description="Create a reusable skill template",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Skill identifier"},
                        "description": {"type": "string", "description": "What this skill does"},
                        "instructions": {"type": "string", "description": "Detailed instructions"},
                        "project_context": {
                            "type": "object",
                            "description": "Project-specific context",
                            "properties": {
                                "test_framework": {"type": "string"},
                                "ci_platform": {"type": "string"},
                                "forbidden_paths": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                    "required": ["name", "description", "instructions"],
                },
            ),
            Tool(
                name="list_skills",
                description="Show all available skill templates",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="view_state",
                description="Show detailed state for a specific loop",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Loop name"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="add_lesson",
                description="Record a lesson learned for future loop runs",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string", "description": "Which loop this applies to"},
                        "lesson": {"type": "string", "description": "The lesson to remember"},
                    },
                    "required": ["loop_name", "lesson"],
                },
            ),
            Tool(
                name="get_metrics",
                description="Get aggregated metrics across all loops",
                inputSchema={"type": "object", "properties": {}},
            ),
            Tool(
                name="configure_verification",
                description="Set or update verification command for a loop",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string", "description": "Loop to configure"},
                        "command": {"type": "string", "description": "Verification command to run"},
                    },
                    "required": ["loop_name", "command"],
                },
            ),
            # --- Tier 1: Scoring ---
            Tool(
                name="score_loop",
                description="Compute Loop Engineering Score (LES) for a loop from config + state history",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Loop name"},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="score_run",
                description="Per-run breakdown: attempts, cost, goal_met, checker/hidden verify",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["loop_name", "run_id"],
                },
            ),
            Tool(
                name="get_autonomy_report",
                description="Trend report: escalations vs total runs (autonomy %) over recent days",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "days": {"type": "integer", "description": "Window in days (default 7)"},
                    },
                },
            ),
            # --- Tier 1: Checker subagent ---
            Tool(
                name="spawn_checker",
                description="Return read-only checker subagent brief (maker/checker gate)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["loop_name", "run_id"],
                },
            ),
            Tool(
                name="submit_checker_verdict",
                description="Record checker PASS/REJECT/ESCALATE before PR flow continues",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "run_id": {"type": "string"},
                        "verdict": {"type": "string", "enum": ["PASS", "REJECT", "ESCALATE"]},
                        "checks_json": {"type": "string", "description": "Optional full JSON from checker"},
                    },
                    "required": ["loop_name", "run_id", "verdict"],
                },
            ),
            # --- Tier 1: Hidden verify ---
            Tool(
                name="configure_hidden_verify",
                description="Set hidden out-of-sample verify command (never shown to maker agent)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "command": {"type": "string"},
                    },
                    "required": ["loop_name", "command"],
                },
            ),
            Tool(
                name="run_hidden_verify",
                description="Run hidden verify manually (orchestrator/ops only)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                    },
                    "required": ["loop_name"],
                },
            ),
            Tool(
                name="view_hidden_metrics",
                description="View hidden verify metrics dashboard (never fed back to agent)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                    },
                    "required": ["loop_name"],
                },
            ),
            # --- Tier 1: Feature checklist ---
            Tool(
                name="init_checklist",
                description="Initialize feature checklist for multi-step goals",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "features": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "string"},
                                    "description": {"type": "string"},
                                    "verify_command": {"type": "string"},
                                },
                                "required": ["id"],
                            },
                        },
                    },
                    "required": ["loop_name", "features"],
                },
            ),
            Tool(
                name="mark_feature",
                description="Mark feature pass/fail; passes=true requires verify_command exit 0",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "feature_id": {"type": "string"},
                        "passes": {"type": "boolean"},
                        "evidence": {"type": "string"},
                    },
                    "required": ["loop_name", "feature_id", "passes"],
                },
            ),
            Tool(
                name="checklist_status",
                description="Show checklist completion % and block/allow PR status",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                    },
                    "required": ["loop_name"],
                },
            ),
            # --- Tier 1: Auto-merge ---
            Tool(
                name="evaluate_merge_risk",
                description="Deterministic merge risk score 0-100 with factor breakdown",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "pr_number": {"type": "integer"},
                        "min_risk_score": {"type": "number"},
                    },
                    "required": ["loop_name", "pr_number"],
                },
            ),
            Tool(
                name="auto_merge",
                description="Merge PR if merge_policy=auto_low_risk and risk score passes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "pr_number": {"type": "integer"},
                        "min_risk_score": {"type": "number"},
                    },
                    "required": ["loop_name", "pr_number"],
                },
            ),
            Tool(
                name="configure_merge_policy",
                description="Set merge_policy (human|auto_low_risk), threshold, forbidden_paths",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "merge_policy": {"type": "string", "enum": ["human", "auto_low_risk"]},
                        "merge_risk_threshold": {"type": "number"},
                        "max_diff_lines": {"type": "integer"},
                        "forbidden_paths": {"type": "array", "items": {"type": "string"}},
                        "risk_paths": {"type": "array", "items": {"type": "string"}},
                        "checker_enabled": {"type": "boolean"},
                        "checker_on_attempt": {"type": "integer"},
                    },
                    "required": ["loop_name"],
                },
            ),
            # --- Tier 2: CI ingestion ---
            Tool(
                name="ingest_ci_failures",
                description="Fetch and classify failing CI checks on a branch",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "branch": {"type": "string"},
                        "repo": {"type": "string", "description": "owner/repo override"},
                    },
                    "required": ["branch"],
                },
            ),
            Tool(
                name="classify_failure",
                description="Classify CI log as flake|bug|env|dependency",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "log": {"type": "string"},
                        "check_name": {"type": "string"},
                    },
                    "required": ["log"],
                },
            ),
            Tool(
                name="create_loop_from_failure",
                description="Create a one-shot loop from a classified CI failure",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "check": {"type": "string"},
                        "log": {"type": "string"},
                        "branch": {"type": "string"},
                    },
                    "required": ["check", "log"],
                },
            ),
            # --- Tier 2: PR review ---
            Tool(
                name="review_pr",
                description="Spawn read-only PR review subagent brief",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                    },
                    "required": ["pr_number"],
                },
            ),
            Tool(
                name="post_review_verdict",
                description="Record PR review verdict; may approve on GitHub if confidence high",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "pr_number": {"type": "integer"},
                        "verdict": {"type": "string", "enum": ["approve", "request_changes", "escalate"]},
                        "confidence": {"type": "number"},
                        "comments": {"type": "array", "items": {"type": "string"}},
                        "loop_name": {"type": "string"},
                    },
                    "required": ["pr_number", "verdict", "confidence"],
                },
            ),
            # --- Tier 2: Deploy verify ---
            Tool(
                name="configure_deploy_check",
                description="Set post-merge HTTP smoke check (url + body markers)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "url": {"type": "string"},
                        "markers": {"type": "array", "items": {"type": "string"}},
                        "timeout": {"type": "number"},
                    },
                    "required": ["loop_name", "url", "markers"],
                },
            ),
            Tool(
                name="verify_deploy",
                description="Run deploy smoke check for a loop",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                    },
                    "required": ["loop_name"],
                },
            ),
            # --- Tier 3: Evidence probes ---
            Tool(
                name="define_probes",
                description="Configure deterministic evidence probes (file_exists, command, diff_max_lines, forbidden_path)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "probes": {
                            "type": "array",
                            "items": {"type": "object"},
                        },
                    },
                    "required": ["loop_name", "probes"],
                },
            ),
            Tool(
                name="run_probes",
                description="Run configured probes against the active worktree",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "workdir": {"type": "string"},
                    },
                    "required": ["loop_name"],
                },
            ),
            # --- Tier 3: Policy gates ---
            Tool(
                name="define_policy",
                description="Set deny_paths, deny_commands, max_files_per_run for a loop",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "deny_paths": {"type": "array", "items": {"type": "string"}},
                        "deny_commands": {"type": "array", "items": {"type": "string"}},
                        "max_files_per_run": {"type": "integer"},
                    },
                    "required": ["loop_name"],
                },
            ),
            Tool(
                name="check_action",
                description="Check a tool call or git diff against loop policy (allow|deny|escalate)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "tool": {"type": "string"},
                        "args": {"type": "object"},
                        "changed_files": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["loop_name", "tool"],
                },
            ),
            Tool(
                name="record_policy_violation",
                description="Manually record a policy violation in loop state",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "detail": {"type": "string"},
                    },
                    "required": ["loop_name", "detail"],
                },
            ),
            # --- Tier 4: Trajectory ---
            Tool(
                name="score_trajectory",
                description="Score run efficiency: iterations, regressions, convergence rate",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "run_id": {"type": "string"},
                    },
                    "required": ["loop_name", "run_id"],
                },
            ),
            # --- Tier 4: Skill meta-loop ---
            Tool(
                name="propose_skill_patch",
                description="Draft skill.md addition from repeated escalations (human approves)",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "min_escalations": {"type": "integer"},
                        "days": {"type": "integer"},
                    },
                    "required": ["loop_name"],
                },
            ),
            Tool(
                name="apply_skill_patch",
                description="Apply an approved skill patch by patch_id",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "patch_id": {"type": "string"},
                    },
                    "required": ["loop_name", "patch_id"],
                },
            ),
            Tool(
                name="list_skill_patches",
                description="List proposed and applied skill patches",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                    },
                },
            ),
            # --- Tier 4: Simulation ---
            Tool(
                name="simulate_loop",
                description="Dry-run a loop against a recorded fixture without writes",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "loop_name": {"type": "string"},
                        "fixture": {"type": "string"},
                    },
                    "required": ["loop_name", "fixture"],
                },
            ),
            Tool(
                name="list_simulation_fixtures",
                description="List available simulation fixtures",
                inputSchema={"type": "object", "properties": {}},
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        """Handle tool calls."""
        try:
            if name == "create_loop":
                result = await loop_manager.create_loop(
                    name=arguments["name"],
                    description=arguments["description"],
                    schedule=arguments["schedule"],
                    skill_instructions=arguments["skill_instructions"],
                    verification_command=arguments.get("verification_command"),
                    goal_check_command=arguments.get("goal_check_command"),
                    goal=arguments["goal"],
                    max_attempts=int(arguments.get("max_attempts", 3)),
                    max_runs_per_day=int(arguments.get("max_runs_per_day", 24)),
                    cost_budget=float(arguments.get("cost_budget", 0)),
                    isolation=arguments.get("isolation", "worktree"),
                )
                await skill_manager.create_skill(
                    name=arguments["name"],
                    description=arguments["description"],
                    instructions=arguments["skill_instructions"],
                )
                await state_manager.initialize_state(arguments["name"])
                logger.info("loop_created", arguments["name"])
                return [TextContent(type="text", text=result)]

            elif name == "start_loop":
                result = await loop_manager.start_loop(arguments["name"])
                if scheduler:
                    scheduler.start()
                logger.info("loop_started", arguments["name"])
                return [TextContent(type="text", text=result)]

            elif name == "stop_loop":
                result = await loop_manager.stop_loop(arguments["name"])
                logger.info("loop_stopped", arguments["name"])
                return [TextContent(type="text", text=result)]

            elif name == "run_loop_now":
                create_pr = arguments.get("create_pr", True)
                result = await executor.begin_run(arguments["name"], create_pr=create_pr)
                return [TextContent(type="text", text=result)]

            elif name == "complete_loop_run":
                result = await executor.complete_run(
                    arguments["loop_name"],
                    arguments["run_id"],
                    arguments["summary"],
                    create_pr=arguments.get("create_pr"),
                    token_cost=float(arguments.get("token_cost", 0) or 0),
                    checker_verdict=arguments.get("checker_verdict"),
                )
                return [TextContent(type="text", text=result)]

            elif name == "check_loop_suitability":
                result = check_suitability(
                    arguments["task_description"],
                    repeats=bool(arguments["repeats"]),
                    automated_verification=bool(arguments["automated_verification"]),
                    agent_tools=bool(arguments["agent_tools"]),
                    token_budget=bool(arguments["token_budget"]),
                ).report
                return [TextContent(type="text", text=result)]

            elif name == "set_goal_check":
                result = await loop_manager.set_goal_check(
                    arguments["loop_name"],
                    arguments["command"],
                )
                return [TextContent(type="text", text=result)]

            elif name == "list_pending_runs":
                result = await state_manager.list_pending_runs()
                return [TextContent(type="text", text=result)]

            elif name == "run_verification":
                loops = await loop_manager._load_loops()
                loop_name = arguments["loop_name"]
                if loop_name not in loops:
                    return [TextContent(type="text", text=f"❌ Loop '{loop_name}' not found.")]
                cmd = loops[loop_name].get("verification_command", "")
                verification = await verification_runner.run(cmd)
                status = "✅ Passed" if verification.success else "❌ Failed"
                result = (
                    f"**Verification for '{loop_name}'**\n"
                    f"**Command:** {cmd}\n"
                    f"**Result:** {status}\n"
                    f"**Exit code:** {verification.exit_code}\n"
                    f"**Duration:** {verification.duration_seconds:.1f}s\n"
                )
                if verification.stdout:
                    result += f"\n**Stdout:**\n```\n{verification.stdout[:2000]}\n```\n"
                if verification.stderr:
                    result += f"\n**Stderr:**\n```\n{verification.stderr[:2000]}\n```\n"
                return [TextContent(type="text", text=result)]

            elif name == "list_loops":
                result = await loop_manager.list_loops()
                return [TextContent(type="text", text=result)]

            elif name == "delete_loop":
                result = await loop_manager.delete_loop(arguments["name"])
                await skill_manager.delete_skill(arguments["name"])
                await state_manager.delete_state(arguments["name"])
                logger.info("loop_deleted", arguments["name"])
                return [TextContent(type="text", text=result)]

            elif name == "add_skill":
                result = await skill_manager.create_skill(
                    name=arguments["name"],
                    description=arguments["description"],
                    instructions=arguments["instructions"],
                    project_context=arguments.get("project_context"),
                )
                return [TextContent(type="text", text=result)]

            elif name == "list_skills":
                result = await skill_manager.list_skills()
                return [TextContent(type="text", text=result)]

            elif name == "view_state":
                result = await state_manager.get_state(arguments["name"])
                return [TextContent(type="text", text=result)]

            elif name == "add_lesson":
                result = await state_manager.add_lesson(
                    arguments["loop_name"],
                    arguments["lesson"],
                )
                return [TextContent(type="text", text=result)]

            elif name == "get_metrics":
                result = await state_manager.get_metrics()
                return [TextContent(type="text", text=result)]

            elif name == "configure_verification":
                result = await loop_manager.configure_verification(
                    arguments["loop_name"],
                    arguments["command"],
                )
                return [TextContent(type="text", text=result)]

            elif name == "score_loop":
                result = await autonomy.score_loop(arguments["name"])
                return [TextContent(type="text", text=result)]

            elif name == "score_run":
                result = await autonomy.score_run(arguments["loop_name"], arguments["run_id"])
                return [TextContent(type="text", text=result)]

            elif name == "get_autonomy_report":
                days = int(arguments.get("days", 7))
                result = await autonomy.get_autonomy_report(days=days)
                return [TextContent(type="text", text=result)]

            elif name == "spawn_checker":
                result = await autonomy.spawn_checker(
                    arguments["loop_name"], arguments["run_id"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "submit_checker_verdict":
                result = await autonomy.submit_checker_verdict(
                    arguments["loop_name"],
                    arguments["run_id"],
                    arguments["verdict"],
                    arguments.get("checks_json", ""),
                )
                return [TextContent(type="text", text=result)]

            elif name == "configure_hidden_verify":
                result = await autonomy.configure_hidden_verify(
                    arguments["loop_name"], arguments["command"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "run_hidden_verify":
                result = await autonomy.run_hidden_verify(arguments["loop_name"])
                return [TextContent(type="text", text=result)]

            elif name == "view_hidden_metrics":
                result = await autonomy.view_hidden_metrics(arguments["loop_name"])
                return [TextContent(type="text", text=result)]

            elif name == "init_checklist":
                result = await autonomy.init_checklist(
                    arguments["loop_name"], arguments["features"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "mark_feature":
                result = await autonomy.mark_feature(
                    arguments["loop_name"],
                    arguments["feature_id"],
                    bool(arguments["passes"]),
                    arguments.get("evidence", ""),
                )
                return [TextContent(type="text", text=result)]

            elif name == "checklist_status":
                result = await autonomy.checklist_status(arguments["loop_name"])
                return [TextContent(type="text", text=result)]

            elif name == "evaluate_merge_risk":
                result = await autonomy.evaluate_merge_risk(
                    arguments["loop_name"],
                    int(arguments["pr_number"]),
                    float(arguments.get("min_risk_score", 85)),
                )
                return [TextContent(type="text", text=result)]

            elif name == "auto_merge":
                result = await autonomy.auto_merge(
                    arguments["loop_name"],
                    int(arguments["pr_number"]),
                    float(arguments.get("min_risk_score", 85)),
                )
                return [TextContent(type="text", text=result)]

            elif name == "configure_merge_policy":
                patch = {
                    k: arguments[k]
                    for k in (
                        "merge_policy",
                        "merge_risk_threshold",
                        "max_diff_lines",
                        "forbidden_paths",
                        "risk_paths",
                        "checker_enabled",
                        "checker_on_attempt",
                    )
                    if k in arguments
                }
                result = await autonomy.update_loop_config(arguments["loop_name"], **patch)
                return [TextContent(type="text", text=result)]

            elif name == "ingest_ci_failures":
                result = await autonomy.ingest_ci_failures(
                    arguments["branch"],
                    arguments.get("repo"),
                )
                return [TextContent(type="text", text=result)]

            elif name == "classify_failure":
                result = await autonomy.classify_failure(
                    arguments["log"],
                    arguments.get("check_name", "unknown"),
                )
                return [TextContent(type="text", text=result)]

            elif name == "create_loop_from_failure":
                result = await autonomy.create_loop_from_failure(
                    arguments["check"],
                    arguments["log"],
                    arguments.get("branch", "main"),
                )
                return [TextContent(type="text", text=result)]

            elif name == "review_pr":
                result = await autonomy.review_pr(int(arguments["pr_number"]))
                return [TextContent(type="text", text=result)]

            elif name == "post_review_verdict":
                result = await autonomy.post_review_verdict(
                    int(arguments["pr_number"]),
                    arguments["verdict"],
                    float(arguments["confidence"]),
                    arguments.get("comments", []),
                    arguments.get("loop_name"),
                )
                return [TextContent(type="text", text=result)]

            elif name == "configure_deploy_check":
                result = await autonomy.configure_deploy_check(
                    arguments["loop_name"],
                    arguments["url"],
                    arguments["markers"],
                    float(arguments.get("timeout", 30)),
                )
                return [TextContent(type="text", text=result)]

            elif name == "verify_deploy":
                result = await autonomy.verify_deploy(arguments["loop_name"])
                return [TextContent(type="text", text=result)]

            elif name == "define_probes":
                result = await autonomy.define_probes(
                    arguments["loop_name"], arguments["probes"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "run_probes":
                result = await autonomy.run_probes(
                    arguments["loop_name"], arguments.get("workdir")
                )
                return [TextContent(type="text", text=result)]

            elif name == "define_policy":
                policy = {
                    k: arguments[k]
                    for k in ("deny_paths", "deny_commands", "max_files_per_run")
                    if k in arguments
                }
                result = await autonomy.define_policy(arguments["loop_name"], policy)
                return [TextContent(type="text", text=result)]

            elif name == "check_action":
                result = await autonomy.check_action(
                    arguments["loop_name"],
                    arguments["tool"],
                    arguments.get("args") or {},
                    arguments.get("changed_files"),
                )
                return [TextContent(type="text", text=result)]

            elif name == "record_policy_violation":
                result = await autonomy.record_policy_violation(
                    arguments["loop_name"], arguments["detail"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "score_trajectory":
                result = await autonomy.score_trajectory(
                    arguments["loop_name"], arguments["run_id"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "propose_skill_patch":
                result = await autonomy.propose_skill_patch(
                    arguments["loop_name"],
                    int(arguments.get("min_escalations", 3)),
                    int(arguments.get("days", 7)),
                )
                return [TextContent(type="text", text=result)]

            elif name == "apply_skill_patch":
                result = await autonomy.apply_skill_patch(
                    arguments["loop_name"], arguments["patch_id"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "list_skill_patches":
                result = await autonomy.list_skill_patches(arguments.get("loop_name"))
                return [TextContent(type="text", text=result)]

            elif name == "simulate_loop":
                result = await autonomy.simulate_loop(
                    arguments["loop_name"], arguments["fixture"]
                )
                return [TextContent(type="text", text=result)]

            elif name == "list_simulation_fixtures":
                result = await autonomy.list_simulation_fixtures()
                return [TextContent(type="text", text=result)]

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error("tool_error", arguments.get("name"), tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    # Attach scheduler for lifecycle management
    server._loop_scheduler = scheduler  # type: ignore[attr-defined]

    return server
