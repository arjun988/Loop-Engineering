"""CLI helpers for Cursor hooks and shell integration."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

from .loop_manager import LoopManager
from .policy.manager import PolicyManager
from .state_manager import StateManager


def _loop_dir() -> Path:
    return Path(os.getcwd()) / ".loop"


async def _check_action(loop_name: str, tool: str, args_json: str) -> int:
    loop_manager = LoopManager(_loop_dir())
    state_manager = StateManager(_loop_dir() / "state")
    policy_mgr = PolicyManager()

    loops = await loop_manager._load_loops()
    if loop_name not in loops:
        print(json.dumps({"decision": "deny", "reason": f"Unknown loop: {loop_name}"}))
        return 1

    try:
        args = json.loads(args_json) if args_json else {}
    except json.JSONDecodeError:
        args = {"raw": args_json}

    decision, detail = policy_mgr.check_action(
        loops[loop_name].get("policy") or {},
        tool=tool,
        args=args,
    )
    if decision != "allow":
        await state_manager.record_policy_violation(loop_name, detail)

    print(json.dumps({"decision": decision, "detail": detail}))
    return 0 if decision == "allow" else 2


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="loop-mcp-cli")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check-action", help="Evaluate tool call against loop policy")
    check.add_argument("loop_name")
    check.add_argument("tool")
    check.add_argument("args", nargs="?", default="{}", help="JSON tool arguments")

    args = parser.parse_args(argv)
    if args.command == "check-action":
        code = asyncio.run(_check_action(args.loop_name, args.tool, args.args))
        sys.exit(code)


if __name__ == "__main__":
    main()
