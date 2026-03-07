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

# Validate runtime dependencies that are dynamically imported at execution time.
& $PythonCmd -c "import azure.ai.projects, openai" | Out-Null
if ($LASTEXITCODE -ne 0) {
  throw "Build Python is missing required packages (azure-ai-projects/openai). Use a fully provisioned env (for example: .venv)."
}

$hasNovaBuildDeps = $false
& $PythonCmd -c "import deepgram, pyaudiowpatch" | Out-Null
if ($LASTEXITCODE -eq 0) {
  $hasNovaBuildDeps = $true
  Write-Host "Nova-3 build dependencies detected; EXE will include Nova preview support." -ForegroundColor Cyan
} else {
  Write-Host "Nova-3 build dependencies not found; EXE will fall back to Azure when Nova is selected." -ForegroundColor Yellow
}

if (-not (Test-Path $buildDir)) {
  New-Item -ItemType Directory -Path $buildDir | Out-Null
}

$nuitkaArgs = @(
  "-m", "nuitka",
  "--standalone",
  "--assume-yes-for-downloads",
  "--output-dir=$buildDir",
  "--output-filename=live-meeting-copilot.exe",
  "--windows-console-mode=force",
  "--include-data-dir=$repoRoot\static=static",
  "--include-data-file=$repoRoot\.env.example=.env.example",
  "--include-data-file=$repoRoot\web_translator_settings.example.json=web_translator_settings.example.json",
  "--include-data-file=$repoRoot\LICENSE=LICENSE",
  "--include-data-file=$repoRoot\README.md=README.md",
  "--include-data-file=$repoRoot\INSTALL.md=INSTALL.md",
  "--include-data-file=$repoRoot\docs\QUICK_START_GUIDE.md=docs\QUICK_START_GUIDE.md",
  "--include-data-file=$repoRoot\docs\DUAL_MODE_SETUP.md=docs\DUAL_MODE_SETUP.md",
  "--include-data-file=$repoRoot\docs\AZURE_PROVISIONING.md=docs\AZURE_PROVISIONING.md",
  "--include-data-file=$repoRoot\docs\assets\social-preview.jpg=docs\assets\social-preview.jpg",
  "--nofollow-import-to=pandas,matplotlib,scipy,sklearn,IPython,jupyter",
  "--include-package=openai",
  "--include-package=app",
  $launcher
)

if ($hasNovaBuildDeps) {
  $nuitkaArgs += @(
    "--include-package=deepgram",
    "--include-package=pyaudiowpatch"
  )
}

Write-Host "Building standalone EXE with Nuitka (this can take several minutes)..." -ForegroundColor Cyan
& $PythonCmd @nuitkaArgs
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

# Always keep the .build cache for faster subsequent builds.
# Only remove the .dist folder (already captured in the zip) unless -KeepBuildDir.
if (-not $KeepBuildDir) {
  Remove-Item -Recurse -Force $distFolder.FullName
}

Write-Host "Portable EXE package created: $outputPath" -ForegroundColor Green
Write-Host "Note: End users do not need Python for this package." -ForegroundColor Green
