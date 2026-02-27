Live Meeting Copilot
====================

Real-time meeting intelligence assistant built with FastAPI.
It captures live speech, streams EN transcript, optionally adds AR translation, supports optional AI coaching hints, and tracks meeting topics with a dedicated topic-tracker agent.

Features
--------
- Real-time speech recognition with optional EN->AR translation.
- Single and dual microphone capture modes.
- WebSocket live updates for transcript, translation patches, telemetry, coach hints, and topics.
- Session summary generation (auto on stop or manual on demand) with:
  - executive summary, key points, action items, decisions, risks, key terms, metadata,
  - optional structured entities (`entities`) from GPT (PERSON/ORG/LOCATION/DATE_TIME/PRODUCT/EVENT/MONEY/PERCENT),
  - deterministic meeting insights (`meeting_insights`) for speaking balance, turn-taking, pace, and health score,
  - deterministic keyword index (`keyword_index`) with occurrences and time span, combining keywords + key terms + entities in one searchable list,
  - topic coverage timeline (`topic_breakdown`) built from agenda definitions + one-shot transcript topic grouping,
  - agenda adherence (`agenda_adherence_pct`) when planned minutes are provided in definitions.
- "From File" summary analysis: upload exported transcript CSV and load the generated result into the main Summary tab (including insights + keyword index) using the same definition-driven topic breakdown approach; backend generation does not mutate transcript/topic runtime state.
- Config API with in-memory update + save/reload/reset.
- Optional coach agent (manual ask + auto-trigger on final turns).
- Optional topic tracker agent (manual and scheduled analysis).

Core Guides
-----------
- Quick start: `docs/QUICK_START_GUIDE.md`
- Azure setup: `docs/AZURE_PROVISIONING.md`
- System definition + agent instruction ownership: `docs/SYSTEM_DEFINITION.md`
- Dual-channel routing (mic + remote): `docs/DUAL_MODE_SETUP.md`
- Packaging: `docs/deployment-package.md`

Distribution Artifacts
----------------------
- Slim package (internet install on target machine):
  - `dist\live-meeting-copilot-deploy.zip`
- Offline package (no internet install on target machine):
  - `dist\live-meeting-copilot-offline.zip`
- Portable EXE package (no Python install on target machine):
  - `dist\live-meeting-copilot-exe.zip`

Current Architecture (at a glance)
----------------------------------
- `app/main.py`: app bootstrap/lifespan, router + websocket mounting.
- `app/controller/__init__.py` (`AppController`): wiring layer only.
- `app/controller/session_manager.py`: session lifecycle, speech event handling, watchdog.
- `app/controller/coach_orchestrator.py`: coach trigger/prompt scheduling and async runs.
- `app/controller/topic_orchestrator.py`: topic configuration/state, agent calls, merge logic.
- `app/controller/summary_orchestrator.py`: summary generation state, orchestration, and broadcasting.
- `app/controller/transcript_store.py`: transcript state + translation telemetry aggregation.
- `app/controller/config_store.py`: runtime config load/save/reset/reload.
- `app/controller/broadcast_service.py`: websocket connections + logs + debug traces.
- `app/services/speech.py`: Azure Speech SDK recognizers.
- `app/services/translation_pipeline.py`: async translation queue + segment/revision guards.
- `app/services/coach.py`: Azure AI Foundry coach client.
- `app/services/topic_tracker.py`: Azure AI Foundry topic tracker client.
- `app/services/summary.py`: Azure AI Foundry summary client.
- `app/services/meeting_insights.py`: deterministic speaking-balance/pace/health + keyword index.
- `app/services/topic_summary.py`: deterministic topic duration resolution + breakdown builders.

Prerequisites
-------------
- Windows recommended (audio device listing endpoint is Windows-oriented).
- Python 3.10+ (3.12 recommended).
- Azure Speech key + region.
- Optional for coach/topics/summary:
  - Azure AI Foundry project endpoint.
  - Model deployment.
  - Agent ID or name.
  - Azure login (`az login`) for `DefaultAzureCredential`.

Environment Variables
---------------------
Required:

```
SPEECH_KEY="..."
SPEECH_REGION="eastus"
```

Optional translator override:

```
TRANSLATOR_KEY="..."
TRANSLATOR_REGION="eastus"
TRANSLATOR_ENDPOINT="https://api.cognitive.microsofttranslator.com"
TRANSLATION_COST_PER_MILLION_USD="10.0"
```
Notes:
- `TRANSLATION_COST_PER_MILLION_USD` is optional.
- If omitted/empty, translation cost estimate stays disabled.

Optional coach agent:

```
PROJECT_ENDPOINT="https://<resource>.services.ai.azure.com/api/projects/<project>"
MODEL_DEPLOYMENT_NAME="gpt-4.1-mini"
AGENT_ID="asst_..."
# or AGENT_NAME="..."
```

