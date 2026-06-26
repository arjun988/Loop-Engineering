# Project Structure

Complete overview of the Loop Engineering MCP Server repository.

## Directory Tree

```
loop-engineering/
│
├── README.md                       # Main documentation
├── QUICKSTART.md                   # 5-minute setup guide
├── FRAMEWORK.md                    # Complete implementation guide
├── CONTRIBUTING.md                 # Contribution guidelines
├── PROJECT_STRUCTURE.md            # This file
├── LICENSE                         # MIT License
├── .gitignore                      # Git ignore rules
│
├── setup.sh                        # Unix/Mac setup script
├── setup.ps1                       # Windows setup script
│
├── python/                         # Python MCP Server
│   ├── pyproject.toml             # Python package configuration
│   ├── README.md                  # Python-specific docs
│   │
│   ├── src/
│   │   └── loop_engineering_mcp/
│   │       ├── __init__.py        # Package initialization
│   │       ├── __main__.py        # Entry point
│   │       ├── server.py          # MCP server implementation
│   │       ├── loop_manager.py    # Loop CRUD operations
│   │       ├── skill_manager.py   # Skill template management
│   │       └── state_manager.py   # State tracking & metrics
│   │
│   └── tests/                     # Python tests (to be added)
│
├── typescript/                    # TypeScript MCP Server
│   ├── package.json              # NPM package configuration
│   ├── tsconfig.json             # TypeScript configuration
│   ├── README.md                 # TypeScript-specific docs
│   │
│   ├── src/
│   │   ├── index.ts              # Entry point
│   │   ├── server.ts             # MCP server implementation
│   │   ├── loop-manager.ts       # Loop CRUD operations
│   │   ├── skill-manager.ts      # Skill template management
│   │   └── state-manager.ts      # State tracking & metrics
│   │
│   └── tests/                    # TypeScript tests (to be added)
│
└── shared/                       # Shared resources
    └── skills/                   # Pre-built skill templates
        ├── ci-triage.md         # CI failure triage
        ├── dependency-updates.md # Dependency management
        └── lint-fixes.md        # Automated formatting
```

## Key Files

### Documentation

| File | Purpose |
|------|---------|
| `README.md` | Main entry point, concepts, quick start |
| `QUICKSTART.md` | 5-minute setup guide |
| `FRAMEWORK.md` | Complete implementation guide with examples |
| `CONTRIBUTING.md` | How to contribute |
| `PROJECT_STRUCTURE.md` | This file - project overview |

### Setup

| File | Purpose |
|------|---------|
| `setup.sh` | Unix/Mac installation script |
| `setup.ps1` | Windows PowerShell installation script |
| `.gitignore` | Git ignore rules |
| `LICENSE` | MIT License |

### Python Package

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package metadata, dependencies |
| `__init__.py` | Package initialization |
| `__main__.py` | CLI entry point |
| `server.py` | MCP server, tool definitions |
| `loop_manager.py` | Create/start/stop/list loops |
| `skill_manager.py` | Manage skill templates |
| `state_manager.py` | Track state, metrics, lessons |

### TypeScript Package

| File | Purpose |
|------|---------|
| `package.json` | Package metadata, dependencies |
| `tsconfig.json` | TypeScript compiler config |
| `index.ts` | CLI entry point |
| `server.ts` | MCP server, tool definitions |
| `loop-manager.ts` | Create/start/stop/list loops |
| `skill-manager.ts` | Manage skill templates |
| `state-manager.ts` | Track state, metrics, lessons |

### Skill Templates

| File | Purpose |
|------|---------|
| `ci-triage.md` | CI failure classification & fixes |
| `dependency-updates.md` | Package update management |
| `lint-fixes.md` | Automated code formatting |

## Runtime Structure

When a user initializes loops in their project:

```
user-project/
├── .loop/                        # Created automatically
│   ├── loops.json               # Loop configurations
│   │
│   ├── skills/                  # Skill instances
│   │   ├── ci-triage.md
│   │   ├── dependency-updates.md
│   │   └── custom-skill.md
│   │
│   ├── state/                   # Loop state & history
│   │   ├── ci-triage.json
│   │   └── dependency-updates.json
│   │
│   └── logs/                    # Execution logs
│       └── loop-runner.log
│
└── [user's existing code]
```

## MCP Tool Architecture

