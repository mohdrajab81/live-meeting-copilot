param(
  [string]$OutputZip = "dist/live-interview-translator-deploy.zip"
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

$items = @(
  "app",
  "static",
  "docs",
  "readme.txt",
  "requirements.txt",
  "requirements-dev.txt",
  ".env.example",
  "web_translator_settings.json"
)

foreach ($item in $items) {
  $src = Join-Path $repoRoot $item
  if (Test-Path $src) {
    Copy-Item -Path $src -Destination $stageDir -Recurse -Force
  }
}

if (Test-Path $outputPath) {
  Remove-Item -Force $outputPath
}

Compress-Archive -Path (Join-Path $stageDir "*") -DestinationPath $outputPath -CompressionLevel Optimal
Remove-Item -Recurse -Force $stageDir

Write-Host "Deployment package created: $outputPath"
