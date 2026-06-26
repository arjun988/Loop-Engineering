#!/bin/bash
# Verification script to check installation

echo "🔍 Verifying Loop Engineering MCP Server Installation"
echo "====================================================="
echo ""

# Check if Python package is installed
echo "Checking Python package..."
if command -v loop-engineering-mcp &> /dev/null; then
    echo "✅ Python package installed"
    loop-engineering-mcp --version 2>&1 || echo "   (Version check skipped - MCP server)"
else
    if python3 -c "import loop_engineering_mcp" 2>/dev/null; then
        echo "✅ Python package importable"
    else
        echo "❌ Python package not found"
        echo "   Run: pip install loop-engineering-mcp"
    fi
fi

echo ""

# Check if TypeScript package is available
echo "Checking TypeScript package..."
if command -v npx &> /dev/null; then
    if npm list -g loop-engineering-mcp &> /dev/null; then
        echo "✅ TypeScript package installed globally"
    else
        echo "⚠️  TypeScript package not installed globally"
        echo "   Run: npm install -g loop-engineering-mcp"
    fi
else
    echo "⚠️  npm not found (needed for TypeScript version)"
fi

echo ""

# Check directory structure
echo "Checking project structure..."
if [ -d "python/src/loop_engineering_mcp" ]; then
    echo "✅ Python source found"
else
    echo "❌ Python source missing"
fi

if [ -d "typescript/src" ]; then
    echo "✅ TypeScript source found"
else
    echo "❌ TypeScript source missing"
fi

if [ -d "shared/skills" ]; then
    echo "✅ Skill templates found"
    SKILL_COUNT=$(ls -1 shared/skills/*.md 2>/dev/null | wc -l)
    echo "   ($SKILL_COUNT templates available)"
else
    echo "❌ Skill templates missing"
fi

echo ""

# Check documentation
echo "Checking documentation..."
DOCS=("README.md" "QUICKSTART.md" "FRAMEWORK.md" "CONTRIBUTING.md")
for doc in "${DOCS[@]}"; do
    if [ -f "$doc" ]; then
        echo "✅ $doc"
    else
        echo "❌ $doc missing"
    fi
done

echo ""
echo "====================================================="

# Summary
if command -v loop-engineering-mcp &> /dev/null || python3 -c "import loop_engineering_mcp" 2>/dev/null; then
    echo "✅ Installation verified!"
    echo ""
    echo "Next steps:"
    echo "1. Configure your AI agent (see QUICKSTART.md)"
    echo "2. Restart your AI agent"
    echo "3. Say: 'Create a CI triage loop'"
else
    echo "⚠️  Installation incomplete"
    echo ""
    echo "Run ./setup.sh to install"
fi

echo ""
