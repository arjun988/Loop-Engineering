# Loop-MCP Autonomy Roadmap

> **Research-backed improvements to reduce human-in-the-loop gates** — scoring, verification, merge decisions, and escalation — while keeping loops safe.
>
> Compiled from loop-engineering essays, GitHub implementations, academic benchmarks, and practitioner writeups (June 2026).
>
> **Status:** Proposal document for `loop-mcp` v0.3+  
> **Last updated:** 2026-06-30

---

## TL;DR

True loop engineering does **not** mean zero humans forever. It means humans design the **control system** once — goals, gates, budgets, escalation policy — and the system runs autonomously inside those bounds. The industry consensus (Osmani, Masood, Towards AI, LangChain, Anthropic) is:

1. **Replace human judgment with deterministic checks wherever possible** (tests, linters, compilers, probes).
2. **Replace human scoring with structured evaluators** (LES, rubrics, LLM-as-judge with adversarial prompts).
3. **Reserve humans for irreversible / high-risk actions** (prod deploy, auth, payments, architecture).
4. **Measure autonomy explicitly** — if you can't score it, you can't improve it.

This document maps those principles to concrete **new MCP tools and modules** for `loop-mcp`.

---

## What We Have Today (v0.2.0)

| Capability | Status |
|------------|--------|
| Cron scheduler (heartbeat) | ✅ |
| Git worktree isolation | ✅ |
| Skills + durable state | ✅ |
| Maker self-check (`verification_command`) | ✅ |
| Independent checker gate (`goal_check_command`) | ✅ |
| Iterate-until-goal (`complete_loop_run` loop body) | ✅ |
| Stop rules (max attempts, no-progress detection) | ✅ |
| Budget caps (daily runs, cost ceiling) | ✅ |
| 4-condition suitability test | ✅ |
| GitHub PR creation | ✅ |
| **Automated scoring / LES** | ❌ |
| **Checker subagent spawn** | ❌ |
| **Hidden out-of-sample validation** | ❌ |
| **Auto-merge with risk scoring** | ❌ |
| **CI signal ingestion** | ❌ |
| **PR review loop** | ❌ |
| **Feature checklist state** | ❌ |
| **Deterministic evidence probes** | ❌ |
| **Policy gates on tool calls** | ❌ |
| **Trajectory / run replay scoring** | ❌ |

---

## The Honest Ceiling: What Humans Cannot Be Removed From

Before the roadmap, the literature is explicit about limits:

