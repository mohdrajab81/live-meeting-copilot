# Architecture

> Canonical technical reference for developers and maintainers.
> This document owns system structure, contracts, flows, invariants, and operational boundaries.
> Historical explanations and design storytelling belong in `ENGINEERING_RATIONALE.md`.

---

## Table of Contents

1. [Purpose and Audience](#1-purpose-and-audience)
2. [Scope](#2-scope)
3. [Non-Goals](#3-non-goals)
4. [System Context](#4-system-context)
5. [Runtime Boundaries](#5-runtime-boundaries)
6. [High-Level Component Model](#6-high-level-component-model)
7. [Module Ownership](#7-module-ownership)
8. [Configuration Model](#8-configuration-model)
9. [Agent Catalog](#9-agent-catalog)
10. [Instruction Ownership Model](#10-instruction-ownership-model)
11. [Runtime Flows](#11-runtime-flows)
12. [Concurrency Model](#12-concurrency-model)
13. [Locking Model](#13-locking-model)
14. [Core Data Contracts](#14-core-data-contracts)
15. [REST API Contracts](#15-rest-api-contracts)
16. [WebSocket Event Catalog](#16-websocket-event-catalog)
17. [Guardrails and Limits](#17-guardrails-and-limits)
18. [Security Model](#18-security-model)
19. [Observability and Telemetry](#19-observability-and-telemetry)
20. [Invariants](#20-invariants)
21. [Failure Handling](#21-failure-handling)
22. [Validation Matrix](#22-validation-matrix)
23. [Key Source Locations](#23-key-source-locations)
24. [Suggested Review Order](#24-suggested-review-order)

---

## 1. Purpose and Audience

This file is the technical source of truth for how Live Meeting Copilot is structured and how it behaves at runtime.

Audience:
- developers making code changes
- maintainers diagnosing defects
- reviewers validating system behavior against implementation

This document should answer:
- what owns each part of the system
- how runtime data moves through the application
- which contracts are exposed over HTTP and WebSocket
- which invariants must remain true

---

## 2. Scope

The system:
- captures live speech on Windows in single-input or dual-input mode
- produces live English transcript updates
- optionally translates committed and live speech from English to Arabic
- optionally provides AI coaching hints during the meeting
- optionally generates structured meeting summaries at stop time or from exported transcript CSV files
- persists runtime settings and selected UI state locally

This document covers:
- backend and frontend runtime boundaries
- internal layering
- API and WebSocket contracts
- concurrency and lock model
- system limits and operational guardrails

This document does not attempt to teach the reasoning behind every design decision. That belongs in `ENGINEERING_RATIONALE.md`.

---

## 3. Non-Goals

Current non-goals:
- no web UI editor for summary-agent system instructions
- no runtime hot-swap of prompt templates for summary from the UI
- no external prompt registry or prompt versioning service
- no remote multi-user deployment mode
- no cross-platform audio capture support; the application targets Windows-only capture paths

---

## 4. System Context

Live Meeting Copilot is a local-first Windows application composed of:
- a browser-based single-page frontend served from `static/`
- a FastAPI backend in `app/`
- optional Azure AI Foundry agents for coaching and summary generation
- Azure AI Services for speech recognition and translation
- an optional Nova-3 preview speech backend for alternate live capture

The browser and backend run on the same machine. HTTP and WebSocket access are restricted to loopback clients.

---

## 5. Runtime Boundaries

| Layer | Technology | Responsibility |
| --- | --- | --- |
| Frontend | Vanilla HTML/CSS/JavaScript | Render transcript, settings, coach, summary, logs, exports |
| API backend | FastAPI | Serve config/session/control endpoints |
| WebSocket backend | FastAPI / Starlette | Push snapshot and incremental runtime events |
| Controller layer | Python controller modules | Own runtime state and orchestration |
| Service layer | Python service modules | External service integration and background processing |
| Speech backend | Azure Speech SDK or Nova-3 preview | Produce normalized live speech events |
| Translation backend | Azure Translator REST API | Translate EN to AR |
| AI agent backend | Azure AI Foundry / Azure Responses API | Coach suggestions and summary generation |

Boundary rules:
- frontend does not talk directly to Azure services
- service modules do not mutate UI state directly
- controller modules are the only place where runtime orchestration decisions are made
- WebSocket payloads are the canonical real-time sync channel for transcript, coach, summary, logs, and telemetry

---

## 6. High-Level Component Model

Design principle: controllers own decisions and state transitions, while services own external integrations and background worker mechanics.

```text
Browser UI
  -> REST API for control/config/export actions
  -> WebSocket for snapshot and live updates

FastAPI app
  -> API routes
  -> WebSocket endpoint
  -> AppController wiring layer

Controller modules
  -> SessionManager
  -> TranscriptStore
  -> CoachOrchestrator
  -> TopicOrchestrator
  -> SummaryOrchestrator
  -> ConfigStore
  -> BroadcastService

Service modules
  -> SpeechProviderService
  -> Azure Speech backend / Nova-3 preview backend
  -> TranslationPipeline
  -> ShadowFinalTranslationPipeline
  -> CoachService
  -> SummaryService
  -> meeting_insights helpers
  -> topic_summary helpers
```

---

## 7. Module Ownership

### Entry and App Wiring

| File | Ownership |
| --- | --- |
| `app/main.py` | FastAPI bootstrap, lifespan startup/shutdown, route registration, static mount |
| `app/controller/__init__.py` | `AppController` wiring layer and public facade |
| `app_launcher.py` | EXE/runtime launcher entry point |

### API Layer

| File | Ownership |
| --- | --- |
| `app/api/routes.py` | REST control plane for config, session, coach, topics, summary, logs, transcript |
| `app/api/websocket.py` | WebSocket endpoint and initial snapshot send |
| `app/api/auth.py` | Loopback-only auth for HTTP and WebSocket |

### Controller Layer

| File | Ownership |
| --- | --- |
| `app/controller/session_manager.py` | Session lifecycle, speech event handling, watchdog |
| `app/controller/transcript_store.py` | Finals, live partials, translation application, translation telemetry |
| `app/controller/coach_orchestrator.py` | Coach triggering, prompt construction, async scheduling, manual asks |
| `app/controller/topic_orchestrator.py` | Topic definitions state used as summary agenda context |
| `app/controller/summary_orchestrator.py` | Summary execution, summary state, deterministic post-processing |
| `app/controller/config_store.py` | Runtime config load/save/reload/reset |
| `app/controller/broadcast_service.py` | WebSocket fanout, log buffer, debug trace emission |

### Service Layer

| File | Ownership |
| --- | --- |
| `app/services/speech_provider.py` | Speech backend selection and Azure fallback |
| `app/services/speech.py` | Azure Speech recognizers and normalized speech/status events |
| `app/services/speech_nova3.py` | Nova-3 preview live capture and event normalization |
| `app/services/translation_pipeline.py` | Async translation queue, priority ordering, stale-result guards |
| `app/services/shadow_translation_pipeline.py` | Optional second-pass final translation worker |
| `app/services/coach.py` | Azure AI Foundry coach client with conversation continuity |
| `app/services/summary.py` | Azure AI Foundry summary client with structured JSON extraction |
| `app/services/topic_summary.py` | Topic normalization, coverage repair, deterministic duration resolution |
| `app/services/meeting_insights.py` | Deterministic insights and keyword index generation |

### Frontend and Static Assets

| File | Ownership |
| --- | --- |
| `static/index.html` | Page structure and UI shell |
| `static/client.js` | Runtime UI logic, state sync, rendering, exports |
| `static/style.css` | Styling and responsive layout |

### Shared Config and Utilities

| File | Ownership |
| --- | --- |
| `app/config.py` | Environment settings, runtime config schema, validation |
| `app/utils/audio_devices.py` | Windows capture-device enumeration |

---

## 8. Configuration Model

Configuration is split across three ownership domains.

### Environment Configuration

Stored in `.env` and loaded via `Settings`.

Owns:
- Azure AI Services key and region
- Azure AI Foundry project endpoint
- coach and summary agent bindings
- Nova-3 API key
- shadow translation toggles and model name

### Runtime Configuration

Stored in memory as `RuntimeConfig`, persisted to `web_translator_settings.json`.

Owns:
- speech provider selection
- capture mode
- device IDs and speaker labels
- translation toggle and interval
- coach toggle and tuning
- summary toggle and timing mode
- topic definitions
- debug mode
- session limits

### External Azure Configuration

Owned outside the app:
- Azure AI Foundry agent system instructions
- Azure-side model selection for coach and summary agents
- Azure credentials and tenant access

Guiding rule:
- infrastructure and secrets live in `.env`
- operational runtime behavior lives in `RuntimeConfig`
- long-lived AI persona and hosted agent settings live in Azure

---

## 9. Agent Catalog

| Product Name | Env Binding | Purpose |
| --- | --- | --- |
| Conversation Coach | `GUIDANCE_AGENT_NAME` | Real-time coaching suggestions for the local speaker |
| Meeting Summarizer | `SUMMARY_AGENT_NAME` | Structured post-session summary generation |

Agent names are expected to match the Azure AI Foundry display names configured for the project.

---

## 10. Instruction Ownership Model

Agent behavior is shaped by multiple layers.

| Priority | Layer | Source | Scope |
| --- | --- | --- | --- |
| 1 | Request context data | Transcript turns, speaker labels, agenda, runtime state | Per request |
| 2 | Runtime meeting brief | `coach_instruction` from UI runtime config | Per meeting, coach only |
| 3 | Code-authored framing | `coach_orchestrator.py`, `summary.py`, `topic_summary.py` | Per request |
| 4 | Azure baseline instruction | Azure AI Foundry agent instructions | Persistent persona and behavior |

Summary generation additionally constrains output through:
- prompt schema
- valid utterance ID ranges
- deterministic backend post-processing

---

## 11. Runtime Flows

### 11.1 Startup and Lifespan

At FastAPI startup:
1. environment is loaded
2. `Settings` is validated
3. `AppController` is constructed
4. event loop references are wired into broadcast/session/translation components
5. translation worker starts
6. shadow translation worker starts
7. watchdog task starts
8. runtime config is reloaded from disk if the config file exists

At shutdown:
1. translation workers stop
2. watchdog task is cancelled
3. coach and summary clients are closed

### 11.2 Recognition Flow

1. user triggers `POST /api/start`
2. `SessionManager.start()` validates critical prerequisites
3. `SpeechProviderService` starts the selected backend
4. the backend emits normalized events:
   - `status`
   - `partial`
   - `partial_clear`
   - `final`
   - `log`
5. `SessionManager.handle_speech_event()` routes those events into transcript, coach, and summary-related state

### 11.3 Transcript and Translation Flow

1. speech backend emits a `partial` event
2. `SessionManager` applies speaker-activity and bleed-suppression checks
3. translation pipeline state is updated for the current speaker, segment, and revision
4. live partial state is broadcast immediately
5. if translation is enabled and partial throttle permits, a translation request is enqueued
6. translation worker processes requests
7. `TranscriptStore.apply_translation_result()` applies partial or final Arabic patch if still current
8. telemetry is updated and broadcast

### 11.4 Shadow Translation Flow

1. a committed final is appended to transcript state
2. if shadow translation is configured and translation is enabled, a shadow request is created
3. `ShadowFinalTranslationPipeline` processes committed-final requests only
4. result is applied back to the same transcript row if generation and segment identity still match
5. WebSocket emits `final_shadow_patch`

### 11.5 Coach Flow

1. a committed final is evaluated by `CoachOrchestrator`
2. trigger eligibility is checked against:
   - coach enabled
   - coach configured
   - trigger speaker policy
   - cooldown
   - pending state
3. prompt is built from transcript delta since the last successful automatic coach send
4. `CoachService.ask()` runs on a worker thread using `asyncio.to_thread`
5. result is normalized into a `coach` WebSocket event
6. if another trigger arrived while pending, only the latest queued trigger is resumed

### 11.6 Topic Definitions Flow

1. topic definitions are edited in the Settings UI
2. definitions are submitted through `PUT /api/config` or helper topic endpoints
3. `TopicOrchestrator` normalizes, deduplicates, orders, and stores definitions
4. `topics_update` is broadcast to the frontend
5. summary generation later uses those definitions as agenda context and planned-minute inputs

### 11.7 Summary Flow

1. summary runs either:
   - automatically on stop when enabled
   - manually via `POST /api/summary/generate`
2. `SummaryOrchestrator` gathers the latest transcript window from committed finals
3. entries are sorted by `start_ts`
4. transcript rows are normalized and assigned deterministic `utterance_id` values
5. expected agenda context is prepended if topic definitions exist
6. `SummaryService.generate()` requests structured output from Azure AI Foundry
7. deterministic post-processing repairs and enriches the result:
   - enforce topic coverage
   - resolve topic durations from `utterance_ids`
   - compute topic breakdown
   - compute agenda adherence
   - compute meeting insights
   - compute keyword index
8. summary result is stored in orchestrator state and broadcast as `summary`

### 11.8 From-File Analysis Flow

1. user uploads an exported transcript CSV to `POST /api/summary/from-transcript`
2. backend validates file size and UTF-8 encoding
3. CSV is parsed into normalized transcript rows
4. transcript prompt is rendered using the same summary helpers used for live sessions
5. summary generation and deterministic post-processing run
6. result is returned in the HTTP response; live runtime transcript state is not mutated

### 11.9 Stop and Finalization Flow

Stop may happen by:
- explicit `POST /api/stop`
- watchdog inactivity auto-stop
- watchdog max-session auto-stop

Finalization path:
1. speech backend stop is requested
2. if using `stop_async()`, summary is attempted before cleanup
3. session runtime modules are reset:
   - translation runtime state
   - shadow translation generation
   - coach runtime pending state
4. transcript finals are retained unless the user explicitly clears transcript

### 11.10 WebSocket Snapshot and Reconnect Flow

1. client connects to `/ws`
2. loopback auth is validated
3. connection is accepted and registered
4. controller sends full `snapshot`
5. client receives incremental events afterward
6. on reconnect, frontend rehydrates from a fresh snapshot instead of requiring polling

---

## 12. Concurrency Model

The backend spans multiple execution contexts.

| Context | What runs there | Communication |
| --- | --- | --- |
| Speech SDK threads | Azure Speech callbacks | `run_coroutine_threadsafe` into event loop |
| Nova-3 listener/pump threads | WASAPI capture, Deepgram socket handling | `run_coroutine_threadsafe` into event loop |
| Asyncio event loop | FastAPI routes, WebSocket sends, worker orchestration | direct `await` |
| Thread pool | Blocking coach and summary calls | `asyncio.to_thread` |

Rules:
- speech backends may emit from non-event-loop threads
- WebSocket fanout is event-loop-owned
- long-running blocking AI client calls must not run directly on the event loop

---

## 13. Locking Model

### Shared Runtime Lock

The following modules share one `threading.RLock` created by `AppController`:
- `SessionManager`
- `TranscriptStore`
- `CoachOrchestrator`
- `TopicOrchestrator`
- `SummaryOrchestrator`

Purpose:
- keep cross-module state transitions atomic
- prevent race conditions during speech-event handling

### Independent Locks

Independent lock domains:
- `ConfigStore` has its own lock
- `TranslationPipeline` has its own sequencing lock
- `ShadowFinalTranslationPipeline` has its own sequencing lock
- `BroadcastService` is effectively event-loop-owned instead of sharing the runtime lock

### `_unlocked` Convention

Methods suffixed with `_unlocked` require the caller to already hold the relevant lock.

This naming is part of the code contract:
- it makes lock expectations explicit
- it avoids hidden nested locking
- it documents which methods are safe only inside a protected state transition

---

## 14. Core Data Contracts

### 14.1 Inbound Speech Events to `SessionManager`

Primary event families:

| Type | Required Core Fields | Notes |
| --- | --- | --- |
| `status` | `type`, `status`, `running` | backend status transitions |
| `partial` | `type`, `speaker`, `speaker_label`, `en` | live speech hypothesis |
| `partial_clear` | `type`, `speaker`, `reason` | clears stale live hypothesis |
| `final` | `type`, `speaker`, `speaker_label`, `en`, `ts` | committed utterance |
| `log` | `type`, `level`, `message` | backend log line |

Azure and Nova-3 finals may also include:
- `start_ts`
- `end_ts`
- `duration_sec`
- `offset_sec`
- `timing_source`
- `recognizer_session_id`
- `recognizer_anchor_ts`

### 14.2 Transcript Final Item Shape

Committed transcript rows stored in `TranscriptStore.finals` contain:
- `en`
- `ar`
- `speaker`
- `speaker_label`
- `segment_id`
- `revision`
- `ts`
- `start_ts`
- `end_ts`
- `duration_sec`
- `offset_sec`
- `timing_source`
- `recognizer_session_id`
- `recognizer_anchor_ts`
- `shadow_translation`

### 14.3 Live Partial Item Shape

Live partial state includes:
- `type`
- `speaker`
- `speaker_label`
- `segment_id`
- `revision`
- `ar_revision`
- `en`
- `ar`
- `ts`

`ar_revision` is an internal Arabic revision counter used to reject stale partial-translation patches.

### 14.4 Translation Request Identity Fields

Translation requests use:
- `kind`
- `speaker`
- `segment_id`
- `revision`
- `generation`
- `text`
- `trigger_ts`
- `debug`

These fields are used to reject stale or mismatched async results.

### 14.5 Coach Hint Shape

Coach hint events include:
- `type: coach`
- `group_id`
- `ts`
- `speaker`
- `speaker_label`
- `trigger_en`
- `trigger_segment_id`
- `trigger_revision`
- `trigger_ts`
- `suggestion`

Manual hints use `speaker=manual` and may omit transcript trigger identity fields.

### 14.6 Summary Payload Shape

Summary events and snapshots expose:
- `executive_summary`
- `key_points`
- `action_items`
- `topic_key_points`
- `keywords`
- `entities`
- `decisions_made`
- `risks_and_blockers`
- `key_terms_defined`
- `metadata`
- `generated_ts`
- `total_ms`
- `topic_breakdown`
- `agenda_adherence_pct`
- `meeting_insights`
- `keyword_index`
- `error` when generation fails

---

## 15. REST API Contracts

All REST endpoints are loopback-authenticated.

### 15.1 State and Config

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/state` | full application snapshot |
| `GET` | `/api/config` | current runtime config |
| `PUT` | `/api/config` | update runtime config in memory |
| `POST` | `/api/config/save` | persist runtime config to disk |
| `POST` | `/api/config/reload` | reload runtime config from disk |
| `POST` | `/api/config/reset-defaults` | restore default runtime config |
| `GET` | `/api/audio/devices` | list capture devices |

Config update constraints:
- `PUT /api/config` is rejected with `409` while a session is running
- reload and reset-defaults are also blocked while running

### 15.2 Session and Clearing Actions

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/start` | begin speech recognition |
| `POST` | `/api/stop` | stop session and schedule auto-summary if applicable |
| `POST` | `/api/logs/clear` | clear log buffer |
| `POST` | `/api/transcript/clear` | clear transcript state |
| `POST` | `/api/coach/clear` | clear coach history |

### 15.3 Coach

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/coach/ask` | manual coach prompt |

`CoachAskRequest`:
- `prompt`: string, max length 2000
- `speaker_label`: optional label, default `"Manual"`

Rate limit:
- 6 requests per 60 seconds per client IP

### 15.4 Topics

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/topics/configure` | configure topic definitions |
| `POST` | `/api/topics/clear` | clear topic definitions |

Definitions payload fields:
- `id`
- `name`
- `expected_duration_min`
- `priority`
- `comments`
- `order`

### 15.5 Summary

| Method | Route | Purpose |
| --- | --- | --- |
| `POST` | `/api/summary/generate` | manual summary generation |
| `POST` | `/api/summary/clear` | clear stored summary state |
| `GET` | `/api/summary` | fetch current summary snapshot |
| `POST` | `/api/summary/from-transcript` | generate summary from uploaded transcript CSV |

Summary generation constraints:
- `summary_enabled` must be true for manual generation
- summary service must be configured
- `summary_pending` blocks duplicate generation

From-file constraints:
- file size max 5 MB
- UTF-8 only
- shared summary rate-limit pool

---

## 16. WebSocket Event Catalog

| Event | When Sent | Payload Use |
| --- | --- | --- |
| `snapshot` | on initial connection | full application state |
| `status` | on runtime state changes | running flag and status text |
| `partial` | during live speech or Arabic patch to partial | live row update |
| `partial_clear` | when a live hypothesis is abandoned or cancelled | remove stale live text |
| `final` | when a committed utterance is stored | append transcript row |
| `final_patch` | when Arabic translation for a committed final completes | patch final row Arabic |
| `final_shadow_patch` | when optional shadow translation completes | patch final row shadow state / Arabic |
| `telemetry` | after translation metrics update | latency, counts, estimated cost |
| `coach` | when coach returns a hint | show coaching guidance |
| `topics_update` | when topic definitions change | refresh topic definitions UI |
| `summary` | when summary result is generated or summary generation fails | render summary state |
| `summary_cleared` | when summary state is reset | clear summary tab |
| `log` | whenever a log line is appended | runtime diagnostics |

Snapshot includes:
- runtime status
- config
- live partials
- finals
- logs
- recording state
- coach state
- topics state
- summary state
- translation telemetry

---

## 17. Guardrails and Limits

### Translation

- partial translation is throttled per speaker
- final translation has higher queue priority than partial translation
- partial backlog collapses to the latest pending partial for a speaker
- translation queue is bounded to 200 items
- shadow translation queue is bounded to 120 items
- translation work is skipped entirely when `translation_enabled=false`

### Coach

- automatic coach triggering obeys speaker policy and cooldown
- only the latest queued trigger is retained while busy
- manual prompt length is capped at 2000 characters
- coach history is capped to the latest 120 hints

### Summary

- summary prompt window uses the latest 500 normalized transcript rows
- summary generation is blocked while another summary is in progress
- `/api/summary/generate` and `/api/summary/from-transcript` share the same 2/min rate-limit pool
- uploaded transcript file size is capped at 5 MB

### Topic Definitions

- topic definitions are normalized and capped to 80 entries
- agenda list derived from definitions is capped to 20 unique names

### State Buffers

- transcript finals are capped by `max_finals` in runtime config
- translation latency window keeps the latest 240 samples
- logs are capped to the latest 1000 items

---

## 18. Security Model

The application is intentionally local-only.

HTTP and WebSocket authorization rules:
- `localhost`
- IPv4 loopback
- IPv6 loopback
- `testclient` in automated tests

No browser-exposed bearer-token mode exists.

Security posture:
- API is not intended for remote access
- browser and backend are assumed to run on the same host
- reduced auth complexity is traded for explicit loopback-only restrictions

---

## 19. Observability and Telemetry

### Logs

The backend maintains an in-memory log buffer exposed through WebSocket snapshot and incremental `log` events.

Log sources include:
- speech backend startup and cancellation
- provider fallback
- watchdog auto-stop
- coach send/reply traces
- summary generation lifecycle
- translation queue and failure warnings
- debug UI emission traces when debug mode is enabled

### Translation Telemetry

Telemetry broadcasts include:
- `translation_latest_ms`
- `translation_p50_ms`
- `translation_samples`
- `translation_chars`
- `estimated_cost_usd` when cost rate is configured
- current WebSocket connection count
- current recognition status and running state

### Frontend Rehydration

On reconnect:
- backend sends a fresh `snapshot`
- frontend rebuilds transcript, coach, topics, summary, logs, and UI state from that snapshot

---

## 20. Invariants

The following invariants should remain true:

- shared runtime state transitions across transcript/session/coach/summary/topic controllers occur under the shared `RLock`
- `BroadcastService` connection mutations occur on the event loop, not under the shared runtime lock
- each live partial stream is identified by `speaker + segment_id + revision`
- a translation result is applied only if it still matches the expected segment/revision/generation state
- committed finals are appended before downstream coach and summary logic reasons about them
- only one summary generation can be pending at a time
- coach automatic queue depth is effectively one
- topic timing in summary output is computed from transcript data, not trusted from model-generated durations
- runtime config reads return validated copies rather than mutable shared references
- transcript clear does not delete topic definitions

---

## 21. Failure Handling

| Failure Class | Behavior |
| --- | --- |
| Missing Azure AI Services key/region | app startup fails during environment validation |
| Coach enabled but not configured | session start is blocked |
| Coach client lacks `conversations.create()` support | session start is blocked |
| Nova-3 unavailable or dependencies missing | provider router falls back to Azure Speech |
| Azure speech cancellation with `client buffer exceeded` | affected Azure channel is restarted |
| Non-recoverable speech backend error | status/log error emitted; session stops |
| Translation request failure | warning logged; English transcript continues |
| Stale translation result | dropped by identity guards |
| Shadow translation failure | warning logged; existing Arabic remains |
| Summary generation failure | error logged and `summary` error payload broadcast |
| Auto-summary timeout | warning logged; cleanup continues |
| WebSocket send failure | dead connection is dropped from connection set |
| Missing config file on reload | `404` on reload endpoint; defaults remain until saved |

---

## 22. Validation Matrix

Recommended validation scenarios:

- single-input Azure speech path with partials, finals, and Arabic patching
- dual-input Azure path with local/remote device routing
- Nova-3 preview start success and Azure fallback path
- bleed suppression under overlapping remote/local audio
- per-channel Azure restart after idle-buffer overflow
- transcript clear while translation requests are inflight
- stop/reset while shadow translation is inflight
- coach enabled/disabled behavior
- coach cooldown behavior
- queued-latest coach trigger behavior
- summary auto-on-stop
- manual summary generation
- from-file summary generation from exported CSV
- topic definitions add/edit/delete and adherence calculations
- loopback-only HTTP and WebSocket auth
- WebSocket reconnect and snapshot rehydration
- translation telemetry updates and estimated cost reporting

---

## 23. Key Source Locations

| Component | File |
| --- | --- |
| Application entry point | `app/main.py` |
| Controller wiring layer | `app/controller/__init__.py` |
| Session lifecycle | `app/controller/session_manager.py` |
| Transcript store | `app/controller/transcript_store.py` |
| Coach orchestration | `app/controller/coach_orchestrator.py` |
| Topic definitions orchestration | `app/controller/topic_orchestrator.py` |
| Summary orchestration | `app/controller/summary_orchestrator.py` |
| Runtime config store | `app/controller/config_store.py` |
| WebSocket fanout and logs | `app/controller/broadcast_service.py` |
| Speech provider router | `app/services/speech_provider.py` |
| Azure speech backend | `app/services/speech.py` |
| Nova-3 preview backend | `app/services/speech_nova3.py` |
| Translation worker | `app/services/translation_pipeline.py` |
| Shadow translation worker | `app/services/shadow_translation_pipeline.py` |
| Coach client | `app/services/coach.py` |
| Summary client | `app/services/summary.py` |
| Topic summary helpers | `app/services/topic_summary.py` |
| Meeting insights helpers | `app/services/meeting_insights.py` |
| API routes | `app/api/routes.py` |
| API auth | `app/api/auth.py` |
| Config schema | `app/config.py` |
| Frontend shell | `static/index.html` |
| Frontend runtime logic | `static/client.js` |
| Frontend styles | `static/style.css` |

---

## 24. Suggested Review Order

For a new maintainer:

1. `app/controller/__init__.py`
2. `app/main.py`
3. `app/controller/session_manager.py`
4. `app/controller/transcript_store.py`
5. `app/controller/coach_orchestrator.py`
6. `app/controller/summary_orchestrator.py`
7. `app/services/translation_pipeline.py`
8. `app/services/speech.py`
9. `app/services/speech_nova3.py`
10. `app/services/topic_summary.py`
11. `app/api/routes.py`
12. `static/client.js`

Use `ENGINEERING_RATIONALE.md` after this document if you need the reasoning behind specific patterns or tradeoffs.
