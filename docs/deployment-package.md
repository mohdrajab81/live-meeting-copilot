# Deployment Package

## Purpose
Create a portable zip package that others can install and run locally.

## Build Package
From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-deployment-package.ps1
```

Output:
- `dist\live-meeting-copilot-deploy.zip`

## Build Offline Package (no internet required on user machine)
From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-offline-package.ps1
```

Output:
- `dist\live-meeting-copilot-offline.zip`
Note: build machine needs internet once to download wheels into `wheelhouse/`.

## Build Portable EXE Package (no Python required on user machine)
From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-nuitka-package.ps1
```

Output:
- `dist\live-meeting-copilot-exe.zip`

## Package Contents
Default package (`live-meeting-copilot-deploy.zip`):
- `app/`
- `static/`
- `docs/`:
  - `QUICK_START_GUIDE.md`
  - `AZURE_PROVISIONING.md`
  - `DUAL_MODE_SETUP.md`
  - `SYSTEM_DEFINITION.md`
  - `EXE_DISTRIBUTION.md`
  - `deployment-package.md`
- `readme.txt`
- `INSTALL.md`
- `requirements.txt`
- `.env.example`
- `setup.ps1`
- `run.ps1`

Offline package adds:
- `wheelhouse/` (pre-downloaded wheels for `requirements.txt`)

EXE package is a separate artifact:
- `dist\live-meeting-copilot-exe.zip`
It contains:
- `live-meeting-copilot.exe`
- bundled runtime/dependencies from Nuitka standalone build

Not included on purpose:
- `.env` (local secrets stay local)
- `web_translator_settings.json` (local device IDs and personal runtime settings stay local)

## Consumer Install Steps
1. Extract zip.
2. Recommended setup path:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

If package includes `wheelhouse/`, `setup.ps1` installs from local wheels (no internet).

Manual alternative:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

For EXE package usage, follow:
- `docs/EXE_DISTRIBUTION.md`

3. Configure environment:
- Copy `.env.example` to `.env`
- Fill required keys (`SPEECH_KEY`, `SPEECH_REGION`, and optional agent/translator settings).

4. Run (recommended):

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

Manual alternative:
```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. Open:
- `http://localhost:8000`

## Notes
- If using topic/coach agents, set project/agent env vars in `.env`.
- This package is for local/self-hosted runtime; cloud deployment can reuse the same app structure.
- Operator quick-start is documented in `docs/QUICK_START_GUIDE.md`.
- Agent/instruction ownership is documented in `docs/SYSTEM_DEFINITION.md`.
- EXE distribution flow is documented in `docs/EXE_DISTRIBUTION.md`.