```
┌─────────────────────────────────────┐
│     AI Agent (Cursor/Kiro/Claude)  │
│                                     │
│  User: "Create a CI triage loop"   │
└──────────────┬──────────────────────┘
               │
               │ MCP Protocol
               │
┌──────────────▼──────────────────────┐
│    Loop Engineering MCP Server      │
│                                     │
│  ┌──────────────────────────────┐  │
│  │  server.py / server.ts       │  │
│  │  - Registers 11 tools        │  │
│  │  - Handles tool calls        │  │
│  └──────────┬───────────────────┘  │
│             │                       │
│  ┌──────────▼───────────────────┐  │
│  │  Managers                    │  │
│  │  - LoopManager               │  │
│  │  - SkillManager              │  │
│  │  - StateManager              │  │
│  └──────────┬───────────────────┘  │
│             │                       │
└─────────────┼───────────────────────┘
              │
              │ File System
              │
┌─────────────▼───────────────────────┐
│    User's Project                   │
│    .loop/                           │
│    ├── loops.json                   │
│    ├── skills/                      │
│    ├── state/                       │
│    └── logs/                        │
└─────────────────────────────────────┘
```

## Data Flow

### Creating a Loop

```
User → AI Agent
      ↓
AI Agent calls create_loop()
      ↓
MCP Server receives request
      ↓
LoopManager.createLoop()
  - Writes loops.json
      ↓
SkillManager.createSkill()
  - Writes skill.md
      ↓
StateManager.initializeState()
  - Writes state.json
      ↓
Return success message
      ↓
AI Agent shows result to user
```

### Running a Loop (Future)

```
Scheduler triggers at cron time
      ↓
Read loop config from loops.json
      ↓
Read skill from skills/name.md
      ↓
Read state from state/name.json
      ↓
Execute AI agent with skill instructions
      ↓
Run verification command
      ↓
Update state with results
      ↓
Create PR if verification passes
      ↓
Log to logs/loop-runner.log
```

## Package Distribution

### Python (PyPI)

```
python/
  ├── src/loop_engineering_mcp/
  └── pyproject.toml

Build:   python -m build
Publish: twine upload dist/*
Install: pip install loop-mcp
Run:     uvx loop-mcp
```

### TypeScript (NPM)

```
typescript/
  ├── src/
  ├── package.json
  └── tsconfig.json

Build:   npm run build
Publish: npm publish
Install: npm install -g loop-mcp
Run:     npx loop-mcp
```

## Development Workflow

1. **Clone Repository**
   ```bash
   git clone https://github.com/yourusername/loop-engineering
   cd loop-engineering
   ```

2. **Install Dependencies**
   ```bash
   # Python
   cd python
   pip install -e ".[dev]"
   
   # TypeScript
   cd typescript
   npm install
   ```

3. **Make Changes**
   - Edit relevant files
   - Follow code style guidelines

4. **Test**
   ```bash
   # Python
   pytest
   
   # TypeScript
   npm test
   ```

5. **Build**
   ```bash
   # Python
   python -m build
   
   # TypeScript
   npm run build
   ```

6. **Submit PR**
   - Create branch
   - Commit changes
   - Push and open PR

## Configuration Files

### Python
- `pyproject.toml` - Package metadata, dependencies, build config
- `.python-version` - Python version (optional)
- `pytest.ini` - Test configuration (optional)

### TypeScript
- `package.json` - Package metadata, scripts, dependencies
- `tsconfig.json` - TypeScript compiler options
- `.npmignore` - Files to exclude from NPM package

### Both
- `.gitignore` - Git ignore patterns
- `README.md` - Package-specific documentation

## Future Additions

Planned but not yet implemented:

```
loop-engineering/
├── web/                          # Web UI (planned)
│   ├── dashboard/               # Metrics dashboard
│   └── configurator/            # Visual loop builder
│
├── cli/                         # Enhanced CLI (planned)
│   └── interactive.py           # Interactive mode
│
├── integrations/                # Third-party integrations (planned)
│   ├── github/
│   ├── linear/
│   └── slack/
│
└── examples/                    # Example projects (planned)
    ├── nodejs-api/
    ├── python-api/
    └── rust-cli/
```

---

This structure is designed for:
- ✅ Easy contribution
- ✅ Clear separation of concerns
- ✅ Both Python and TypeScript support
- ✅ Extensibility
- ✅ Package distribution (PyPI & NPM)
