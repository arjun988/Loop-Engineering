# Quick Start Guide

Get Loop Engineering running in 5 minutes.

## 1. Install (Choose One)

### Option A: Python (Recommended)
```bash
uvx loop
```
No installation needed! `uvx` downloads and runs automatically.

### Option B: TypeScript/Node
```bash
npx loop
```

### Option C: From Source
```bash
# Clone repository
git clone https://github.com/yourusername/loop-engineering
cd loop-engineering

# Run setup script
# Unix/Mac:
./setup.sh

# Windows:
./setup.ps1
```

## 2. Configure Your AI Agent

### Cursor

Create `.cursor/mcp.json` in your project:
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

### Kiro

Create `.kiro/settings/mcp.json` in your project:
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

### Claude Desktop

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

## 3. Restart Your AI Agent

- **Cursor**: Reload window (Cmd/Ctrl + R)
- **Kiro**: MCP servers reconnect automatically
- **Claude Desktop**: Restart the app

## 4. Create Your First Loop

Open your AI agent and say:

```
Create a CI triage loop that runs every 6 hours
```

The AI agent will:
1. Create the loop configuration
2. Generate a skill file
3. Initialize state tracking
4. Schedule the loop

## 5. Start the Loop

```
Start the ci-triage loop
```

## 6. Check Status

```
What loops are running?
```

You'll see:
- Loop status (active/stopped)
- Last run time
- Recent PRs opened
- Acceptance rate

## Example Workflow

```
You: "Create a CI triage loop"

AI: ✅ Loop 'ci-triage' created
    Schedule: Every 6 hours
    Skill: .loop/skills/ci-triage.md
    State: .loop/state/ci-triage.json

You: "Start it"

AI: ✅ Loop started
    Status: Active
    Next run: In 6 hours

[6 hours later...]

AI: 📊 CI triage loop completed
    - Classified 3 failures
    - Opened 2 fix PRs
    - Escalated 1 complex issue

You: "Show me the state"

AI: 📊 State for ci-triage:
    Last run: 10 minutes ago
    PRs opened: 2
    PRs merged: 1
    Acceptance rate: 50%
    
    Lessons learned:
    - Auth tests need AUTH_SECRET env var
```

## Troubleshooting

### MCP Server Not Found

Check if the command works:
```bash
# Python
uvx loop --version

# Node
npx loop
```

### Tools Not Available

1. Check MCP config is valid JSON
2. Verify paths are correct
3. Restart your AI agent
4. Check AI agent logs

### Permission Errors

```bash
# Unix/Mac
chmod -R u+w .loop/

# Windows
icacls .loop /grant Users:F /T
```

## Next Steps

- Read [FRAMEWORK.md](./FRAMEWORK.md) for complete guide
- Check [README.md](./README.md) for concepts
- See [shared/skills/](./shared/skills/) for templates
- Join [Discussions](https://github.com/yourusername/loop-engineering/discussions)

## Common First Loops

### CI Triage
```
Create a CI triage loop that runs every 6 hours
```

### Dependency Updates
```
Create a weekly dependency update loop that runs Mondays at 9am
```

### Lint Fixes
```
Create a loop that applies lint fixes on every PR
```

### Custom Loop
```
Create a loop that checks for TODO comments daily and creates GitHub issues
```

---

**That's it!** You're now running loops. The AI agent handles everything else.

Questions? Check [FRAMEWORK.md](./FRAMEWORK.md) or [open an issue](https://github.com/yourusername/loop-engineering/issues).
