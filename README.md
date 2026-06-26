# Loop Engineering MCP Server

> **Stop typing prompts. Start designing systems that prompt.**

Automate repetitive coding tasks with AI agents. Set up once, run forever.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-blue.svg)](https://www.typescriptlang.org/)
[![MCP](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io)

---

## What is This?

An MCP server that brings **loop engineering** to your AI coding workflow. Instead of manually prompting your AI agent for every task, you create loops that:

- 🔄 **Run automatically** on schedule or triggers
- 🧠 **Learn from mistakes** through state tracking
- ✅ **Verify changes** before creating PRs
- 📊 **Track metrics** (acceptance rates, token costs, time saved)
- 🎯 **Escalate complexity** to humans when needed

**Think of it as:** GitHub Actions + AI Agents + Intelligent State Management

---

## Why is This Powerful?

### Before Loop Engineering
```
You: "Check CI failures"          [5 minutes]
AI:  [reports failures]

You: "What caused the auth test failure?"  [3 minutes]
AI:  [investigates]

You: "Fix it"                     [10 minutes]
AI:  [writes fix]

You: "Open a PR"                  [2 minutes]
AI:  [creates PR]

Total: 20 minutes × 4 times/day = 80 minutes/day
```

### After Loop Engineering
```
[You set up once: "Create a CI triage loop, run every 6 hours"]

Loop automatically:
✅ Detects failures
✅ Classifies (flake vs bug vs env issue)
✅ Drafts fixes for deterministic bugs
✅ Runs tests
✅ Opens PRs
✅ Escalates complex issues
✅ Records lessons learned

Total: 0 minutes/day (runs while you sleep)
```

**Real Impact:**
- ⚡ **80% faster** - Loops run in parallel, don't need your attention
- 🎯 **Higher quality** - Consistent checks, learns from past mistakes
- 💰 **Cost effective** - Only runs when needed, tracks ROI
- 😴 **Works 24/7** - Runs while you sleep, on weekends

---

## What Can You Automate?

### ✅ Perfect for Loops
- **CI Triage** - Classify failures, draft fixes, escalate blockers
- **Dependency Updates** - Check for updates, test compatibility, create PRs
- **Lint & Format** - Apply automated fixes on every PR
- **Documentation Sync** - Keep docs updated with code changes
- **Flaky Test Detection** - Identify and track intermittent failures
- **Security Patches** - Auto-apply safe security updates

### ❌ Don't Automate These
- Architecture decisions (requires judgment)
- Auth/payment code (too risky)
- Production deployments (needs human oversight)
- Vague product work (unclear success criteria)

---

## Installation

### Option 1: Python (Recommended - Easiest)

**Install once, run anywhere:**
```bash
pip install loop
```

**Or use directly (no installation):**
```bash
uvx loop
```

### Option 2: TypeScript/Node

**Install globally:**
```bash
npm install -g loop
```

**Or use directly:**
```bash
npx loop
```

### Option 3: From Source (Local Development)

**Clone and install:**
```bash
# Clone repository
git clone https://github.com/yourusername/loop-engineering
cd loop-engineering

# Python
cd python
pip install -e ".[dev]"

# TypeScript
cd typescript
npm install
npm run build
```

---

## Setup (2 minutes)

### Step 1: Add to Your AI Agent Config

#### For Cursor

Create or edit `.cursor/mcp.json` in your project:

```json
{
  "mcpServers": {
    "loop-engineering": {
      "command": "uvx",
      "args": ["loop"]
    }
  }
}
```

#### For Kiro

Create or edit `.kiro/settings/mcp.json`:

```json
{
  "mcpServers": {
    "loop-engineering": {
      "command": "uvx",
      "args": ["loop"]
    }
  }
}
```

#### For Claude Desktop

**Mac:** Edit `~/Library/Application Support/Claude/claude_desktop_config.json`

**Windows:** Edit `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "loop-engineering": {
      "command": "uvx",
      "args": ["loop"]
    }
  }
}
```

**Using npm instead?** Replace `"uvx"` with `"npx"` in the command above.

**Local development?** Use:
```json
{
  "command": "python",
  "args": ["-m", "loop_engineering_mcp"]
}
```

### Step 2: Restart Your AI Agent

- **Cursor**: Reload window (Cmd/Ctrl + R)
- **Kiro**: Reconnects automatically
- **Claude Desktop**: Restart application

### Step 3: Create Your First Loop

Open your AI agent and say:

```
Create a CI triage loop that runs every 6 hours
```

The AI will set up everything automatically.

---

## Quick Example

### Creating a Loop

```
You: "Create a CI triage loop"

AI: ✅ Loop 'ci-triage' created!
    Schedule: Every 6 hours
    Verification: npm test
    Goal: All CI failures classified
    
    Files created:
    - .loop/loops.json (configuration)
    - .loop/skills/ci-triage.md (instructions)
    - .loop/state/ci-triage.json (state tracking)

You: "Start it"

AI: ✅ Loop started and will run automatically
```

### Checking Status

```
You: "What loops are running?"

AI: 📊 Active loops:
    
    ci-triage
    - Last run: 2 hours ago
    - PRs today: 3 (2 merged)
    - Acceptance rate: 67%
    - Token cost today: $4.20
```

### Viewing History

```
You: "Show me ci-triage state"

AI: 📊 State for ci-triage:
    
    Last 5 runs:
    - 2h ago: Classified 3 failures, opened 2 PRs
    - 8h ago: All tests passing, no action needed
    - 14h ago: Fixed flaky auth test, escalated DB issue
    
    Lessons learned:
    - Auth tests need AUTH_SECRET env var
    - E2E tests require Stripe webhook config
```

---

## Available Tools

Once installed, your AI agent gets these tools:

| Tool | Purpose |
|------|---------|
| `create_loop` | Set up a new automated loop |
| `start_loop` | Start/resume a loop |
| `stop_loop` | Pause a loop |
| `list_loops` | View all loops and their status |
| `delete_loop` | Remove a loop permanently |
| `add_skill` | Create custom skill templates |
| `view_state` | Check loop history and metrics |
| `add_lesson` | Record learnings for future runs |
| `get_metrics` | See overall performance |
| `run_loop_now` | Execute a loop on-demand |
| `test_verification` | Test verification commands |

Your AI agent uses these automatically when you ask for loop-related tasks.

---

## Local Development Setup

### Python

```bash
# Navigate to python package
cd python

# Install in development mode
pip install -e ".[dev]"

# Run MCP server
loop

# Run background worker (optional - for scheduled execution)
loop-worker

# Run tests
pytest

# Run tests with coverage
pytest --cov
```

### TypeScript

```bash
# Navigate to typescript package
cd typescript

# Install dependencies
npm install

# Build
npm run build

# Run MCP server
npm start

# Development mode (watch)
npm run dev

# Run tests
npm test
```

### Testing the MCP Server

1. **Install locally** (commands above)
2. **Configure in your AI agent** (see Setup section)
3. **Test with your AI agent:**
   ```
   "Do you have loop-engineering tools?"
   "Create a test loop"
   "List all loops"
   ```

---

## Project Structure

```
loop-engineering/
├── python/                  # Python MCP server
│   ├── src/
│   │   └── loop_engineering_mcp/
│   │       ├── server.py            # MCP server
│   │       ├── loop_manager.py      # Loop CRUD
│   │       ├── skill_manager.py     # Skill templates
│   │       ├── state_manager.py     # State tracking
│   │       ├── loop_executor.py     # Execution engine
│   │       ├── scheduler.py         # Cron scheduler
│   │       ├── verification_runner.py  # Test runner
│   │       ├── github_client.py     # GitHub integration
│   │       └── worker.py            # Background worker
│   └── tests/
│
├── typescript/              # TypeScript MCP server
│   ├── src/
│   │   ├── server.ts
│   │   ├── loop-manager.ts
│   │   ├── skill-manager.ts
│   │   └── state-manager.ts
│   └── tests/
│
├── shared/                  # Shared skill templates
│   └── skills/
│       ├── ci-triage.md
│       ├── dependency-updates.md
│       └── lint-fixes.md
│
└── references/              # Documentation
    ├── README.md            # Full loop engineering guide
    ├── FRAMEWORK.md         # Complete implementation guide
    └── QUICKSTART.md        # 5-minute setup
```

---

## Pre-built Skill Templates

### CI Triage
Automatically classifies CI failures and drafts fixes:
- **Flakes** - Retry once, file issue if persists
- **Bugs** - Draft fix PR immediately
- **Env issues** - Escalate with clear instructions
- **Dependency issues** - Draft rollback PR

### Dependency Updates
Keeps packages up-to-date safely:
- Checks for outdated packages
- Tests compatibility
- Creates PRs for safe updates
- Flags breaking changes for review

### Lint & Format Fixes
Maintains code quality automatically:
- Applies automated formatting
- Verifies no logic changes
- Runs tests before committing
- Opens clean-up PRs

---

## Configuration Options

### Loop Schedule (Cron Format)

```
"0 */6 * * *"    # Every 6 hours
"0 9 * * 1"      # Mondays at 9am
"0 0 * * *"      # Daily at midnight
"*/30 * * * *"   # Every 30 minutes
```

### Verification Commands

```json
{
  "verification_command": "npm test && npm run lint"
}
```

### Environment Variables

```bash
# Optional: GitHub integration
export GITHUB_TOKEN="ghp_..."

# Optional: Custom workspace
export LOOP_WORKSPACE="/path/to/project"
```

---

## Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - 5-minute setup guide
- **[FRAMEWORK.md](./FRAMEWORK.md)** - Complete implementation guide with examples
- **[references/README.md](./references/README.md)** - Loop engineering concepts and theory
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - How to contribute
- **[PROJECT_STRUCTURE.md](./PROJECT_STRUCTURE.md)** - Architecture details

---

## Troubleshooting

### MCP Server Not Found

```bash
# Check if installed
uvx loop --version

# Or for npm
npx loop
```

### Tools Not Available in AI Agent

1. Verify MCP config is valid JSON
2. Check command path is correct
3. Restart your AI agent
4. Check AI agent logs for errors

### Permission Errors

```bash
# Unix/Mac
chmod -R u+w .loop/

# Windows
icacls .loop /grant Users:F /T
```

---

## FAQ

**Q: Do I need an API key?**  
A: No! Your AI agent (Cursor/Kiro/Claude) already has its own API key. This MCP server just provides tools.

**Q: Does it work offline?**  
A: The MCP server works offline, but loop execution needs internet (to call AI APIs, create PRs, etc.)

**Q: What about security?**  
A: Loops never auto-merge to main. Human review required. Verification gates prevent bad code.

**Q: Can I use my own AI model?**  
A: Yes! Works with any AI agent that supports MCP (Cursor, Kiro, Claude Desktop, etc.)

**Q: How much does it cost?**  
A: The MCP server is free. You only pay for AI API usage (same as manual prompting, but more efficient).

---

## Credits & License

### Loop Engineering Concept
- **Author:** Codez ([@0xCodez](https://x.com/0xCodez))
- **Article:** [14-Step Roadmap](https://x.com/0xCodez/status/2064374643729773029)
- **Based on:** Anthropic engineering docs, Addy Osmani's research

### MCP Server Implementation
- **License:** MIT
- **Repository:** [GitHub](https://github.com/yourusername/loop-engineering)

### Model Context Protocol
- **Developed by:** [Anthropic](https://www.anthropic.com/)
- **Docs:** [modelcontextprotocol.io](https://modelcontextprotocol.io)

---

## Support

- 📖 **Documentation:** [FRAMEWORK.md](./FRAMEWORK.md)
- 🐛 **Report Issues:** [GitHub Issues](https://github.com/yourusername/loop-engineering/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/yourusername/loop-engineering/discussions)
- 🚀 **Quick Start:** [QUICKSTART.md](./QUICKSTART.md)

---

## What's Next?

1. **Install** the MCP server (1 command)
2. **Configure** your AI agent (add JSON config)
3. **Create** your first loop ("Create a CI triage loop")
4. **Monitor** performance (acceptance rates, time saved)
5. **Iterate** based on learnings

**Build the loop. Stay the engineer.** 🚀

---

## Star History

⭐ If this saves you time, give us a star on GitHub!

---

**Made with ❤️ by the Loop Engineering community**
