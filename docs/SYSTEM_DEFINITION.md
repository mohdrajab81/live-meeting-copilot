# System Definition

> **Developer document.** This file is a reference for developers and maintainers.
> It is not needed to install, configure, or use the application.
> End users should refer to `INSTALL.md` and `docs/AZURE_PROVISIONING.md` instead.

---

## Product Identity

| Field | Value |
| --- | --- |
| Product name | Live Meeting Copilot |
| Repository folder | `live-meeting-copilot` |
| Core purpose | Real-time transcription, Arabic translation, AI coaching, topic definitions, and meeting summary |

---

## Runtime Boundaries

| Layer | Technology |
| --- | --- |
| Frontend | `static/` — single-page app, no framework |
| API and WebSocket backend | FastAPI (`app/`) |
| Speech transcription | Azure AI Services — Speech SDK |
| Arabic translation | Azure AI Services — Translator API |
| AI coaching, summary | Azure AI Foundry agents |

---

## Agent Catalog

| Product Name | Env Binding | Purpose |
| --- | --- | --- |
| Conversation Coach | `GUIDANCE_AGENT_NAME` | Real-time coaching suggestions for the local speaker |
| Meeting Summarizer | `SUMMARY_AGENT_NAME` | Final structured meeting summary generation |

Agent names in this table refer to the display names used in Azure AI Foundry. These must exactly match the values set in `.env`.

---

## Instruction Ownership Model

Agent behavior is shaped by four layers, listed in order of practical influence on the model response:

| Priority | Layer | Source | Scope |
| --- | --- | --- | --- |
| 1 (highest) | Request context data | Code — transcript turns, speaker labels, agenda, runtime state | Per-request; highest signal |
| 2 | Runtime web instruction | UI Settings → `PUT /api/config` → `coach_instruction` | Per-session coaching style; coach agent only |
| 3 | Code-authored request framing | `coach_orchestrator.py`, `topic_orchestrator.py`, `summary.py` | Per-request schema constraints and task framing |
| 4 (lowest) | Azure baseline system instruction | Azure AI Foundry agent system instructions | Persistent persona and global behaviour |

---

## Configuration Sources

| What You Are Configuring | Where to Configure It |
| --- | --- |
| Credentials, endpoints, agent bindings | `.env` |
| Runtime settings (capture mode, language, toggles, coach instruction) | Web UI → `PUT /api/config` |
| Agenda topics and session definitions | Web UI → Topics panel |
| Agent baseline instructions and model selection | Azure AI Foundry portal |
| Request schema, payload structure, deterministic post-processing | Source code |

---

## Key Source Locations

| Component | File |
| --- | --- |
| Application entry point | `app/main.py` |
| Controller wiring layer | `app/controller/__init__.py` |
| Session lifecycle | `app/controller/session_manager.py` |
| Topic orchestration | `app/controller/topic_orchestrator.py` |
| Coach orchestration | `app/controller/coach_orchestrator.py` |
| Summary orchestration | `app/controller/summary_orchestrator.py` |
| Transcript store | `app/controller/transcript_store.py` |
| Runtime config store | `app/controller/config_store.py` |
| Broadcast service | `app/controller/broadcast_service.py` |
| Speech SDK integration | `app/services/speech.py` |
| Translation pipeline | `app/services/translation_pipeline.py` |
| Coach agent client | `app/services/coach.py` |
| Summary agent client | `app/services/summary.py` |
| API routes | `app/api/routes.py` |
| API authentication | `app/api/auth.py` |
| Environment validation | `app/config.py` |
| EXE launcher | `app_launcher.py` |

---

## Non-Goals (Current Version)

- No web UI editor for summary-agent system instructions.
- No runtime hot-swap of prompt templates for summary from the UI.
- No external prompt registry or versioning service.
