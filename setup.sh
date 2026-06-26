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

# Check Node version
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version)
    echo "✅ Node detected: $NODE_VERSION"
else
    echo "⚠️  Node.js not found (optional for TypeScript version)"
fi

echo ""
echo "Choose installation method:"
echo "1) Python (recommended)"
echo "2) TypeScript/Node"
echo "3) Both"
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Installing Python package..."
        cd python
        pip install -e ".[dev]"
        echo "✅ Python package installed"
        echo ""
        echo "Test with: loop-engineering-mcp --version"
        ;;
    2)
        echo ""
        echo "Installing TypeScript package..."
        cd typescript
        npm install
        npm run build
        npm link
        echo "✅ TypeScript package installed"
        echo ""
        echo "Test with: loop-engineering-mcp"
        ;;
    3)
        echo ""
        echo "Installing both packages..."
        cd python
        pip install -e ".[dev]"
        cd ../typescript
        npm install
        npm run build
        npm link
        echo "✅ Both packages installed"
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "📝 Next steps:"
echo "1. Add to your AI agent config (Cursor, Kiro, or Claude Desktop)"
echo "2. See FRAMEWORK.md for configuration details"
echo "3. Restart your AI agent"
echo "4. Say: 'Create a CI triage loop'"
echo ""
echo "✨ Setup complete!"
