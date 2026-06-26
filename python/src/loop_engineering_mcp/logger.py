"""Structured logging for loop engineering."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


class LoopLogger:
    """Writes structured JSON logs to .loop/logs/."""

    def __init__(self, logs_dir: Path):
        self.logs_dir = logs_dir
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger("loop_engineering")
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)

    def _write_json(self, filename: str, entry: dict[str, Any]) -> None:
        log_file = self.logs_dir / filename
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def _entry(
        self,
        level: str,
        event: str,
        loop_name: Optional[str] = None,
        **extra: Any,
    ) -> dict[str, Any]:
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "loop_name": loop_name,
            **extra,
        }

    def info(self, event: str, loop_name: Optional[str] = None, **extra: Any) -> None:
        entry = self._entry("INFO", event, loop_name, **extra)
        self._write_json("loop-engineering.log", entry)
        self._logger.info(f"[{loop_name or 'system'}] {event}")

    def warning(self, event: str, loop_name: Optional[str] = None, **extra: Any) -> None:
        entry = self._entry("WARNING", event, loop_name, **extra)
        self._write_json("loop-engineering.log", entry)
        self._logger.warning(f"[{loop_name or 'system'}] {event}")

    def error(self, event: str, loop_name: Optional[str] = None, **extra: Any) -> None:
        entry = self._entry("ERROR", event, loop_name, **extra)
        self._write_json("loop-engineering.log", entry)
        self._logger.error(f"[{loop_name or 'system'}] {event}")

    def run_log(self, loop_name: str, run_id: str, data: dict[str, Any]) -> None:
        entry = self._entry("INFO", "loop_run", loop_name, run_id=run_id, **data)
        self._write_json(f"{loop_name}-runs.log", entry)
