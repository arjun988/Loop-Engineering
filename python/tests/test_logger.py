"""Tests for loop logger."""

import json
from pathlib import Path

from loop_engineering_mcp.logger import LoopLogger


def test_logger_writes_structured_log(tmp_path):
    logger = LoopLogger(tmp_path)
    logger.info("test_event", "my-loop", detail="value")

    log_file = tmp_path / "loop-engineering.log"
    assert log_file.exists()
    lines = log_file.read_text(encoding="utf-8").strip().split("\n")
    entry = json.loads(lines[-1])
    assert entry["event"] == "test_event"
    assert entry["loop_name"] == "my-loop"
    assert entry["detail"] == "value"


def test_run_log(tmp_path):
    logger = LoopLogger(tmp_path)
    logger.run_log("ci-triage", "abc123", {"status": "success"})

    run_log = tmp_path / "ci-triage-runs.log"
    assert run_log.exists()
    entry = json.loads(run_log.read_text(encoding="utf-8").strip())
    assert entry["run_id"] == "abc123"
    assert entry["status"] == "success"
