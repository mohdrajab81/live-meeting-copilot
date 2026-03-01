#Requires -Version 5.1
# Live Meeting Copilot — start the app
# Run: powershell -ExecutionPolicy Bypass -File .\run.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

# ── Sanity checks ─────────────────────────────────────────────────────────────
$uvicorn = Join-Path $root ".venv\Scripts\uvicorn.exe"
if (-not (Test-Path $uvicorn)) {
    Write-Host ""
    Write-Host "  [ERROR] Dependencies not installed. Run setup.ps1 first." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

$envFile = Join-Path $root ".env"
if (-not (Test-Path $envFile)) {
    Write-Host ""
    Write-Host "  [ERROR] .env file not found. Run setup.ps1 first." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Quick check that AZURE_AI_SERVICES_KEY is not a placeholder
$envContent = Get-Content $envFile -Raw
if ($envContent -match "AZURE_AI_SERVICES_KEY=your-azure-ai-services-key" -or
    $envContent -notmatch "AZURE_AI_SERVICES_KEY=\S") {
    Write-Host ""
    Write-Host "  [WARN] AZURE_AI_SERVICES_KEY looks empty or is still the placeholder." -ForegroundColor Yellow
    Write-Host "  The app will start but transcription won't work without a real key." -ForegroundColor Yellow
    Write-Host "  Edit .env and add your Azure AI Services key, then restart." -ForegroundColor Yellow
    Write-Host ""
}

# ── Open browser after a short delay ─────────────────────────────────────────
$url = "http://localhost:8000"
Write-Host ""
Write-Host "  Starting Live Meeting Copilot..." -ForegroundColor Cyan
Write-Host "  URL: $url" -ForegroundColor White
Write-Host "  Press Ctrl+C to stop." -ForegroundColor White
Write-Host ""

Start-Job -ScriptBlock {
    param($u)
    Start-Sleep -Seconds 3
    Start-Process $u
} -ArgumentList $url | Out-Null

# ── Launch uvicorn ────────────────────────────────────────────────────────────
Set-Location $root
& $uvicorn app.main:app --host 0.0.0.0 --port 8000
