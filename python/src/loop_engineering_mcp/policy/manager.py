"""Policy gates on agent actions and git diffs."""

from __future__ import annotations

import fnmatch
import re
from typing import Any, Literal

ActionDecision = Literal["allow", "deny", "escalate"]


class PolicyManager:
    """BOUND-style policy checks for loop runs."""

    DEFAULT_POLICY = {
        "deny_paths": [],
        "deny_commands": [],
        "max_files_per_run": 50,
    }

    def normalize_policy(self, policy: dict[str, Any] | None) -> dict[str, Any]:
        base = dict(self.DEFAULT_POLICY)
        if policy:
            base.update(policy)
        return base

    def check_diff(
        self, policy: dict[str, Any], changed_files: list[str]
    ) -> tuple[ActionDecision, list[str]]:
        violations: list[str] = []
        deny_paths = policy.get("deny_paths") or []
        max_files = int(policy.get("max_files_per_run", 50) or 50)

        if max_files and len(changed_files) > max_files:
            violations.append(
                f"Too many files changed ({len(changed_files)} > {max_files})"
            )

        for path in changed_files:
            for pattern in deny_paths:
                if fnmatch.fnmatch(path, pattern) or pattern in path:
                    violations.append(f"Denied path touched: {path} (rule: {pattern})")

        if not violations:
            return "allow", []
        if any("Too many files" in v for v in violations):
            return "escalate", violations
        return "deny", violations

    def check_action(
        self,
        policy: dict[str, Any],
        *,
        tool: str,
        args: dict[str, Any],
        changed_files: list[str] | None = None,
    ) -> tuple[ActionDecision, str]:
        """Evaluate a tool call or diff snapshot against policy."""
        policy = self.normalize_policy(policy)
        files = changed_files or []

        if files:
            decision, violations = self.check_diff(policy, files)
            if decision != "allow":
                return decision, "; ".join(violations)

        tool_lower = tool.lower()
        if tool_lower in ("shell", "bash", "run_terminal_cmd", "terminal"):
            command = str(args.get("command") or args.get("cmd") or "")
            for denied in policy.get("deny_commands") or []:
                if denied and re.search(denied, command, re.I):
                    return "deny", f"Denied command pattern: {denied}"

        if tool_lower in ("write", "edit", "strreplace", "apply_patch"):
            path = str(args.get("path") or args.get("file") or "")
            for pattern in policy.get("deny_paths") or []:
                if path and (fnmatch.fnmatch(path, pattern) or pattern in path):
                    return "deny", f"Denied write to: {path}"

        return "allow", "Policy check passed"

    def format_decision(self, loop_name: str, decision: ActionDecision, detail: str) -> str:
        icons = {"allow": "✅", "deny": "🚫", "escalate": "🚨"}
        return f"{icons.get(decision, '❓')} **Policy ({loop_name}):** {decision}\n{detail}"
