# Live Meeting Copilot - Low-Level Design

## 1. Scope and goals
The system captures live speech, produces EN transcript, optionally translates EN->AR, broadcasts updates to the UI, and can invoke optional agent features:
- conversation coach hints,
- session summary generation.

Primary goals:
- low-latency transcript/translation updates,
- deterministic transcript correctness under concurrency,
- bounded costs and predictable runtime behavior,
- clear separation of responsibilities across controller modules.

## 2. Runtime decomposition

### 2.1 Entry, API, and auth
- `app/main.py`: creates FastAPI app, wires lifespan, starts translation worker, starts watchdog.
- `app/api/routes.py`: authenticated REST endpoints for config, session, coach, topics, and summary.
- `app/api/websocket.py`: authenticated websocket endpoint; sends snapshot on connect.
- `app/api/auth.py`: loopback-only HTTP/WebSocket authorization.

### 2.2 Controller layer
- `app/controller/__init__.py` (`AppController`): wiring and facade only.
- `app/controller/session_manager.py`:
  - handles incoming speech events,
  - controls session start/stop,
  - runs watchdog for auto-stop.
- `app/controller/transcript_store.py`:
  - owns transcript/live partial state,
  - applies translation results,
  - tracks translation telemetry/cost estimate.
- `app/controller/coach_orchestrator.py`:
  - decides when to trigger coach,
  - builds prompts from transcript deltas,
  - manages queued trigger while busy.
- `app/controller/topic_orchestrator.py`:
  - stores topic definitions and derived agenda names for summary context.
- `app/controller/summary_orchestrator.py`:
  - builds transcript prompt from final turns,
  - runs summary generation (auto on stop/manual endpoint),
  - resolves summary topic durations deterministically from `utterance_ids`,
  - computes topic breakdown + agenda adherence from topic definitions + resolved summary topic groups,
  - stores summary pending/result/error state.
- `app/controller/config_store.py`: runtime config persistence and validation.
- `app/controller/broadcast_service.py`: websocket fanout and log buffering.

### 2.3 Service layer
- `app/services/speech_provider.py`: speech backend router and provider selection.
- `app/services/speech.py`: Azure Speech recognizer(s), emits normalized speech/status events.
- `app/services/speech_nova3.py`: Nova-3 preview backend; lazy-loads optional runtime dependencies.
- `app/services/translation_pipeline.py`: async queue worker with priority and stale guards.
- `app/services/shadow_translation_pipeline.py`: optional shadow translation worker for committed utterances; disabled by default (`SHADOW_FINAL_TRANSLATION_ENABLED`); uses its own independent lock.
- `app/services/coach.py`: Azure AI Foundry coach client with conversation continuity.
- `app/services/summary.py`: Azure AI Foundry summary client with structured JSON extraction.
- `app/services/meeting_insights.py`: deterministic analytics + keyword index computation.
- `app/services/topic_summary.py`: deterministic summary-topic duration and breakdown helpers.

## 3. Concurrency and lock model

### 3.1 Shared state lock
`SessionManager`, `TranscriptStore`, `CoachOrchestrator`, `TopicOrchestrator`, and `SummaryOrchestrator` share one `threading.RLock` from `AppController`.

### 3.2 Independent state
- `BroadcastService` is loop-owned (connection mutations on event loop).
- `ConfigStore` has its own lock to avoid blocking runtime lock on config reads.
- `TranslationPipeline` has its own lock for translation sequencing state.
- `ShadowFinalTranslationPipeline` has its own lock for shadow translation sequencing state.

### 3.3 Cross-thread execution
- Speech callbacks come from SDK thread(s).
- Async actions are dispatched via `asyncio.run_coroutine_threadsafe`.
- Translation worker is one asyncio task.

## 4. Core data contracts

### 4.1 Inbound speech events (to `SessionManager`)
- `partial`: `{type, speaker, speaker_label, en, ...}`
- `partial_clear`: `{type, speaker, reason, ...}`
- `final`: `{type, speaker, speaker_label, en, ts, ...}`
- `status` / `log`

