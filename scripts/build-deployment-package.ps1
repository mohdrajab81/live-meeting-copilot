param(
  [string]$OutputZip = "dist/live-meeting-copilot-deploy.zip"
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$outputPath = Join-Path $repoRoot $OutputZip
$distDir = Split-Path -Parent $outputPath
$stageDir = Join-Path $distDir "_stage"

if (-not (Test-Path $distDir)) {
  New-Item -ItemType Directory -Path $distDir | Out-Null
}

if (Test-Path $stageDir) {
  Remove-Item -Recurse -Force $stageDir
}
New-Item -ItemType Directory -Path $stageDir | Out-Null

# Keep default package slim (internet install path).
$items = @(
  "app",
  "static",
  "LICENSE",
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
  "docs\DUAL_MODE_SETUP.md",
  "docs\assets\social-preview.jpg"
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

if (Test-Path $outputPath) {
  Remove-Item -Force $outputPath
}

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $outputPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $stageDir

Write-Host "Deployment package created: $outputPath"