| Keep human | Why (sources) |
|------------|---------------|
| **Goal definition** | A loop that optimizes a badly specified objective pursues the wrong thing efficiently ([Tosea.ai](https://tosea.ai/blog/loop-engineering-ai-agents-complete-guide-2026)) |
| **Irreversible actions** | Prod deploy, merge to main, secret rotation — need explicit approval gates ([loopengineering.run](https://loopengineering.run/), [Ouro Loop](https://github.com/VictorVVedtion/ouro-loop)) |
| **Auth / payments / PII** | High blast-radius; policy should hard-block, not "score and hope" ([Towards AI LES governance dimension](https://towardsai.net/p/machine-learning/loop-engineering-the-missing-governance-layer-for-reliable-ai-agents)) |
| **No deterministic verifier exists** | LLM-as-judge is necessary but gameable; humans remain the backstop ([Masood](https://medium.com/@adnanmasood/loop-engineering-a-guide-for-engineers-and-practitioners-893bb65ea943)) |
| **Checker drift** | The grader can become lenient too; acceptance criteria must be frozen *before* work starts ([HydraFlow / LinkedIn commentary on Osmani](https://www.linkedin.com/posts/addyosmani_ai-softwareengineering-programming-activity-7469999258658791425-cTvy)) |

**Design principle:** automate *verification* and *scoring*, not *accountability*. Humans set the constitution; the loop enforces it.

---

## Tier 1 — High Impact, Build Next

These eliminate the most common human touchpoints (re-running tests, eyeballing diffs, manual "is it done?").

### 1. Loop Engineering Score (LES) — `score_loop` / `score_run`

**Problem:** No quantitative way to know if a loop is getting more autonomous, faster, or safer over time.

**Industry reference:**
- [KanakMalpani/Loop-Engineering — LES 1.0](https://github.com/KanakMalpani/Loop-Engineering/tree/main/scoring) — eight weighted categories
- [Towards AI — 8 governance dimensions](https://towardsai.net/p/machine-learning/loop-engineering-the-missing-governance-layer-for-reliable-ai-agents) — goal fidelity, termination, governance, traceability, cost awareness, human escalation

**Proposed MCP tools:**

```
score_loop(name)           → LES-style composite from loop config + state history
score_run(loop_name, run_id) → per-run breakdown: attempts, cost, goal_met, escalation reason
get_autonomy_report()      → trend: human escalations / total runs over 7d
```

**LES categories to implement (normalize 0–1 each):**

| Category | Weight | Computed from |
|----------|--------|---------------|
| Effectiveness | 0.20 | `goals_met / total_runs`, acceptance rate |
| Speed | 0.15 | median iteration duration |
| Cost | 0.12 | `total_token_cost / goals_met` |
| Robustness | 0.13 | success rate under flaky CI / retry |
| Safety | 0.12 | forbidden-path violations blocked, escalations appropriate |
| Scalability | 0.10 | parallel worktrees without collision |
| Adaptability | 0.10 | lessons_learned applied → fewer repeat failures |
| **Autonomy** | 0.08 | `1 - (human_escalations / total_runs)` |

**Implementation sketch:** `scoring/les.py` reads `.loop/state/*.json` + `loops.json`, emits JSON report. Optional: export LSS YAML spec per loop for interoperability with [Loop-Core-Engineering](https://github.com/KanakMalpani/Loop-Core-Engineering).

---

### 2. Checker Subagent Brief — `spawn_checker`

**Problem:** Shell commands verify *mechanics* (tests pass) but not *intent* (right files, minimal diff, no cheating). Humans currently eyeball this.

**Industry reference:**
- [Addy Osmani — `/goal` uses a separate model to decide done](https://addyosmani.com/blog/loop-engineering/)
- [awesome-loop-engineering — loop-verifier skill, default REJECT](https://github.com/invincible04/awesome-loop-engineering/blob/refs/heads/main/prompts/subagents-maker-checker.md)
- [lSAAGl/loop-harness](https://github.com/lSAAGl/loop-harness) — second Claude session must print `VERDICT: PASS`
- [Contieri — spawn read-only subagent with PASS/FAIL table](https://maximilianocontieri.com/ai-coding-tip-024-force-a-criteria-check-before-the-task-ends)

**Proposed MCP tool:**

```
spawn_checker(loop_name, run_id) → markdown brief for host agent to spawn a READ-ONLY checker subagent
```

**Checker brief should include:**
- Changed files list (from git diff in worktree)
- Frozen rubric from skill (scope, intent, tests-run-by-checker, no-cheating rules)
- Required output: JSON `{ "verdict": "PASS"|"REJECT"|"ESCALATE", "checks": [...] }`
- Instruction: **default REJECT**, run tests independently, read-only tools only

**Flow integration:**
```
complete_loop_run → verification_command (deterministic)
                 → goal_check_command (deterministic)
                 → spawn_checker (semantic, LLM)     ← NEW
                 → merge/PR only if all three pass
```

**Cost control:** Only spawn checker on attempt ≥ 2, or when diff touches `risk_paths` from loop config.

---

### 3. Hidden Out-of-Sample Validation — `run_hidden_verify`

**Problem:** Agent can overfit to the verification command (disable tests, mock assertions). Humans catch this in review.

**Industry reference:**
- [leoncuhk/auto-dev-agentos](https://github.com/leoncuhk/auto-dev-agentos) — `hidden_verify_command` on data the LLM never sees; metrics in `.state/hidden_metrics.json` never fed back to the agent

**Proposed MCP tools:**

```
configure_hidden_verify(loop_name, command)  → set hidden gate (not shown in run brief)
run_hidden_verify(loop_name)                 → orchestrator-only, after goal_check passes
view_hidden_metrics(loop_name)               → human/ops dashboard only
```

**Architectural guarantee:** `hidden_verify_command` is **never** included in `_build_brief()` or skill files the agent reads. Only `loop_executor.complete_run()` invokes it.

---

### 4. Feature Checklist State — `init_checklist` / `mark_feature` / `checklist_status`

**Problem:** Multi-step goals ("implement 200 E2E features") need structured progress; humans track this in issues/spreadsheets.

**Industry reference:**
- [Anthropic long-running agent harness](https://www.anthropic.com/engineering) — JSON feature list, each `passes: false` until proven
- [eesel AI on verification lever](https://www.eesel.ai/blog/loop-engineering)

**Proposed MCP tools:**

```
init_checklist(loop_name, features: [{id, description, verify_command}])
mark_feature(loop_name, feature_id, passes: bool, evidence: str)
checklist_status(loop_name) → % complete, block PR until all pass
```

**State file:** `.loop/state/{name}-checklist.json` — agent can read status but cannot self-mark `passes: true` without `verify_command` exit 0 (orchestrator enforces).

---

### 5. Risk-Scored Auto-Merge — `evaluate_merge_risk` / `auto_merge`

**Problem:** Humans merge green PRs that are low-risk; loops stop at "PR opened."

**Industry reference:**
- [a7t-ai/three-body-agent](https://github.com/a7t-ai/three-body-agent) — Merger workflow merges fully-green autoagent PRs; Claude weighs review comments
- [AntaresYuan/claude-devloop](https://github.com/AntaresYuan/claude-devloop) — squash-merge after sub-agent review + live URL regression check

**Proposed MCP tools:**

```
evaluate_merge_risk(loop_name, pr_number) → score 0-100 + factors
auto_merge(loop_name, pr_number, min_risk_score: 85) → merge if:
    - CI green
    - no human review requested
    - diff lines < threshold
    - paths not in denylist
    - checker verdict PASS
    - LES safety dimension > 0.8
```

**Risk factors (deterministic, no LLM):**

| Factor | Weight | Signal |
|--------|--------|--------|
| CI status | 30% | all checks pass |
| Diff size | 15% | lines changed < cap |
| Path risk | 25% | no matches in `forbidden_paths` |
| Review comments | 15% | zero unresolved human comments |
| Flake history | 10% | branch hasn't been retried > 2x |
| Test delta | 5% | tests added or unchanged |

**Human gate preserved:** `auto_merge` disabled by default; `merge_policy: "human" | "auto_low_risk"` in loop config.

---

## Tier 2 — CI / GitHub Signal Loops (Eliminate Human Triage)

### 6. CI Failure Ingestion — `ingest_ci_failures`

**Problem:** Humans paste CI logs into chat. Loops should discover work autonomously.

**Industry reference:**
- [loop-harness triage-ci](https://github.com/lSAAGl/loop-harness) — every 10m, worktree fix or diagnosis PR
- [three-body-agent Fixer workflow](https://github.com/a7t-ai/three-body-agent) — on CI failure, every 30m

**Proposed MCP tools:**

```
ingest_ci_failures(repo, branch) → structured failures [{check, log_snippet, classification}]
classify_failure(log) → flake | bug | env | dependency (rules + optional LLM)
create_loop_from_failure(failure) → one-shot loop config + skill
```

**Classification heuristics (deterministic first):**
- `flake` — same test passed on retry in last 7d state
- `env` — missing env var / service connection in log
- `dependency` — version conflict / lockfile
- `bug` — assertion failure with stable repro

---

### 7. Automated PR Review Loop — `review_pr` / `post_review_verdict`

**Problem:** Humans review every loop PR. A review sub-loop can clear obvious cases.

**Industry reference:**
- [loop-harness pr-reviewer](https://github.com/lSAAGl/loop-harness) — polls PRs, inline comments, approves if clean
- [Magistrate multi-agent CR](https://openreview.net/attachment?id=V9pJJy2uRc) — static ast-grep + semantic analysis
- [CR-Bench](https://arxiv.org/html/2603.11078v1) — SNR vs Recall tradeoff; optimize for signal integrity

**Proposed MCP tools:**

```
review_pr(pr_number) → spawn brief for read-only review subagent
post_review_verdict(pr_number, verdict, comments) → approve / request_changes / escalate
```

**Scoring (from CR-Bench):** track **Signal-to-Noise Ratio** — false approvals are worse than false escalations. Default: escalate if confidence < 0.85.

---

### 8. Live Deploy Verification — `verify_deploy`

**Problem:** Merged code might break production; humans manually smoke-test.

**Industry reference:**
- [claude-devloop](https://github.com/AntaresYuan/claude-devloop) — `curl` live URL + grep feature markers after merge

**Proposed MCP tool:**

```
configure_deploy_check(loop_name, {url, markers: [string], timeout})
verify_deploy(loop_name) → HTTP checks + optional screenshot diff
```

Runs after merge, before marking loop run `success`. Failure → auto-revert PR (optional, high risk).

---

## Tier 3 — Deterministic Evidence Layer (No LLM Scoring)

### 9. Evidence Probes — `define_probes` / `run_probes`

**Problem:** LLM says "done" but file doesn't exist or tests weren't run.

**Industry reference:**
- [dybala-21/bracket](https://github.com/dybala-21/bracket) — FilesystemProbe, CommandProbe; verdict BLOCKED without LLM

**Proposed MCP tools:**

```
define_probes(loop_name, probes: [
  {type: "file_exists", path: "..."},
  {type: "command", cmd: "pytest -q", expect_exit: 0},
  {type: "diff_max_lines", max: 200},
  {type: "forbidden_path", pattern: "src/auth/**"}
])
run_probes(loop_name, worktree) → {passed, failures[]}
```

**Integration:** `run_probes` runs *before* checker subagent — cheap, deterministic, no tokens.

---

### 10. Policy Gates on Actions — `define_policy` / `check_action`

**Problem:** Agent edits `package-lock.json` or `.env` despite skill saying not to.

**Industry reference:**
- [Ouro Loop BOUND system](https://github.com/VictorVVedtion/ouro-loop) — PreToolUse hooks, exit 2 hard-block
- [AutoHarness 6-step pipeline](https://github.com/aiming-lab/AutoHarness) — risk classify every tool call

**Proposed MCP tools:**

```
define_policy(loop_name, {deny_paths, deny_commands, max_files_per_run})
check_action(loop_name, {tool, args}) → allow | deny | escalate
record_policy_violation(loop_name, detail)
```

MCP can't intercept host-agent tool calls directly today — but `check_action` can be called in `complete_loop_run` by scanning git diff + command log appended to state.

**Future:** Cursor hook integration via `hooks.json` calling `loop-mcp check-action` CLI.

---

## Tier 4 — Observability & Meta-Loops

### 11. Trajectory Scoring — `score_trajectory`

**Problem:** Single run pass/fail doesn't show *how* the agent got there (wasted steps, regressions).

**Industry reference:**
- [LangSmith trajectory evaluations](https://docs.smith.langchain.com/)
- [AgentRx — localize first critical failure step](https://medium.com/@adnanmasood/loop-engineering-a-guide-for-engineers-and-practitioners-893bb65ea943)
- LES diagnostics: convergence rate, regression count

**Proposed MCP tool:**

```
score_trajectory(loop_name, run_id) → {
  iterations, regression_count, wasted_attempts,
  convergence_rate, first_failure_step
}
```

**Data source:** append per-attempt events to `.loop/logs/{run_id}.jsonl` during iterate loop.

---

### 12. Loop Self-Improvement Meta-Loop — `propose_skill_patch`

**Problem:** Humans rewrite skills when loops fail repeatedly.

**Industry reference:**
- [claude-devloop](https://github.com/AntaresYuan/claude-devloop) — proposes `SKILL.md` diff backed by evidence after N failures
- LangChain harness engineering — optimize harness, not model

**Proposed MCP tool:**

```
propose_skill_patch(loop_name) → if escalations > 3 in 7d with same signature,
  draft skill.md addition (human approves before apply)
apply_skill_patch(loop_name, patch_id) → after human approval
```

**Autonomy boundary:** patch is *proposed*, not auto-applied — prevents runaway self-modification.

---

### 13. Simulation Before Live — `simulate_loop`

**Problem:** New loops burn tokens on production repos before proving value.

**Industry reference:**
- [eesel AI — simulate against historical tickets before live](https://www.eesel.ai/blog/loop-engineering)
- [LoopBench / replay sandboxes](https://github.com/KanakMalpani/Loop-Engineering)

**Proposed MCP tool:**

```
simulate_loop(loop_name, fixture: "ci-failure-auth-test") → dry-run against
  recorded logs + stub git repo; report predicted outcome without writes
```

---

## Tier 5 — Host-Agent Integration (Platform-Level)

These require Cursor / Claude Code / Codex primitives — document as integration targets.

| Primitive | Platform | MCP integration |
|-----------|----------|-----------------|
| `/goal` stop hook | Claude Code, Codex | `set_goal_check` wraps condition; host runs `/goal {goal_check}` |
| Stop hook (deterministic) | Claude Code | `loop-mcp verify` as shell hook on Stop event |
| Subagent spawn | Claude Code, Codex, Cursor | `spawn_checker` returns Task-tool-compatible prompt |
| `ScheduleWakeup` | Claude Code | `queue_run` + host scheduler |
| Git worktree flag | Claude Code | already in `loop_executor._create_isolation` |
| Cost tracking | Anthropic API headers | `token_cost` in `complete_loop_run` from host |

**Reference:** [Claude Code hooks](https://code.claude.com/docs/en/hooks), [Jakub Kontra — /goal vs /loop vs Stop hook](https://jakubkontra.com/en/blog/goal-vs-loop-vs-stop-hook-claude-code)

---

## Suggested Implementation Order

```
Phase A (scoring foundation)     score_loop, score_run, trajectory jsonl
Phase B (verification depth)   run_probes, spawn_checker, hidden_verify
Phase C (GitHub autonomy)      ingest_ci_failures, evaluate_merge_risk, review_pr
Phase D (structured goals)     init_checklist, mark_feature
Phase E (meta)                 propose_skill_patch, simulate_loop
```

**Target autonomy metric:** `Autonomy score ≥ 0.85` (LES) = <15% runs escalate to human, with zero safety violations.

---

## New Module Layout (Proposed)

```
python/src/loop_engineering_mcp/
├── scoring/
│   ├── les.py              # LES 1.0 calculator
│   └── trajectory.py       # per-run convergence metrics
├── probes/
│   └── runner.py           # bracket-style deterministic probes
├── checker/
│   └── brief.py            # spawn_checker brief builder
├── github/
│   ├── ci_ingest.py        # failure classification
│   ├── merge_risk.py       # auto-merge scoring
│   └── pr_review.py        # review loop helpers
├── checklist/
│   └── manager.py          # feature checklist state
└── hidden_verify.py        # out-of-sample gate
```

---

## Configuration Schema Additions (loops.json)

```json
{
  "name": "ci-triage",
  "merge_policy": "auto_low_risk",
  "merge_risk_threshold": 85,
  "hidden_verify_command": "pytest tests/integration/ --timeout=300",
  "checker_enabled": true,
  "checker_on_attempt": 2,
  "probes": [
    {"type": "diff_max_lines", "max": 150},
    {"type": "forbidden_path", "pattern": "src/billing/**"}
  ],
  "policy": {
    "deny_paths": [".env", "package-lock.json"],
    "max_files_changed": 20
  },
  "deploy_check": {
    "url": "https://staging.example.com/health",
    "markers": ["ok"]
  },
  "les_target": 75.0
}
```

---

## Key Sources

### Essays & articles
- [Addy Osmani — Loop Engineering](https://addyosmani.com/blog/loop-engineering/)
- [O'Reilly Radar — Loop Engineering](https://www.oreilly.com/radar/loop-engineering/)
- [Adnan Masood — Loop Engineering: A Guide for Engineers](https://medium.com/@adnanmasood/loop-engineering-a-guide-for-engineers-and-practitioners-893bb65ea943)
- [Tosea.ai — Complete Guide 2026](https://tosea.ai/blog/loop-engineering-ai-agents-complete-guide-2026)
- [Towards AI — Governance Layer](https://towardsai.net/p/machine-learning/loop-engineering-the-missing-governance-layer-for-reliable-ai-agents)
- [eesel AI — Designing Agent Loops](https://www.eesel.ai/blog/loop-engineering)
- [loopengineering.run — Safe Autonomous Loops](https://loopengineering.run/)
- [VentureBeat — Claude Code /goal](https://venturebeat.com/orchestration/claude-codes-goals-separates-the-agent-that-works-from-the-one-that-decides-its-done)
- [Maximilian Contieri — Criteria check subagent](https://maximilianocontieri.com/ai-coding-tip-024-force-a-criteria-check-before-the-task-ends)
- [Augment Code — Harness Engineering / PEV](https://www.augmentcode.com/guides/harness-engineering-ai-coding-agents)

### GitHub implementations
- [invincible04/awesome-loop-engineering](https://github.com/invincible04/awesome-loop-engineering) — maker/checker prompts
- [lSAAGl/loop-harness](https://github.com/lSAAGl/loop-harness) — multi-loop orchestrator + verifier session
- [leoncuhk/auto-dev-agentos](https://github.com/leoncuhk/auto-dev-agentos) — hidden verify + metrics
- [a7t-ai/three-body-agent](https://github.com/a7t-ai/three-body-agent) — full autonomous GH Actions pipeline
- [AntaresYuan/claude-devloop](https://github.com/AntaresYuan/claude-devloop) — unattended /devloop skill
- [dybala-21/bracket](https://github.com/dybala-21/bracket) — deterministic evidence probes
- [VictorVVedtion/ouro-loop](https://github.com/VictorVVedtion/ouro-loop) — BOUND guardrails + 5 gates
- [aiming-lab/AutoHarness](https://github.com/aiming-lab/AutoHarness) — governance pipeline
- [KanakMalpani/Loop-Engineering](https://github.com/KanakMalpani/Loop-Engineering) — LES 1.0 + LSS spec
- [ai-boost/awesome-harness-engineering](https://github.com/ai-boost/awesome-harness-engineering) — curated harness patterns

### Academic / benchmarks
- [CR-Bench — Code Review Agent Evaluation](https://arxiv.org/html/2603.11078v1)
- [Magistrate — Multi-Agent Code Review](https://openreview.net/attachment?id=V9pJJy2uRc)

### X / social threads
- [Codez — 14-step roadmap](https://x.com/0xCodez/status/2064374643729773029)
- [Addy Osmani — LinkedIn loop engineering post](https://www.linkedin.com/posts/addyosmani_ai-softwareengineering-programming-activity-7469999258658791425-cTvy)

---

## Success Criteria for "Human Elimination"

A loop is **production-autonomous** when:

1. **≥ 85% of runs** complete without human escalation (LES Autonomy ≥ 0.85)
2. **100% of merges** pass deterministic + hidden verification
3. **Zero** policy violations on forbidden paths (Safety = 1.0)
4. **Checker subagent** rejects ≥ 1 issue per 10 runs (proves it's not rubber-stamping)
5. **Human touches only:** goal changes, constitution updates, incident response

Until those metrics hold for 30 days on a real repo, keep humans in the merge gate.

---

*This document should be updated as tools ship. Link PRs to sections when implementing.*
