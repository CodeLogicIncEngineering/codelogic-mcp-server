# Ensure proper UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "Starting MCP server with UTF-8 encoding..." -ForegroundColor Green

# Run with npx
npx @modelcontextprotocol/inspector python ./src/start_server.py