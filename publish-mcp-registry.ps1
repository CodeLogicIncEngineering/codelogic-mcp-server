# Publish server.json to the MCP Registry (local run).
# Use this to verify registry publish without re-running the full PyPI workflow.
# Requires: server.json in the repo root.

$ErrorActionPreference = "Stop"

$arch = if ([System.Runtime.InteropServices.RuntimeInformation]::ProcessArchitecture -eq "Arm64") { "arm64" } else { "amd64" }
$url = "https://github.com/modelcontextprotocol/registry/releases/latest/download/mcp-publisher_windows_$arch.tar.gz"

Write-Host "Downloading: $url" -ForegroundColor Cyan
$tarball = Join-Path $env:TEMP "mcp-publisher_windows_$arch.tar.gz"
Invoke-WebRequest -Uri $url -OutFile $tarball -UseBasicParsing

$outDir = Join-Path $env:TEMP "mcp-publisher-$PID"
New-Item -ItemType Directory -Path $outDir -Force | Out-Null
try {
    tar -xzf $tarball -C $outDir
    $exe = Join-Path $outDir "mcp-publisher.exe"
    if (-not (Test-Path $exe)) {
        throw "mcp-publisher.exe not found in archive"
    }

    Write-Host "Verifying mcp-publisher..." -ForegroundColor Cyan
    & $exe --help | Out-Null

    Push-Location $PSScriptRoot
    try {
        Write-Host "Log in to the MCP Registry (opens browser for GitHub OAuth)..." -ForegroundColor Cyan
        & $exe login github
        Write-Host "Publishing server.json to the MCP Registry..." -ForegroundColor Cyan
        & $exe publish
        Write-Host "Done." -ForegroundColor Green
    }
    finally {
        Pop-Location
    }
}
finally {
    Remove-Item -Path $outDir -Recurse -Force -ErrorAction SilentlyContinue
    Remove-Item -Path $tarball -Force -ErrorAction SilentlyContinue
}
