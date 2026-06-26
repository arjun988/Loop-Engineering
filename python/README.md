# Loop Engineering MCP Server (Python)

Python implementation of the Loop Engineering MCP server.

## Installation

### Using uvx (recommended - no installation needed)

```bash
uvx loop-engineering-mcp
```

### Using pip

```bash
pip install loop-engineering-mcp
```

## Configuration

Add to your MCP configuration file:

**Cursor** (`.cursor/mcp.json`):
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

**Kiro** (`.kiro/settings/mcp.json`):
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

**Claude Desktop**:
- Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

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

## Development

```bash
cd python
pip install -e ".[dev]"
pytest
```

## License

MIT
