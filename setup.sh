#!/bin/bash
# Setup script for Loop Engineering MCP Server (Unix/Mac)

echo "🚀 Loop Engineering MCP Server Setup"
echo "======================================"
echo ""

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | awk '{print $2}')
    echo "✅ Python detected: $PYTHON_VERSION"
else
    echo "❌ Python 3.10+ required but not found"
    echo "   Install from: https://www.python.org/downloads/"
    exit 1
fi

echo ""
echo "Installing Python package..."
cd python
pip install -e ".[dev]"
echo "✅ Python package installed"
echo ""
echo "Test with: loop-mcp --version"

echo ""
echo "📝 Next steps:"
echo "1. Add to your AI agent config (Cursor, Kiro, or Claude Desktop)"
echo "2. See FRAMEWORK.md for configuration details"
echo "3. Restart your AI agent"
echo "4. Say: 'Create a CI triage loop'"
echo ""
echo "✨ Setup complete!"
