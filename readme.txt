Live Interview Translator
=========================

Real-time speech translation web app built with FastAPI.
It streams live English speech recognition and Arabic translation, supports single/dual microphone capture modes, and includes an optional interview coach powered by Azure AI Foundry agent integration.

Features
--------
- Real-time speech recognition and EN->AR translation
- Single input mode (default microphone or selected device)
- Dual input mode (local + remote microphones with separate labels)
- Live transcript stream over WebSocket (`/ws`)
- Runtime configuration API (`/api/config`)
- Optional AI coach hints (manual + auto deep suggestions)
- Session-scoped coach conversation continuity using Azure OpenAI Conversations API

Tech Stack
----------
- FastAPI + Uvicorn
- Azure Cognitive Services Speech SDK
- Pydantic / pydantic-settings
- Azure AI Projects + Azure Identity (for coach)

Project Structure
-----------------
- `app/main.py`: app bootstrap, controller, state management, routing
- `app/services/speech.py`: speech recognizer lifecycle and event wiring
- `app/services/coach.py`: Azure AI coach client integration
- `app/api/routes.py`: REST API endpoints
- `app/api/websocket.py`: WebSocket endpoint
- `static/`: frontend UI assets
- `.env`: environment variables
- `web_translator_settings.json`: persisted runtime config (created/saved by API)

Prerequisites
-------------
- Windows (audio device listing endpoint is Windows-specific)
- Python 3.10+ (3.12 recommended)
- Azure Speech resource key + region
- Optional for coach:
  - Azure AI Foundry Project endpoint
  - Model deployment name
  - Agent name/id
  - Azure CLI login (`az login`) to the correct tenant

Environment Variables
---------------------
Create or update `.env` in project root:

```
SPEECH_KEY="your-speech-key"
SPEECH_REGION="eastus2"

# Optional (coach)
PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
MODEL_DEPLOYMENT_NAME="gpt-4.1-mini"
AGENT_ID="my-profile-agent"
# or use AGENT_NAME instead of AGENT_ID
```

Install
-------
From project root (`c:\Projects\AI-102\live-interview-translator`):

```
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Run
---
```
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload
```

Open:
- App UI: `http://127.0.0.1:8000/`
- Swagger docs: `http://127.0.0.1:8000/docs`

API Endpoints
-------------
- `GET /api/state`: full app snapshot (status, transcript, logs, coach state)
- `GET /api/config`: current runtime config
- `PUT /api/config`: update runtime config (only when not running)
- `POST /api/config/save`: persist config to `web_translator_settings.json`
- `POST /api/config/reload`: reload config from `web_translator_settings.json`
- `GET /api/audio/devices`: list available capture devices (Windows)
- `POST /api/start`: start recognition
- `POST /api/stop`: stop recognition
- `POST /api/logs/clear`: clear logs
- `POST /api/transcript/clear`: clear transcript
- `POST /api/coach/clear`: clear coach history
- `POST /api/coach/ask`: manually request coach suggestion

WebSocket
---------
- `ws://127.0.0.1:8000/ws`
- Sends snapshot on connect, then streams `status`, `partial`, `final`, `log`, and `coach` events.

Runtime Config Notes
--------------------
Key fields accepted by `PUT /api/config`:
- `capture_mode`: `single` | `dual`
- `recognition_language`: default `en-US`
- `audio_source`: `default` | `device_id` (single mode)
- `input_device_id`: device id for single mode with `audio_source=device_id`
- `local_input_device_id`, `remote_input_device_id`: required in dual mode
- `local_speaker_label`, `remote_speaker_label`
- `coach_enabled`: enable/disable auto coach
- `coach_trigger_speaker`: `remote` | `local` | `default` | `any`
- `coach_cooldown_sec`, `coach_max_turns`, `coach_instruction`
- `end_silence_ms`, `initial_silence_ms`, `max_finals`, `debug`

Coach Runtime Behavior
----------------------
- On `POST /api/start`, if coach is enabled, the app initializes one conversation session and reuses it for manual and auto coach asks until stop/reset.
- Auto coach sends transcript updates incrementally (delta since last sent point), not full history every turn.
- If a new coach trigger arrives while a coach call is running, latest trigger is queued and resumed after current call completes.
- Manual coach asks continue in the same active conversation session.

Troubleshooting
---------------
- PowerShell execution policy issue:
  - `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Mic/device issue (common error "5"):
  - Check Windows microphone permissions
  - Ensure device is not exclusively locked by another app
  - Switch to default mic first, then test explicit device ids
- Coach auth failure:
  - Login with Azure CLI to the correct tenant and scope:
  - `az logout`
  - `az login --tenant "<tenant-id>" --scope "https://ai.azure.com/.default"`
- Start blocked with conversations support error:
  - Current runtime/client must support `openai_client.conversations.create()`.
  - Update dependencies and retry:
  - `python -m pip install -U azure-ai-projects openai`
  - Verify you are using the intended Python environment (`.venv`).
- After project folder rename:
  - If `.venv` breaks, recreate it and reinstall requirements

Security
--------
- Do not commit real secrets in `.env`.
- Rotate keys immediately if they were exposed.
