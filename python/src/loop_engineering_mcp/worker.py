"""Standalone worker entry point for loop scheduler."""

import asyncio
import sys
from pathlib import Path

from .loop_manager import LoopManager
from .skill_manager import SkillManager
from .state_manager import StateManager
from .logger import LoopLogger
from .loop_executor import LoopExecutor
from .scheduler import LoopScheduler


async def run_worker():
    """Run the loop scheduler as a standalone background worker."""
    workspace_root = Path.cwd()
    loop_dir = workspace_root / ".loop"
    loop_dir.mkdir(exist_ok=True)

    loop_manager = LoopManager(loop_dir)
    skill_manager = SkillManager(loop_dir / "skills")
    state_manager = StateManager(loop_dir / "state")
    logger = LoopLogger(loop_dir / "logs")
    executor = LoopExecutor(
        workspace_root, loop_manager, skill_manager, state_manager, logger
    )
    scheduler = LoopScheduler(loop_manager, logger, run_callback=executor.queue_run)

    logger.info("worker_started", workspace=str(workspace_root))
    scheduler.start()

    try:
        while True:
            await asyncio.sleep(3600)
    except asyncio.CancelledError:
        pass
    finally:
        await scheduler.stop()
        logger.info("worker_stopped")


def main():
    """CLI entry point for loop-engineering-worker."""
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        print("\nShutting down loop worker...", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