### 4.2 WebSocket outbound events
- `snapshot`
- `status`
- `partial`
- `partial_clear`
- `final`
- `final_patch`
- `final_shadow_patch` (shadow translation result; sent only when shadow translation is enabled)
- `telemetry`
- `coach`
- `topics_update`
- `summary`
- `summary_cleared`
- `log`

### 4.3 Topic API contracts
- Primary UI path: `PUT /api/config` carries `topic_definitions` as part of runtime settings.
- `POST /api/topics/configure`: still available as a definitions-only helper path.
- `POST /api/topics/clear`: clears topic definitions.

### 4.4 Summary API contracts
- `POST /api/summary/generate`: manual summary trigger.
- `POST /api/summary/from-transcript`: upload exported transcript CSV and return summary result without mutating live session state.
- `POST /api/summary/clear`: clears stored summary state.
- `GET /api/summary`: returns current summary snapshot.

Summary payload includes:
- `executive_summary`, `key_points`, `action_items`,
- `topic_key_points` (topic-grouped key points with `utterance_ids`, backend-computed estimated duration, and origin),
- `decisions_made`, `risks_and_blockers`, `key_terms_defined`, `metadata`,
- `topic_breakdown`, `agenda_adherence_pct`,
- `meeting_insights`, `keyword_index`.

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
- `SHADOW_FINAL_TRANSLATION_ENABLED=true` enables a second worker for committed finals only; live partial translation remains on the normal path.
- Coach and summary continue to operate from EN transcript data.

## 6. Coach design details
- Triggered on final turns based on `coach_trigger_speaker` and cooldown.
- Prompt built from transcript delta (`coach_last_sent_final_idx -> end`), trimmed by `coach_max_turns`.
- Uses conversation continuity via carried `conversation_id` (with `previous_response_id` fallback when needed).
- If a trigger arrives while busy, only latest trigger is kept.
- Manual asks (`/api/coach/ask`) run in same conversation session.

## 7. Topics design details
- Topics are definitions-only in current design.
- Definitions are edited in **Settings → Topics**, persisted through the shared settings flow, and supplied as agenda context to summary generation.
- No automatic/manual topic agent analysis is performed.

## 8. Watchdog behavior
Runs once per second:
- auto-stops session on:
  - inactivity (`auto_stop_silence_sec`),
  - max session duration (`max_session_sec`),
- on stop, `SessionManager.stop_async()` runs summary generation.

## 9. API security and rate limiting
- API and websocket auth:
  - loopback clients only.
- Rate limits:
  - `/api/coach/ask`: 6/min/client IP,
  - `/api/summary/generate`: 2/min/client IP,
  - `/api/summary/from-transcript`: shares the same 2/min pool as `/api/summary/generate`.

## 10. Invariants
- Shared runtime state changes under shared `RLock`.
- One translation worker task at a time.
- `finals` capped by `max_finals`.
- Coach hints capped to 120 entries.
- Logs capped to 1000 entries.

## 11. Failure handling
- Translator errors: logged; app continues.
- Coach and summary agent errors: logged and surfaced; app continues.
- Speech failures: backend-specific status/log events emitted; Nova selection auto-falls back to Azure when Nova cannot start.
- Missing config file at startup: defaults kept; reload is optional.

## 12. Suggested validation matrix
- Single-mode partial/final flow with AR patching.
- Dual-mode speaker separation and bleed-suppression behavior.
- Stop/reset during heavy partial load (stale translation guard).
- Coach enabled/disabled, cooldown, queue-latest behavior.
- Topics definitions add/edit/delete and summary context propagation.
- Summary auto-on-stop, manual `/api/summary/generate`, and `/api/summary/from-transcript`.
- Deterministic topic duration resolution from `utterance_ids` and adherence computation.
- Auth mode: loopback-only.
