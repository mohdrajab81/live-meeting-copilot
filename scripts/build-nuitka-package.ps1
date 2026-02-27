param(
  [string]$PythonCmd = "python",
  [string]$OutputZip = "dist/live-meeting-copilot-exe.zip",
  [switch]$KeepBuildDir
)

$ErrorActionPreference = "Stop"

$repoRoot = Split-Path -Parent $PSScriptRoot
$distDir = Join-Path $repoRoot "dist"
$buildDir = Join-Path $distDir "_nuitka_build"
$outputPath = Join-Path $repoRoot $OutputZip

if (-not (Test-Path $distDir)) {
  New-Item -ItemType Directory -Path $distDir | Out-Null
}

$launcher = Join-Path $repoRoot "app_launcher.py"
if (-not (Test-Path $launcher)) {
  throw "Missing launcher file: $launcher"
}

Write-Host "Checking Nuitka availability..." -ForegroundColor Cyan
& $PythonCmd -m nuitka --version | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Nuitka is not installed. Install with: $PythonCmd -m pip install nuitka"
}

if (Test-Path $buildDir) {
  Remove-Item -Recurse -Force $buildDir
}
New-Item -ItemType Directory -Path $buildDir | Out-Null

$args = @(
  "-m", "nuitka",
  "--standalone",
  "--remove-output",
  "--assume-yes-for-downloads",
  "--output-dir=$buildDir",
  "--output-filename=live-meeting-copilot.exe",
  "--windows-console-mode=force",
  "--include-data-dir=$repoRoot\static=static",
  "--include-data-file=$repoRoot\.env.example=.env.example",
  "--include-data-file=$repoRoot\readme.txt=readme.txt",
  "--include-data-file=$repoRoot\INSTALL.md=INSTALL.md",
  "--include-data-file=$repoRoot\docs\QUICK_START_GUIDE.md=docs\QUICK_START_GUIDE.md",
  "--include-data-file=$repoRoot\docs\DUAL_MODE_SETUP.md=docs\DUAL_MODE_SETUP.md",
  "--include-data-file=$repoRoot\docs\AZURE_PROVISIONING.md=docs\AZURE_PROVISIONING.md",
  "--include-data-file=$repoRoot\docs\SYSTEM_DEFINITION.md=docs\SYSTEM_DEFINITION.md",
  "--include-data-file=$repoRoot\docs\EXE_DISTRIBUTION.md=docs\EXE_DISTRIBUTION.md",
  "--nofollow-import-to=pandas,matplotlib,scipy,sklearn,IPython,jupyter",
  "--include-package=app",
  $launcher
)

Write-Host "Building standalone EXE with Nuitka (this can take several minutes)..." -ForegroundColor Cyan
& $PythonCmd @args
if ($LASTEXITCODE -ne 0) {
  throw "Nuitka build failed."
}

$distFolder = Get-ChildItem -Path $buildDir -Directory | Where-Object { $_.Name -like "*.dist" } | Select-Object -First 1
if (-not $distFolder) {
  throw "Nuitka output folder (*.dist) not found in $buildDir"
}

# Remove caches/bytecode artifacts if any.
Get-ChildItem -Path $distFolder.FullName -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $distFolder.FullName -Recurse -Include *.pyc,*.pyo -File -ErrorAction SilentlyContinue |
  Remove-Item -Force -ErrorAction SilentlyContinue

if (Test-Path $outputPath) {
  Remove-Item -Force $outputPath
}

Compress-Archive -Path (Join-Path $distFolder.FullName "*") -DestinationPath $outputPath -CompressionLevel Optimal

if (-not $KeepBuildDir) {
  Remove-Item -Recurse -Force $buildDir
}

Write-Host "Portable EXE package created: $outputPath" -ForegroundColor Green
Write-Host "Note: End users do not need Python for this package." -ForegroundColor Green
