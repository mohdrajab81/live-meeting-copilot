# Live Interview Translator - Low-Level Design

## 1. Scope and goals
The system captures live speech, produces EN transcript, optionally translates EN->AR, broadcasts updates to the UI, and can invoke two optional agent features:
- interview coach hints,
- meeting topic tracking.

Primary goals:
- low-latency transcript/translation updates,
- deterministic transcript correctness under concurrency,
- bounded costs and predictable runtime behavior,
- clear separation of responsibilities across controller modules.

## 2. Runtime decomposition

### 2.1 Entry, API, and auth
- `app/main.py`: creates FastAPI app, wires lifespan, starts translation worker, starts watchdog.
- `app/api/routes.py`: authenticated REST endpoints for config, session, coach, topics.
- `app/api/websocket.py`: authenticated websocket endpoint; sends snapshot on connect.
- `app/api/auth.py`: loopback-only fallback or token-based auth (`API_AUTH_TOKEN`).

### 2.2 Controller layer
- `app/controller/__init__.py` (`AppController`): wiring and facade only.
- `app/controller/session_manager.py`:
  - handles incoming speech events,
  - controls session start/stop,
  - runs watchdog for auto-stop and scheduled topic analysis.
- `app/controller/transcript_store.py`:
  - owns transcript/live partial state,
  - applies translation results,
  - tracks translation telemetry/cost estimate.
- `app/controller/coach_orchestrator.py`:
  - decides when to trigger coach,
  - builds prompts from transcript deltas,
  - manages queued trigger while busy.
- `app/controller/topic_orchestrator.py`:
  - stores topic config and runtime state,
  - prepares topic agent input,
  - normalizes and merges agent responses,
  - allocates chunk time and maintains topic runs.
- `app/controller/config_store.py`: runtime config persistence and validation.
- `app/controller/broadcast_service.py`: websocket fanout and log buffering.

### 2.3 Service layer
- `app/services/speech.py`: Azure Speech recognizer(s), emits normalized speech/status events.
- `app/services/translation_pipeline.py`: async queue worker with priority and stale guards.
- `app/services/coach.py`: Azure AI Foundry coach client with conversation continuity.
- `app/services/topic_tracker.py`: Azure AI Foundry topic tracker client with retry + JSON extraction.

## 3. Concurrency and lock model

### 3.1 Shared state lock
`SessionManager`, `TranscriptStore`, `CoachOrchestrator`, and `TopicOrchestrator` share one `threading.RLock` from `AppController`.

### 3.2 Independent state
- `BroadcastService` is loop-owned (connection mutations on event loop).
- `ConfigStore` has its own lock to avoid blocking runtime lock on config reads.
- `TranslationPipeline` has its own lock for translation sequencing state.

### 3.3 Cross-thread execution
- Speech callbacks come from SDK thread(s).
- Async actions are dispatched via `asyncio.run_coroutine_threadsafe`.
- Translation worker is one asyncio task.

## 4. Core data contracts

### 4.1 Inbound speech events (to `SessionManager`)
- `partial`: `{type, speaker, speaker_label, en, ...}`
- `final`: `{type, speaker, speaker_label, en, ts, ...}`
- `status` / `log`

### 4.2 WebSocket outbound events
- `snapshot`
- `status`
- `partial`
- `final`
- `final_patch`
- `telemetry`
- `coach`
- `topics_update`
- `log`

### 4.3 Topic API contracts
- `POST /api/topics/configure`: settings + agenda + definitions.
- `POST /api/topics/analyze-now`: manual run.
- `POST /api/topics/clear`: resets topic runtime state.

## 5. Translation design details

### 5.1 Segment/revision model
Per speaker:
- active partial segment has `segment_id` + incremental `revision`,
- final closes active segment and increments revision,
- translation response must match expected segment/revision to be applied.

### 5.2 Queue behavior
- bounded priority queue (`final` before `partial`),
- per-speaker partial backlog collapse while inflight,
- generation guard drops stale queued items after reset/stop.

### 5.3 Telemetry
`TranscriptStore` computes and broadcasts:
- latest translation latency,
- p50 latency,
- sample count,
- translated char count,
- optional estimated cost if `TRANSLATION_COST_PER_MILLION_USD` is set.

### 5.4 Optional translation mode
- `RuntimeConfig.translation_enabled` controls whether translation requests are enqueued.
- When disabled, EN transcript flow continues unchanged while AR translation work is skipped.
- Coach and topics continue to operate from EN transcript data.

## 6. Coach design details
- Triggered on final turns based on `coach_trigger_speaker` and cooldown.
- Prompt built from transcript delta (`coach_last_sent_final_idx -> end`), trimmed by `coach_max_turns`.
- Uses conversation continuity (`conversations.create()`).
- If a trigger arrives while busy, only latest trigger is kept.
- Manual asks (`/api/coach/ask`) run in same conversation session.

## 7. Topics design details

### 7.1 Execution modes
- Manual via `/api/topics/analyze-now`.
- Automatic via watchdog when:
  - app running,
  - topics enabled,
  - tracker configured,
  - interval elapsed,
  - no pending topic run.

### 7.2 Agent payload strategy
`TopicOrchestrator` maintains a rich internal `topic_call` context for merge logic, but sends a reduced payload to the agent (agenda/definitions/current topics/chunk/recent context/reset hint) to reduce prompt noise.

### 7.3 Merge semantics (high-level)
- Normalize and validate incoming topic rows.
- Match names against known agenda/runtime topics.
- Apply confidence thresholding and allow-new rules.
- Merge status/time/statements into persisted topic state.
- Auto-cover stale active topics after inactivity thresholds.
- Broadcast updated topic snapshot.

## 8. Watchdog behavior
Runs once per second:
- auto-stops session on:
  - inactivity (`auto_stop_silence_sec`),
  - max session duration (`max_session_sec`),
- schedules topic auto-analysis when eligible.

## 9. API security and rate limiting
- API and websocket auth:
  - token mode when `API_AUTH_TOKEN` is set,
  - otherwise loopback clients only.
- Rate limits:
  - `/api/coach/ask`: 6/min/client IP,
  - `/api/topics/analyze-now`: 4/min/client IP.

## 10. Invariants
- Shared runtime state changes under shared `RLock`.
- One translation worker task at a time.
- `finals` capped by `max_finals`.
- Coach hints capped to 120 entries.
- Topic runs capped to 160 entries.
- Logs capped to 1000 entries.

## 11. Failure handling
- Translator errors: logged; app continues.
- Coach/topic agent errors: logged and surfaced; app continues.
- Speech failures: recognition loop stops and status/log events emitted.
- Missing config file at startup: defaults kept; reload is optional.

## 12. Suggested validation matrix
- Single-mode partial/final flow with AR patching.
- Dual-mode speaker separation and bleed-suppression behavior.
- Stop/reset during heavy partial load (stale translation guard).
- Coach enabled/disabled, cooldown, queue-latest behavior.
- Topics manual + auto runs, allow-new on/off, context resets.
- Auth modes: loopback-only and token-required.
