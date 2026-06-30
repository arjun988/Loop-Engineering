"""The 4-condition loop suitability test.

Before building a loop you should confirm the task is actually loop-shaped.
This implements the canonical loop-engineering pre-flight check: don't wrap a
task in an autonomous loop unless it repeats, can be verified automatically, the
agent has real tools, and the token budget can absorb the iterations.
"""

from dataclasses import dataclass


@dataclass
class SuitabilityResult:
    score: int
    passed: bool
    report: str


_CONDITIONS = [
    (
        "repeats",
        "Does the task repeat (at least roughly weekly)?",
        "One-off work is cheaper as a single manual prompt than as a loop.",
    ),
    (
        "automated_verification",
        "Is there automated verification (tests, linter, build, or a check script)?",
        "Without an objective gate the loop grades its own homework — the #1 failure mode.",
    ),
    (
        "agent_tools",
        "Does the agent have senior-engineer tools (CLI, repro env, test runner)?",
        "An agent that can only suggest, not run-observe-fix, is not running a loop.",
    ),
    (
        "token_budget",
        "Can the token/cost budget absorb repeated automated iterations?",
        "Loops iterate; an uncapped or tiny budget turns autonomy into runaway spend.",
    ),
]


def check_suitability(
    task_description: str,
    *,
    repeats: bool,
    automated_verification: bool,
    agent_tools: bool,
    token_budget: bool,
) -> SuitabilityResult:
    """Score a task against the four conditions and return a verdict + guidance."""
    answers = {
        "repeats": repeats,
        "automated_verification": automated_verification,
        "agent_tools": agent_tools,
        "token_budget": token_budget,
    }
    score = sum(1 for v in answers.values() if v)
    passed = score == 4

    lines = [
        f"🧪 **Loop Suitability Test** — `{task_description[:80]}`\n",
        f"**Score: {score}/4**\n",
    ]
    for key, question, why in _CONDITIONS:
        mark = "✅" if answers[key] else "❌"
        lines.append(f"{mark} {question}")
        if not answers[key]:
            lines.append(f"   ↳ {why}")
    lines.append("")

    if passed:
        lines.append(
            "**Verdict: ✅ Build the loop.** Start small — one skill, one state file, "
            "one verification gate — then schedule it. Order matters: get it working "
            "manually, turn it into a skill, wrap it in a loop, then automate."
        )
    else:
        missing = [k for k, v in answers.items() if not v]
        lines.append(
            "**Verdict: ❌ Keep this as a manual prompt for now.** "
            f"Unmet conditions: {', '.join(missing)}. "
            "Fix the gaps (especially automated verification) before automating, or you'll "
            "pay for a system that drifts, loops on errors, or can't prove it's done."
        )

    return SuitabilityResult(score=score, passed=passed, report="\n".join(lines))