Optional topic agent (can reuse model/agent vars above if dedicated vars are not set):

```
TOPIC_MODEL_DEPLOYMENT_NAME="gpt-4.1-mini"
TOPIC_AGENT_ID="asst_..."
# or TOPIC_AGENT_NAME="..."
```

Optional summary agent (can reuse project/model vars above):

```
SUMMARY_MODEL_DEPLOYMENT_NAME="gpt-4.1-mini"
SUMMARY_AGENT_ID="asst_..."
# or SUMMARY_AGENT_NAME="..."
```

Optional API auth token:

```
API_AUTH_TOKEN="strong-random-token"
```

Auth behavior:
- If `API_AUTH_TOKEN` is set: required for all `/api/*` and `/ws`.
- If unset: access is restricted to loopback clients only.

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
- Swagger: `http://127.0.0.1:8000/docs`

REST API
--------
- `GET /api/state`
- `GET /api/config`
- `PUT /api/config`
- `POST /api/config/save`
- `POST /api/config/reload`
- `POST /api/config/reset-defaults`
- `GET /api/audio/devices`
- `POST /api/start`
- `POST /api/stop`
- `POST /api/logs/clear`
- `POST /api/transcript/clear`
- `POST /api/coach/clear`
- `POST /api/coach/ask`
- `POST /api/topics/configure`
- `POST /api/topics/analyze-now`
- `POST /api/topics/clear`
- `POST /api/summary/generate`
- `POST /api/summary/from-transcript`
- `POST /api/summary/clear`
- `GET /api/summary`

Rate limits:
- `/api/coach/ask`: 6 requests/minute per client IP.
- `/api/topics/analyze-now`: 4 requests/minute per client IP.
- `/api/summary/generate`: 2 requests/minute per client IP.
- `/api/summary/from-transcript`: shares the same 2/minute pool as `/api/summary/generate`.

WebSocket
---------
- Endpoint: `ws://127.0.0.1:8000/ws`
- Sends snapshot immediately on connect, then incremental events:
  - `snapshot`
  - `status`
  - `partial`
  - `final`
  - `final_patch`
  - `telemetry`
  - `coach`
  - `topics_update`
  - `summary`
  - `summary_cleared`
  - `log`
Snapshot notes:
- Includes `recording` status payload from session state for UI controls/indicators.

Runtime Config (`PUT /api/config`)
----------------------------------
Key fields:
- `capture_mode`: `single|dual`
- `recognition_language`
- `audio_source`: `default|device_id`
- `input_device_id`
- `local_input_device_id`, `remote_input_device_id`
- `local_speaker_label`, `remote_speaker_label`
- `translation_enabled`
- `summary_enabled`
- `coach_enabled`, `coach_trigger_speaker`, `coach_cooldown_sec`, `coach_max_turns`, `coach_instruction`
  - `coach_trigger_speaker` valid values: `remote|local|default|any`
- `partial_translate_min_interval_sec`
- `auto_stop_silence_sec`
- `max_session_sec`
- `end_silence_ms`, `initial_silence_ms`, `max_finals`, `debug`

Topics Config (`POST /api/topics/configure`)
--------------------------------------------
Settings are separate from `RuntimeConfig` and include:
- `enabled`
- `allow_new_topics`
- `chunk_mode`: `since_last|window`
- `interval_sec`, `window_sec`
- `agenda` (up to 20)
- `definitions` (up to 80)

Topic Runtime Notes
-------------------
- Auto topic analysis is scheduled by watchdog only when:
  - session is running,
  - topics are enabled,
  - tracker is configured,
  - interval elapsed,
  - no topic run is currently pending.
- Manual analysis uses `/api/topics/analyze-now`.
- Topic tracker payload sent to the agent is intentionally minimal and scoped to agent-needed fields.

Troubleshooting
---------------
- PowerShell script policy:
  - `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Audio device errors:
  - verify Windows microphone permissions
  - test default input first, then explicit device IDs
  - for dual mode routing, follow `docs/DUAL_MODE_SETUP.md`
  - if remote audio is not audible on speakers/headset, follow the monitoring fix in `docs/DUAL_MODE_SETUP.md`
  - if local/remote bleed appears, apply the audio-enhancement disable guidance in `docs/DUAL_MODE_SETUP.md`
- Azure auth issues (coach/topics):
  - `az logout`
  - `az login --tenant "<tenant-id>" --scope "https://ai.azure.com/.default"`
- `conversations.create()` unsupported:
  - update dependencies:
  - `python -m pip install -U azure-ai-projects openai`
- Upload endpoints fail with `Form data requires "python-multipart"`:
  - `python -m pip install -r requirements.txt`

Security
--------
- Never commit real secrets to source control.
- Rotate keys/tokens immediately if exposed.
