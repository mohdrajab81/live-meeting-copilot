param(
  [string]$OutputZip = "dist/live-meeting-copilot-offline.zip",
  [string]$PythonCmd = "python"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outputPath = Join-Path $repoRoot $OutputZip
$distDir = Split-Path -Parent $outputPath
$stageDir = Join-Path $distDir "_stage_offline"
$wheelhouseDir = Join-Path $stageDir "wheelhouse"
$legacyZip = Join-Path $distDir "live-meeting-copilot-deploy.zip"

if (-not (Test-Path $distDir)) {
  New-Item -ItemType Directory -Path $distDir | Out-Null
}

# Clean legacy artifact name so users only see current branding.
if (Test-Path $legacyZip) {
  Remove-Item -Force $legacyZip
}

if (Test-Path $stageDir) {
  Remove-Item -Recurse -Force $stageDir
}
New-Item -ItemType Directory -Path $stageDir | Out-Null
New-Item -ItemType Directory -Path $wheelhouseDir | Out-Null

$items = @(
  "app",
  "static",
  "README.md",
  "INSTALL.md",
  "requirements.txt",
  "requirements-nova3.txt",
  ".env.example",
  "web_translator_settings.example.json",
  "setup.ps1",
  "run.ps1"
)

$docFiles = @(
  "docs\QUICK_START_GUIDE.md",
  "docs\AZURE_PROVISIONING.md",
  "docs\DUAL_MODE_SETUP.md"
)

$missing = @()
foreach ($item in $items) {
  $src = Join-Path $repoRoot $item
  if (-not (Test-Path $src)) {
    $missing += $item
  }
}
foreach ($doc in $docFiles) {
  $src = Join-Path $repoRoot $doc
  if (-not (Test-Path $src)) {
    $missing += $doc
  }
}
if ($missing.Count -gt 0) {
  throw "Missing required package files: $($missing -join ', ')"
}

foreach ($item in $items) {
  $src = Join-Path $repoRoot $item
  Copy-Item -Path $src -Destination $stageDir -Recurse -Force
}

foreach ($doc in $docFiles) {
  $src = Join-Path $repoRoot $doc
  $dst = Join-Path $stageDir $doc
  $dstDir = Split-Path -Parent $dst
  if (-not (Test-Path $dstDir)) {
    New-Item -ItemType Directory -Path $dstDir | Out-Null
  }
  Copy-Item -Path $src -Destination $dst -Force
}

# Strip cache/bytecode artifacts to keep package small.
Get-ChildItem -Path $stageDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $stageDir -Recurse -Include *.pyc,*.pyo -File -ErrorAction SilentlyContinue |
  Remove-Item -Force -ErrorAction SilentlyContinue

$requirementsPath = Join-Path $repoRoot "requirements.txt"
$novaRequirementsPath = Join-Path $repoRoot "requirements-nova3.txt"
Write-Host "Downloading dependency wheels for offline install..." -ForegroundColor Cyan
& $PythonCmd -m pip download --dest $wheelhouseDir --requirement $requirementsPath --prefer-binary
if ($LASTEXITCODE -ne 0) {
  throw "pip download failed. Offline package not created."
}
if (Test-Path $novaRequirementsPath) {
  & $PythonCmd -m pip download --dest $wheelhouseDir --requirement $novaRequirementsPath --prefer-binary
  if ($LASTEXITCODE -ne 0) {
    throw "pip download for requirements-nova3.txt failed. Offline package not created."
  }
}

if (Test-Path $outputPath) {
  Remove-Item -Force $outputPath
}

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $outputPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $stageDir

Write-Host "Offline deployment package created: $outputPath"
