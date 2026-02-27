# EXE Distribution (No Python on Target Machine)

This flow creates a portable Windows package using Nuitka standalone mode.

Output artifact:
- `dist/live-meeting-copilot-exe.zip`

## What target users need
- Windows machine
- Azure credentials in `.env`
- No Python installation required
- No dependency download required at runtime

## Build machine prerequisites
- Python 3.10+
- Nuitka installed:

```powershell
python -m pip install --upgrade nuitka
```
Notes:
- On first build, Nuitka can auto-download its supported MinGW gcc toolchain.
- Visual Studio Build Tools are not mandatory for this pipeline.

## Build command
From repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-nuitka-package.ps1
```

Optional:

```powershell
# Keep raw Nuitka build output for troubleshooting
powershell -ExecutionPolicy Bypass -File .\scripts\build-nuitka-package.ps1 -KeepBuildDir
```
Script parameters:
- `-PythonCmd` to select Python executable.
- `-OutputZip` to change artifact path/name.

## What the package includes
- `live-meeting-copilot.exe`
- compiled Python runtime/dependencies
- `static/`
- docs:
  - `docs/QUICK_START_GUIDE.md`
  - `docs/DUAL_MODE_SETUP.md`
  - `docs/AZURE_PROVISIONING.md`
  - `docs/SYSTEM_DEFINITION.md`
  - `docs/EXE_DISTRIBUTION.md`
- `.env.example`
- `readme.txt`
- `INSTALL.md`

## First run on target machine
1. Extract zip.
2. Copy `.env.example` to `.env`.
3. Fill `SPEECH_KEY` and `SPEECH_REGION`.
4. Run `live-meeting-copilot.exe`.
5. If needed, install Microsoft Visual C++ Redistributable 2015-2022 on the target machine.

If `.env` is missing, launcher auto-creates it from `.env.example`, opens it, then exits.
After saving keys, run the EXE again.

Runtime environment knobs:
- `APP_HOST` (default `127.0.0.1`)
- `APP_PORT` (default `8000`)
- `OPEN_BROWSER` (default `1`, set `0` to disable auto-open)

Build behavior note:
- This script uses `--remove-output`, so each build is a clean rebuild.
