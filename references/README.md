# Loop Engineering MCP Server

> **Automate repetitive coding tasks with AI agents**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

Based on the 14-step roadmap by Codez ([@0xCodez](https://x.com/0xCodez)) | [Original Article](https://x.com/0xCodez/status/2064374643729773029)

## What is Loop Engineering?

Loop engineering is building a system that finds work, hands it to an AI agent, checks the result, records what happened, and decides the next move - automatically. You design the system once. The system prompts the agent from then on.

This repository provides an **MCP (Model Context Protocol) server** that integrates loop engineering directly into your AI coding workflow (Cursor, Kiro, Claude Desktop).

---

## Quick Start

### Installation

**Python (recommended):**
```bash
uvx loop-engineering-mcp
```

**Node/TypeScript:**
```bash
npx loop-engineering-mcp
```

### Configure Your AI Agent

Add to `.cursor/mcp.json`, `.kiro/settings/mcp.json`, or Claude Desktop config:

```json
{
  "mcpServers": {
    "loop-engineering": {
      "command": "uvx",
      "args": ["loop-engineering-mcp"]
    }
  }
}
```

### Use It

Talk to your AI agent naturally:

```
You: "Set up a CI triage loop that runs every 6 hours"

AI: ✅ Loop created: ci-triage
    Schedule: Every 6 hours
    Verification: npm test
```

That's it. The loop runs automatically.

---

## Features

### 🔧 Core Tools

- **`create_loop`** - Set up automated coding loops
- **`start_loop`** / **`stop_loop`** - Control execution
- **`list_loops`** - View status and metrics
- **`add_skill`** - Create reusable templates
- **`view_state`** - Check history and learnings
- **`get_metrics`** - Track ROI and performance

### 📦 Pre-built Loop Templates

- **CI Triage** - Classify failures, draft fixes, escalate complex issues
- **Dependency Updates** - Check for outdated packages, test, create PRs
- **Lint Fixes** - Apply automated formatting, verify no logic changes
- **Custom Loops** - Build your own with skill templates

### 📊 Built-in Metrics

- Acceptance rates (target: >50%)
- Token costs
- Time saved estimates
- Lessons learned
- Escalation tracking

---

## Project Structure

```
loop-engineering/
├── README.md              # You are here
├── FRAMEWORK.md           # Complete implementation guide
├── python/                # Python MCP server
│   ├── pyproject.toml
│   └── src/loop_engineering_mcp/
│       ├── server.py
│       ├── loop_manager.py
│       ├── skill_manager.py
│       └── state_manager.py
├── typescript/            # TypeScript MCP server
│   ├── package.json
│   └── src/
│       ├── server.ts
│       ├── loop-manager.ts
│       ├── skill-manager.ts
│       └── state-manager.ts
└── shared/                # Skill templates
    └── skills/
        ├── ci-triage.md
        ├── dependency-updates.md
        └── lint-fixes.md
```

---

## Documentation

- **[FRAMEWORK.md](./FRAMEWORK.md)** - Complete implementation guide
- **[Python README](./python/README.md)** - Python package docs
- **[TypeScript README](./typescript/README.md)** - TypeScript package docs

---

## Loop Engineering Concepts

- [Part 1: The Why & The Test](#part-1-the-why--the-test)
  - [01. Loop engineering is replacing yourself as the prompter](#01-loop-engineering-is-replacing-yourself-as-the-prompter)
  - [02. Run the 4-condition test before you build anything](#02-run-the-4-condition-test-before-you-build-anything)
  - [03. Who wins, who loses](#03-who-wins-who-loses)
  - [04. The 30-second loop check](#04-the-30-second-loop-check)
- [Part 2: The 5 Building Blocks](#part-2-the-5-building-blocks)
  - [05. Automations: the heartbeat](#05-automations-the-heartbeat)
  - [06. Worktrees: parallel without chaos](#06-worktrees-parallel-without-chaos)
  - [07. Skills: write project knowledge once](#07-skills-write-project-knowledge-once)
  - [08. Connectors: the loop touches your real tools](#08-connectors-the-loop-touches-your-real-tools)
  - [09. Sub-agents: keep the maker away from the checker](#09-sub-agents-keep-the-maker-away-from-the-checker)
- [Part 3: Build It Right or Don't Build It](#part-3-build-it-right-or-dont-build-it)
  - [10. The state file](#10-the-state-file)
  - [11. The minimum viable loop](#11-the-minimum-viable-loop)
  - [12. The Ralph Wiggum loop](#12-the-ralph-wiggum-loop)
  - [13. Comprehension debt and cognitive surrender](#13-comprehension-debt-and-cognitive-surrender)
  - [14. The security tax](#14-the-security-tax)
- [Common Mistakes](#common-mistakes)
- [Conclusion](#conclusion)

---

## PART 1: The Why & The Test

### 01. Loop engineering is replacing yourself as the prompter

For two years, the way you got something out of a coding agent was: write a prompt, share the context, read what came back, write the next prompt. The agent was a tool and you held it the entire time. **That part is ending.**

**Loop engineering** is building a small system that finds the work, hands it to the agent, checks the result, records what happened, and decides the next move - on its own. You design that system once. The system prompts the agent from then on.

Anthropic engineers now merge **eight times as much code per day** as they did in 2024 - a figure Anthropic itself calls "almost certainly an overstatement of the true productivity gain."

The number is debated. The mechanism isn't: **the leverage point moved from typing prompts to designing the loop that prompts.**

---

### 02. Run the 4-condition test before you build anything

Loops earn their cost under four conditions. **Miss one and the loop costs more than it returns.**

#### The four conditions in plain English:

1. **The task repeats.** A loop amortizes its setup across many runs. For a one-time job, a good prompt is faster and cheaper. If the work does not recur weekly, you don't have a loop - you have a script you ran once.

2. **Verification is automated.** The loop needs something that can fail the work without you in the room. A test suite, a type checker, a linter, a build. No automated check means you're back in the chair reading every diff - the exact job the loop was supposed to remove.

3. **Your token budget can absorb the waste.** Loops re-read context, retry, explore. That burns tokens whether or not the run ships anything. The technique scales with budget, which is why it reads as obvious to people with effectively free tokens and reckless to people on a metered plan.

4. **The agent has a senior engineer's tools.** Logs, a reproduction environment, the ability to run the code it writes and see what breaks. Without that, the loop iterates blind.

---

### 03. Who wins, who loses

The economics are not universal. The people calling loop engineering obvious tend to have unmetered tokens. The people for whom it's reckless are usually on a $20 consumer plan trying to run heavy verification loops without hitting limits or a surprise invoice.

#### Who actually benefits:

- **Teams with repetitive, machine-checkable work** and the budget to run it - continuous test triage, dependency bumps, lint-and-fix passes, issue-to-PR drafts on a codebase with strong test coverage.
- **Codebases with strong existing test suites.** If a junior engineer could do the task from a checklist and a test suite would catch their mistakes, a loop fits.
- **Async-first teams with multi-agent patterns** already in use. For these teams, routines are the missing orchestration layer.

#### Who should skip it, today:

- **Solo builders on consumer plans** - the token bill arrives before the productivity gain does.
- **Anyone working on code with no automated verification.** A loop with no real check is the agent agreeing with itself on repeat.
- **Teams whose real constraint is review capacity** rather than typing speed. A loop generates more code; if review was already the bottleneck, it just makes the queue longer.

**The honest version:** Loop engineering is real, and most developers don't need it yet.

---

### 04. The 30-second loop check

The checklist you run on a specific task before you turn it into a loop. **Miss one box and keep it as a manual prompt.**

#### Checklist:

1. ✅ The task happens **at least weekly**
2. ✅ A test, type check, build, or linter can **reject bad output**
3. ✅ The agent can **run the code** it changes
4. ✅ The loop has a **hard stop** (token budget, iteration count, or time limit)
5. ✅ A **human reviews** before merge, deploy, or dependency changes

#### Good first loops:

- **CI failure triage** - nightly, scan failures, classify causes, draft fix PRs for the easy ones
- **Dependency bump PRs** - weekly, scan for updates, test compatibility, open PRs
- **Lint-and-fix passes** - on every PR open event, apply style fixes automatically
- **Flaky test reproduction** - loop until a theory survives the test
- **Issue-to-PR drafts** on code with strong tests, where bad output gets rejected by the suite

#### Bad first loops (these need a human in the chair):

- Architecture rewrites
- Auth or payments code
- Production deploys
- Vague product work
- Anything where "done" is a judgment call

---

## PART 2: The 5 Building Blocks

### 05. Automations: the heartbeat

Automations are what make a loop an actual loop and not just one run you did once. They fire on a schedule, on an event, or on a trigger condition. They're the heartbeat - everything else in the loop hangs off them.

#### What this looks like in the two tools that matter:

**Codex:** The Automations tab - pick a project, set a prompt, set a cadence, choose local checkout or background worktree.

**Claude Code:** Three primitives - `/loop` for session-scoped cadence, Desktop scheduled tasks for restart-survival, Routines for laptop-off cloud runs.

#### Two primitives that separate working loops from expensive ones:

- **`/loop`** re-runs on a cadence. Use it when you want regular checks regardless of state.
- **`/goal`** keeps going until a condition you wrote is actually true. A separate small model checks completion, so the agent that wrote the code isn't the one grading it.

**Example:**
```python
> /loop 30m /goal All tests in test/auth pass and lint is clean.
  Scan src/auth for new failures, propose fixes in claude/auth-fixes,
  open draft PR when goal condition holds.
```

---

### 06. Worktrees: parallel without chaos

The second you run more than one agent, the files start colliding. A **git worktree** fixes it - a separate working directory on its own branch sharing the same repo history, so one agent's edits literally cannot touch the other's checkout.

#### How it shows up:

- **Codex** builds worktree support in - several threads hit the same repo at once without bumping into each other.
- **Claude Code** exposes git worktree directly, a `--worktree` flag to open a session in its own checkout.

**Reality check:** Worktrees take away the mechanical collision, but you are still the ceiling. Your review bandwidth decides how many parallel agents you can actually run - not the tool.

---

### 07. Skills: write project knowledge once

A **Skill** is how you stop re-explaining the same project context every session. Both tools use the same format: a folder with a `SKILL.md` inside, holding instructions and metadata, plus optional scripts, references, and assets.

**Why this matters for loops:** A loop without skills re-derives your whole project context from zero every cycle. With skills, intent compounds.

**Example structure:**
```yaml
name: ci-triage
description: Classify CI failures by root cause, draft fixes for the easy ones
---

# CI triage skill

## Classification rules
- env: missing secret, wrong env var
- flake: passes on retry without code change
- bug: deterministic failure tied to recent commit
- dependency: failure tied to a version bump
- infra: timeout, OOM, runner issue

## Fix patterns
- Auth tests → check src/auth/middleware first
- Database tests → verify migration applied in CI env
```

---

### 08. Connectors: the loop touches your real tools

A loop that can only see the filesystem is a tiny loop. **Connectors**, built on the Model Context Protocol (MCP), let the agent read your issue tracker, query a database, hit a staging API, drop a message in Slack.

This is the difference between an agent that says "here is the fix" and a loop that **opens the PR, links the Linear ticket, and pings the channel once CI is green.**

#### The connectors that pay back fastest:

1. **GitHub** - read repos, create branches, open PRs, comment on issues
2. **Linear or Jira** - update tickets as the loop progresses, link PRs back to issues
3. **Slack** - post triage results, ping humans on escalations
4. **Sentry / error tracker** - let the loop investigate live alerts and draft fixes

---

### 09. Sub-agents: keep the maker away from the checker

The most useful structural thing in a loop: **splitting the agent that writes from the agent that checks.**

Addy Osmani's framing: the model that wrote the code is "way too nice grading its own homework." A second agent with different instructions and sometimes a different model catches the stuff the first one talked itself into.

#### How sub-agents land in both tools:

- **Codex:** Define your own agents as TOML files in `.codex/agents/` - name, description, instructions, optional model and reasoning effort.
- **Claude Code:** Subagents in `.claude/agents/` and agent teams that pass work between them.

**The usual split:** One agent explores, one implements, one verifies against the spec.

**Why it matters:** The loop runs while you are not watching, so a verifier you actually trust is the only reason you can walk away.

---

## PART 3: Build It Right or Don't Build It

### 10. The state file

This is the piece that sounds too dumb to matter and is actually **the spine of every working loop.** A markdown file, a Linear board, a JSON state - anything that lives outside the single conversation and holds what's done and what is next.

**Why this matters:** Agents have short memory by default. What they learn this session is gone tomorrow unless you write it down.

**Osmani's rule:** The agent forgets, the repo does not. A loop without persistent state restarts every run; a loop with state resumes.

#### Example state file:

```markdown
# Loop state · ci-triage

## Last run
2026-06-09 03:30 UTC · 7 failures classified, 3 fixes drafted, 4 escalated

## In progress
- claude/fix-auth-token-refresh — tests passing locally, awaiting CI
- claude/fix-flaky-payment-webhook — retry pattern applied, monitoring

## Completed today
- claude/bump-axios-1.7.4 → merged (CI green, deps loop verified)

## Escalated to humans
- src/billing/refund.ts — tests failing in 3 ways, root cause unclear

## Lessons learned
- 2026-06-08: PowerShell hits TLS 1.2 issue on this Windows runner. Use bash.
```

#### Two patterns for where the state file lives:

1. **Markdown in the repo** - `STATE.md` at the root or inside `.claude/`. Version-controlled. Simple. Best for solo or small team work.
2. **External system** (Linear, GitHub Issues, a database) - survives across repos, queryable, supports team-wide visibility.

---

### 11. The minimum viable loop

If you passed the 4-condition test in step 2, build the smallest loop that works before anything fancy. **Four parts, no swarm.**

#### The four parts:

1. **One automation.** A scheduled run that fires on a cadence and stops on a clear condition.
2. **One skill.** A single `SKILL.md` that stores the project context.
3. **One state file.** Records what is done and what is next. Tomorrow's run resumes instead of restarting.
4. **One gate.** The test, type check, or build that fails bad work automatically.

**Order matters:** Get one manual run reliable first. Turn it into a skill. Wrap it in a loop. Then schedule it. Skipping ahead is how loops fail in production.

**The metric that matters:** Cost per accepted change - not tokens spent, not tasks attempted. If your accepted-change rate is below 50%, the loop is losing.

---

### 12. The Ralph Wiggum loop

Engineer Geoffrey Huntley documented this failure mode. An agent meant to emit a completion token only when finished emits it early, and the loop exits on a half-done job. **Without a hard gate, loops fail quietly and keep spending.**

#### The Ralph Wiggum loop happens when:

- **No real verifier.** Just a second agent asked to "review," no objective signal.
- **Soft completion conditions.** "Done" defined by the agent's judgment, not by a test.
- **No hard stops.** Loop continues until something external kills it.

**The fix:** The gate from step 11 - something objective that can fail the work. A test that passes or fails. A build that compiles or doesn't. Not a verifier that has an opinion.

#### Other measured failure modes:

- **Goal drift** over long sessions. Mitigation: a standing `VISION.md` reread each run.
- **Self-preferential bias.** The agent that wrote the code is too nice grading its own homework. Mitigation: separate verifier subagent.
- **Agentic laziness.** The loop declares "done enough" at partial completion. Mitigation: `/goal` with an objective stop condition.

---

### 13. Comprehension debt and cognitive surrender

This is the failure mode that gets sharper as the loop gets better, not worse.

#### Two named risks:

1. **Comprehension debt.** The faster the loop ships code you didn't write, the larger the distance between what the repository contains and what you understand. The bill that hurts is not the token bill. It is the day you have to debug a system no one on the team has read.

2. **Cognitive surrender.** The pull to stop forming an opinion and accept whatever the loop returns. Designing the loop is the cure when you do it with judgment and the accelerant when you do it to avoid thinking.

#### The mitigations are not technical:

- **Read the diffs.** If you don't read what the loop ships, you're renting comprehension debt at compound interest.
- **Spot-check the gate.** Verify the test that approved them actually catches the failure mode you care about. Gates rot.
- **Block the loop from architecture work.** Keep it on small, machine-checkable changes.
- **Pair-design loops with a teammate.** A second pair of eyes catches blind spots.

---

### 14. The security tax

A loop running unattended is also an attack surface running unattended.

#### The threat model your loop has to defend against:

- **Generated code shipping unreviewed.** Without a gate that includes security checks (SAST, dependency audit, secret scanning), insecure code merges automatically.
- **Skills as injection vectors.** A loop that auto-installs skills inherits every prompt injection hiding in their descriptions. Audit skill sources before installing.
- **Credentials in logs.** Debug logging during a long-running loop scatters secrets across logs you don't monitor.
- **Permission scope creep.** A loop tested with read-only permissions gets "just one" write permission added for convenience, then never re-audited.

**Mitigation:** Re-audit permissions every 30 days.

---

## Common Mistakes

**The mistakes that turn loops into money pits:**

1. ❌ Building a loop without running the 4-condition test
2. ❌ No objective gate (just a second agent asked to "review")
3. ❌ One agent doing both writing and verifying
4. ❌ No state file (tomorrow's run restarts from zero)
5. ❌ Vague stop conditions ("done when it looks good")
6. ❌ No token budget cap
7. ❌ Running loops on a consumer plan with heavy verification
8. ❌ Auto-installing community skills (520 of 17,022 audited skills leak credentials)
9. ❌ Loops on judgment-call work (architecture, auth, payments)
10. ❌ Not reading the diffs (comprehension debt at compound interest)

---

## Conclusion

### The leverage moved. Your job did too.

For two years, the leverage in working with coding agents was at the prompt. Better prompts, better context, better one-shot output.

**That phase is ending.** The agents got good enough that the next leverage point is one floor up: the system that decides what they work on, when, with what gate, and what state survives between runs.

But the honest version of this story is not that everyone should rush to build loops. **Most developers don't need one yet** - not until the task repeats, verification is automated, the budget can absorb the waste, and the agent has senior engineer tools.

**If you pass the test, build small:**
- One automation
- One skill
- One state file
- One gate

Get a manual run reliable. Turn it into a skill. Wrap it in a loop. Then schedule it. **Order matters.** Skip ahead and you're paying for a system no one understands.

**Build the loop. Stay the engineer.**

---

## Resources

- **Author:** Codez ([@0xCodez](https://x.com/0xCodez))
- **LinkedIn:** [linkedin.com/in/lev-deviatkin](https://linkedin.com/in/lev-deviatkin)
- **Original Article:** [X Thread](https://x.com/0xCodez/status/2064374643729773029)
- **Published:** June 9, 2026

---

*Content rephrased and structured for clarity while preserving the core insights and recommendations from the original article.*


---

## Examples

### Example 1: CI Triage Loop

```
You: "Create a loop that checks CI failures every 6 hours"

AI: [creates loop with ci-triage skill]
✅ Loop created
✅ Will classify failures as: flake, bug, env, dependency
✅ Opens PRs for fixable bugs
✅ Escalates complex issues

You: "Start it"

AI: ✅ Loop active
    Next run: In 6 hours
```

**Result:** Automatic CI monitoring, fixes drafted while you sleep.

---

### Example 2: Dependency Updates

```
You: "Set up weekly dependency updates"

AI: [creates loop with dependency-updates skill]
✅ Loop created
✅ Schedule: Every Monday 9am
✅ Will check for outdated packages
✅ Creates PRs for safe updates

You: "What's the current state?"

AI: 📊 Last run: 2 days ago
    - 5 packages checked
    - 2 PRs opened (both merged)
    - Acceptance rate: 100%
```

---

### Example 3: Custom Loop

```
You: "Create a loop that checks for TODO comments and creates issues"

AI: I'll create a custom loop for that.

[AI creates loop with custom skill]

✅ Loop 'todo-tracker' created
✅ Will scan for TODO/FIXME comments
✅ Creates GitHub issues with context
✅ Runs daily at 9am
```

---

## Development

### Python Package

```bash
cd python
pip install -e ".[dev]"
pytest
```

### TypeScript Package

```bash
cd typescript
npm install
npm run build
npm start
```

---

## Publishing

### Python (PyPI)

```bash
cd python
python -m build
twine upload dist/*
```

### TypeScript (NPM)

```bash
cd typescript
npm run build
npm publish
```

---

## Contributing

Contributions welcome! Areas we'd love help with:

- [ ] Additional skill templates
- [ ] Better error handling
- [ ] Metrics visualization
- [ ] CI/CD integrations
- [ ] Documentation improvements

See [CONTRIBUTING.md](./CONTRIBUTING.md) for guidelines.

---

## License

MIT License - see [LICENSE](./LICENSE) file for details.

---

## Credits

- **Loop Engineering Concept**: Codez ([@0xCodez](https://x.com/0xCodez))
  - [Original Article](https://x.com/0xCodez/status/2064374643729773029)
  - Based on Anthropic engineering docs and Addy Osmani's research
- **MCP Server Implementation**: This repository
- **MCP Protocol**: [Anthropic](https://www.anthropic.com/)

---

## Support

- 📖 [Documentation](./FRAMEWORK.md)
- 🐛 [Report Issues](https://github.com/yourusername/loop-engineering/issues)
- 💬 [Discussions](https://github.com/yourusername/loop-engineering/discussions)

---

## Roadmap

- [x] Core MCP server (Python & TypeScript)
- [x] Basic loop management
- [x] Skill templates
- [x] State tracking
- [ ] Metrics dashboard
- [ ] GitHub integration
- [ ] Slack notifications
- [ ] VS Code extension
- [ ] Web UI for configuration

---

**Build the loop. Stay the engineer.**
