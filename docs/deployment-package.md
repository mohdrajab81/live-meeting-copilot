# Deployment Package

## Purpose
Create a portable zip package that others can install and run locally.

## Build Package
From project root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build-deployment-package.ps1
```

Output:
- `dist\live-interview-translator-deploy.zip`

## Package Contents
- `app/`
- `static/`
- `docs/`
- `readme.txt`
- `requirements.txt`
- `requirements-dev.txt`
- `.env.example`
- `web_translator_settings.json`

## Consumer Install Steps
1. Extract zip.
2. Create virtual env:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

3. Configure environment:
- Copy `.env.example` to `.env`
- Fill required keys (`SPEECH_KEY`, `SPEECH_REGION`, and optional agent/translator settings).

4. Run:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

5. Open:
- `http://localhost:8000`

## Notes
- If using topic/coach agents, set project/agent env vars in `.env`.
- This package is for local/self-hosted runtime; cloud deployment can reuse the same app structure.
