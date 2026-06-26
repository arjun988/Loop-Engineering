"""Cron-like scheduler for active loops."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Callable, Awaitable, Optional, Any

from croniter import croniter

from .logger import LoopLogger
from .loop_manager import LoopManager


class LoopScheduler:
    """Background worker that runs active loops on their cron schedule."""

    def __init__(
        self,
        loop_manager: LoopManager,
        logger: LoopLogger,
        run_callback: Callable[..., Awaitable[str]],
        poll_interval: int = 60,
    ):
        self.loop_manager = loop_manager
        self.logger = logger
        self.run_callback = run_callback
        self.poll_interval = poll_interval
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._last_run: dict[str, datetime] = {}
        self._in_progress: set[str] = set()

    def _is_due(self, schedule: str, loop_name: str) -> bool:
        """Check if a loop is due to run based on its cron schedule."""
        try:
            now = datetime.now()
            cron = croniter(schedule, now)
            prev_run = cron.get_prev(datetime)
            last = self._last_run.get(loop_name)
            if last is None or prev_run > last:
                return True
            return False
        except (ValueError, KeyError) as e:
            self.logger.warning("invalid_cron", loop_name, schedule=schedule, error=str(e))
            return False

    async def _tick(self) -> None:
        """Check all active loops and run any that are due."""
        loops = await self.loop_manager._load_loops()
        for name, config in loops.items():
            if config.get("status") != "active":
                continue
            if name in self._in_progress:
                continue
            if not self._is_due(config.get("schedule", ""), name):
                continue

            self._in_progress.add(name)
            try:
                self.logger.info("scheduler_triggered", name, schedule=config.get("schedule"))
                await self.run_callback(name)
                self._last_run[name] = datetime.now()
            except Exception as e:
                self.logger.error("scheduler_run_failed", name, error=str(e))
            finally:
                self._in_progress.discard(name)

    async def _loop(self) -> None:
        """Main scheduler loop."""
        self._running = True
        self.logger.info("scheduler_started", poll_interval=self.poll_interval)
        while self._running:
            try:
                await self._tick()
            except Exception as e:
                self.logger.error("scheduler_tick_failed", error=str(e))
            await asyncio.sleep(self.poll_interval)

    def start(self) -> None:
        """Start the background scheduler."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """Stop the background scheduler."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.logger.info("scheduler_stopped")

    async def run_now(self, loop_name: str, **kwargs: Any) -> str:
        """Manually trigger a loop run immediately."""
        if loop_name in self._in_progress:
            return f"⏳ Loop '{loop_name}' is already running."
        self._in_progress.add(loop_name)
        try:
            result = await self.run_callback(loop_name, **kwargs)
            self._last_run[loop_name] = datetime.now()
            return result
        finally:
            self._in_progress.discard(loop_name)
