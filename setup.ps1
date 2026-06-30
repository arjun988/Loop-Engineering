# Setup script for Loop Engineering MCP Server (Windows PowerShell)

Write-Host "🚀 Loop Engineering MCP Server Setup" -ForegroundColor Cyan
Write-Host "======================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Python detected: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "❌ Python 3.10+ required but not found" -ForegroundColor Red
    Write-Host "   Install from: https://www.python.org/downloads/" -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "Installing Python package..." -ForegroundColor Cyan
Set-Location python
pip install -e ".[dev]"
Write-Host "✅ Python package installed" -ForegroundColor Green
Write-Host ""
Write-Host "Test with: loop-mcp --version"

Write-Host ""
Write-Host "📝 Next steps:" -ForegroundColor Cyan
Write-Host "1. Add to your AI agent config (Cursor, Kiro, or Claude Desktop)"
Write-Host "2. See FRAMEWORK.md for configuration details"
Write-Host "3. Restart your AI agent"
Write-Host "4. Say: 'Create a CI triage loop'"
Write-Host ""
Write-Host "✨ Setup complete!" -ForegroundColor Green
