# Loop Engineering MCP Server (TypeScript)

TypeScript/Node implementation of the Loop Engineering MCP server.

## Installation

### Using npx (recommended - no installation needed)

```bash
npx loop-engineering-mcp
```

### Using npm

```bash
npm install -g loop-engineering-mcp
```

## Configuration

Add to your MCP configuration file:

**Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "loop-engineering": {
      "command": "npx",
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
      "command": "npx",
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
      "command": "npx",
      "args": ["loop-engineering-mcp"]
    }
  }
}
```

## Development

```bash
cd typescript
npm install
npm run build
npm start
```

## License

MIT
