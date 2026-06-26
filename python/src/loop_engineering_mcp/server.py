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
                description="Create a new automated loop with skill template and state tracking",
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
                            "description": "Command to verify changes (e.g., 'npm test')",
                        },
                        "goal": {
                            "type": "string",
                            "description": "Success criteria for each run",
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
                    "Finalize a loop run after you (host agent) have made code changes. "
                    "Runs verification, opens PR, and updates state."
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
                    },
                    "required": ["loop_name", "run_id", "summary"],
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
                    goal=arguments["goal"],
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

            else:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

        except Exception as e:
            logger.error("tool_error", arguments.get("name"), tool=name, error=str(e))
            return [TextContent(type="text", text=f"Error executing {name}: {str(e)}")]

    # Attach scheduler for lifecycle management
    server._loop_scheduler = scheduler  # type: ignore[attr-defined]

    return server
