# Loop Engineering MCP Server - Implementation Framework

**The easiest way to implement loop engineering in your AI coding workflow.**

This MCP (Model Context Protocol) server runs locally on your machine and integrates directly with Cursor, Kiro, Claude Desktop, or any MCP-compatible AI agent. No hosting required, no containers to manage.

---

## What This MCP Server Does

Adds powerful loop engineering tools to your AI agent:

- **`create_loop`** - Set up automated coding loops (CI triage, dependency updates, lint fixes)
- **`start_loop`** / **`stop_loop`** - Control loop execution
- **`list_loops`** - View all active and paused loops
- **`add_skill`** - Create reusable skill templates
- **`view_state`** - Check loop history and metrics
- **`configure_verification`** - Set up automated testing gates

Your AI agent uses these tools automatically when you say things like:
- *"Set up a CI triage loop that runs every 6 hours"*
- *"What loops are currently running?"*
- *"Create a dependency update loop"*

---

## Prerequisites

Before implementing any loop, verify you pass the **4-Condition Test**:

- [ ] **Task repeats** at least weekly
- [ ] **Verification is automated** (tests, linter, type checker, build)
- [ ] **Token budget** can absorb retry costs
- [ ] **Agent has senior tools** (can run code, see logs, reproduction environment)

If you fail any condition, **stop here** and use manual prompting instead.

---

## Installation

### Option 1: Python (Recommended)

**Easiest installation using uvx (no manual install needed):**

```bash
# uvx automatically downloads and runs the package
uvx loop
```

**Or install permanently:**

```bash
pip install loop
```

**Then add to your MCP configuration:**

For **Cursor**, add to `.cursor/mcp.json`:
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

For **Kiro**, add to `.kiro/settings/mcp.json`:
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

For **Claude Desktop**, add to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):
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

---

### Option 2: Node/TypeScript

**Using npx (no manual install needed):**

```bash
npx loop
```

**Or install globally:**

```bash
npm install -g loop
```

**Then add to your MCP configuration:**

For **Cursor**, add to `.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "loop-engineering": {
      "command": "npx",
      "args": ["loop"]
    }
  }
}
```

For **Kiro**, add to `.kiro/settings/mcp.json`:
```json
{
  "mcpServers": {
    "loop-engineering": {
      "command": "npx",
      "args": ["loop"]
    }
  }
}
```

For **Claude Desktop**, use the same configuration pattern as above but with `npx` command.

---

## Quick Start (3 minutes)

### 1. Install the MCP Server

```bash
# Python (recommended)
uvx loop

# OR Node
npx loop
```

### 2. Add to Your AI Agent Config

Add the MCP server to your config file (see [Installation](#installation) section above for exact paths).

###3. Restart Your AI Agent

- **Cursor**: Reload window or restart app
- **Kiro**: MCP servers auto-reconnect on config changes
- **Claude Desktop**: Restart the application

### 4. Start Using It

Simply talk to your AI agent naturally:

```
You: "Set up a CI triage loop that runs every 6 hours"

AI Agent: [uses create_loop tool]
✅ Loop created: ci-triage
✅ Skill file created at .loop/skills/ci-triage.md
✅ State initialized at .loop/state/ci-triage.json
✅ Scheduled to run every 6 hours

You: "What's the status of my loops?"

AI Agent: [uses list_loops tool]
📊 Active loops:
- ci-triage: Last run 2h ago, 3 PRs opened today, 67% acceptance rate
```

**That's it!** The AI agent handles everything using the MCP tools.

---

## Resources

- [Loop Engineering Concepts](./README.md) - Understand the theory
- [MCP Documentation](https://modelcontextprotocol.io) - Learn about MCP
- [GitHub Repository](https://github.com/yourusername/loop-engineering) - Source code and issues

---

**Build the loop. Stay the engineer.**
