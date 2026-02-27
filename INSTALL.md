# Live Meeting Copilot — Install Guide

Real-time speech recognition, optional EN→AR translation, AI coach hints,
topic tracking, and session summary. Runs entirely on your local machine.

---

## Prerequisites

| Requirement | Notes |
|---|---|
| Windows 10 or 11 | Audio capture is Windows-only |
| Python 3.10+ (3.12 recommended) | Download from https://www.python.org/downloads/ — tick "Add to PATH" |
| Azure account | Free trial at https://azure.microsoft.com/free |
| Azure credentials | See [AZURE_PROVISIONING.md](docs/AZURE_PROVISIONING.md) |

---

## Quick Start (automated)

1. Extract the zip to a folder (e.g. `C:\tools\live-meeting-copilot`).
2. Right-click `setup.ps1` → **Run with PowerShell**, or open a terminal and run:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

3. On first run, Notepad opens with `.env`. Fill in your Azure keys (see [AZURE_PROVISIONING.md](docs/AZURE_PROVISIONING.md)). Save and close.
4. Start the app:

```powershell
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

5. Your browser opens at `http://localhost:8000`. Done.

System and instruction ownership:
- [SYSTEM_DEFINITION.md](docs/SYSTEM_DEFINITION.md)
- [DUAL_MODE_SETUP.md](docs/DUAL_MODE_SETUP.md) (dual-channel routing)

Package variants:
- `live-meeting-copilot-deploy.zip`: smaller package, installs dependencies from internet.
- `live-meeting-copilot-offline.zip`: larger package with `wheelhouse/`, no internet needed during setup.
- `live-meeting-copilot-exe.zip`: portable EXE package; no Python install required on target machine.
  - For EXE targets, install Microsoft Visual C++ Redistributable 2015-2022 if missing.

---

## Manual Steps (if you prefer)

```powershell
# 1. Create virtual environment
python -m venv .venv

# 2. Activate it
.\.venv\Scripts\Activate.ps1

# 3. Install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Create your .env
copy .env.example .env
notepad .env

# 5. Run
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

---

## Minimum .env (speech only, no AI features)

```
SPEECH_KEY=your-key-here
SPEECH_REGION=eastus
```

## Full .env (all features)

See [AZURE_PROVISIONING.md](docs/AZURE_PROVISIONING.md) for how to get each value.

```
SPEECH_KEY=...
SPEECH_REGION=eastus

TRANSLATOR_KEY=
TRANSLATOR_REGION=eastus
TRANSLATOR_ENDPOINT=https://api.cognitive.microsofttranslator.com
TRANSLATION_COST_PER_MILLION_USD=10.0

PROJECT_ENDPOINT=https://<resource>.services.ai.azure.com/api/projects/<project>
MODEL_DEPLOYMENT_NAME=gpt-4.1-mini

AGENT_ID=asst_...
AGENT_NAME=
TOPIC_MODEL_DEPLOYMENT_NAME=
TOPIC_AGENT_ID=asst_...
TOPIC_AGENT_NAME=
SUMMARY_MODEL_DEPLOYMENT_NAME=
SUMMARY_AGENT_ID=asst_...
SUMMARY_AGENT_NAME=

API_AUTH_TOKEN=
```
Notes:
- `.env.example` is the source of truth for supported environment keys.
- Service fallback aliases also supported by code:
  - `AZURE_AI_PROJECT_ENDPOINT`, `AZURE_AI_MODEL_DEPLOYMENT_NAME`
- EXE launcher runtime env vars:
  - `APP_HOST` (default `127.0.0.1`)
  - `APP_PORT` (default `8000`)
  - `OPEN_BROWSER` (`1` by default, set `0` to disable auto-open)

---

## Troubleshooting

**"running scripts is disabled"**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

**No audio / mic not found**
- Check Windows Settings → Privacy → Microphone → allow desktop apps.
- In the app UI, open the device picker and select your mic explicitly.

**Azure auth error for coach/topics/summary**
```powershell
az login
```
If you have multiple tenants:
```powershell
az login --tenant "<your-tenant-id>"
```

**`conversations.create()` unsupported**
```powershell
python -m pip install -U azure-ai-projects openai
```

---

## What runs where

Everything runs on **your machine**. No data is sent anywhere except:
- Azure Speech Service — audio for transcription (your key, your subscription).
- Azure AI Foundry agents — transcript excerpts for coach/topic/summary (your key, your subscription).

Your Azure account pays for usage. Cost depends mainly on speech time and capture mode.
