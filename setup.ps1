#Requires -Version 5.1
# Live Meeting Copilot — first-time setup
# Run: powershell -ExecutionPolicy Bypass -File .\setup.ps1

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

Write-Host ""
Write-Host "Live Meeting Copilot — Setup" -ForegroundColor Cyan
Write-Host "===================================" -ForegroundColor Cyan
Write-Host ""

# ── 1. Check Python ──────────────────────────────────────────────────────────
$python = $null
foreach ($candidate in @("python", "python3", "py")) {
    try {
        $ver = & $candidate --version 2>&1
        if ($ver -match "Python (\d+)\.(\d+)") {
            $major = [int]$Matches[1]
            $minor = [int]$Matches[2]
            if ($major -eq 3 -and $minor -ge 10) {
                $python = $candidate
                Write-Host "  [OK] Found $ver" -ForegroundColor Green
                break
            } else {
                Write-Host "  [WARN] $ver found but 3.10+ is required." -ForegroundColor Yellow
            }
        }
    } catch { }
}
if (-not $python) {
    Write-Host ""
    Write-Host "  [ERROR] Python 3.10+ not found." -ForegroundColor Red
    Write-Host "  Download from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "  Make sure to tick 'Add Python to PATH' during install." -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# ── 2. Create virtual environment ────────────────────────────────────────────
$venvPath = Join-Path $root ".venv"
if (Test-Path (Join-Path $venvPath "Scripts\python.exe")) {
    Write-Host "  [OK] Virtual environment already exists." -ForegroundColor Green
} else {
    Write-Host "  Creating virtual environment..." -ForegroundColor Cyan
    & $python -m venv $venvPath
    Write-Host "  [OK] Virtual environment created." -ForegroundColor Green
}

# ── 3. Install dependencies ──────────────────────────────────────────────────
$pip = Join-Path $venvPath "Scripts\pip.exe"
$reqFile = Join-Path $root "requirements.txt"
$novaReqFile = Join-Path $root "requirements-nova3.txt"
$wheelhouse = Join-Path $root "wheelhouse"

if (Test-Path $wheelhouse) {
    $wheelCount = @(Get-ChildItem -Path $wheelhouse -Filter *.whl -ErrorAction SilentlyContinue).Count
    if ($wheelCount -gt 0) {
        Write-Host "  Offline package detected (wheelhouse found)." -ForegroundColor Cyan
        Write-Host "  Installing dependencies from local wheelhouse..." -ForegroundColor Cyan
        & $pip install --no-index --find-links $wheelhouse -r $reqFile --quiet
        if (Test-Path $novaReqFile) {
            & $pip install --no-index --find-links $wheelhouse -r $novaReqFile --quiet
        }
        Write-Host "  [OK] Offline dependencies installed." -ForegroundColor Green
    } else {
        Write-Host "  Wheelhouse folder exists but has no .whl files. Falling back to online install..." -ForegroundColor Yellow
        Write-Host "  Upgrading pip..." -ForegroundColor Cyan
        & $pip install --upgrade pip --quiet
        Write-Host "  Installing dependencies (this may take a minute)..." -ForegroundColor Cyan
        & $pip install -r $reqFile --quiet
        if (Test-Path $novaReqFile) {
            & $pip install -r $novaReqFile --quiet
        }
        Write-Host "  [OK] Dependencies installed." -ForegroundColor Green
    }
} else {
    Write-Host "  Upgrading pip..." -ForegroundColor Cyan
    & $pip install --upgrade pip --quiet
    Write-Host "  Installing dependencies (this may take a minute)..." -ForegroundColor Cyan
    & $pip install -r $reqFile --quiet
    if (Test-Path $novaReqFile) {
        & $pip install -r $novaReqFile --quiet
    }
    Write-Host "  [OK] Dependencies installed." -ForegroundColor Green
}

# ── 4. Create .env if missing ────────────────────────────────────────────────
$envFile    = Join-Path $root ".env"
$envExample = Join-Path $root ".env.example"

if (Test-Path $envFile) {
    Write-Host "  [OK] .env already exists — skipping copy." -ForegroundColor Green
} else {
    Copy-Item $envExample $envFile
    Write-Host "  [OK] Created .env from .env.example." -ForegroundColor Green
}

# ── 5. Open .env for editing ─────────────────────────────────────────────────
Write-Host ""
Write-Host "  Opening .env in Notepad — fill in your Azure keys, then save and close." -ForegroundColor Yellow
Write-Host "  See docs\AZURE_PROVISIONING.md for instructions on getting the keys." -ForegroundColor Yellow
Write-Host ""
Start-Process notepad.exe -ArgumentList $envFile -Wait

# ── Done ─────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the app, run:" -ForegroundColor Cyan
Write-Host "  powershell -ExecutionPolicy Bypass -File .\run.ps1" -ForegroundColor White
Write-Host ""
Read-Host "Press Enter to exit"
