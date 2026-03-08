# Architecture Summary

## Purpose
Live meeting copilot that:
- captures speech (single or dual input),
- emits live EN transcript,
- optionally translates EN->AR asynchronously,
- optionally generates session summary (executive summary, key points, action items, decisions, risks, key terms, metadata),
- optionally extracts structured entities in summary output (PERSON/ORG/LOCATION/DATE_TIME/PRODUCT/EVENT/MONEY/PERCENT),
- computes deterministic meeting insights and keyword index from transcript turns for both live and from-file summary paths,
- builds topic coverage timeline from agenda definitions + one-shot transcript topic grouping with deterministic duration allocation from utterance IDs,
- computes agenda adherence when planned minutes exist in definitions,
- optionally provides coach hints.

## High-level modules

### Entry and API
- `app/main.py`: FastAPI bootstrap, lifespan startup/shutdown, routing.
- `app/api/routes.py`: authenticated REST control plane.
- `app/api/websocket.py`: authenticated websocket endpoint.
- `app/api/auth.py`: loopback-only authorization policy for HTTP and WebSocket access.

### Controller layer (state and orchestration)
- `app/controller/__init__.py` (`AppController`): dependency wiring only.
- `app/controller/session_manager.py`: speech event handling, start/stop lifecycle, watchdog.
- `app/controller/transcript_store.py`: transcript state + translation telemetry.
- `app/controller/coach_orchestrator.py`: coach trigger scheduling and async execution.
- `app/controller/topic_orchestrator.py`: topic definitions config/state used by summary context.
- `app/controller/summary_orchestrator.py`: summary generation state and execution.
- `app/controller/config_store.py`: runtime config get/set/save/reload/reset.
- `app/controller/broadcast_service.py`: websocket fanout, log buffer, debug trace broadcasting.

### Service layer
- `app/services/speech_provider.py`: provider router for Azure Speech and Nova-3 preview.
- `app/services/speech.py`: Azure Speech recognizers and event emission.
- `app/services/speech_nova3.py`: Nova-3 preview live STT backend.
- `app/services/translation_pipeline.py`: async translation queue with priority and stale guards.
- `app/services/shadow_translation_pipeline.py`: optional shadow translation worker for final utterances; disabled by default (`SHADOW_FINAL_TRANSLATION_ENABLED`).
- `app/services/coach.py`: Azure AI Foundry coach agent client.
- `app/services/summary.py`: Azure AI Foundry summary agent client.
- `app/services/meeting_insights.py`: deterministic meeting insights and keyword index builders.
- `app/services/topic_summary.py`: deterministic topic duration/breakdown helpers for summary flows.

## Runtime flows

### Transcript + translation flow
1. `POST /api/start` starts recognition.
2. `SpeechProviderService` starts the selected backend and emits normalized `partial`, `final`, and `partial_clear` events.
3. `SessionManager` updates transcript state and schedules translation work only when `translation_enabled=true`.
4. `TranslationPipeline` processes queue (`final` priority over `partial`) when translation is enabled.
5. If shadow final translation is enabled, committed finals are also sent to `ShadowFinalTranslationPipeline` for a second-pass Arabic patch.
6. `TranscriptStore` applies translation results and broadcasts:
   - `partial` updates,
   - `partial_clear` updates,
   - `final_patch` updates,
   - `final_shadow_patch` updates,
   - `telemetry` updates.

### Coach flow
1. Final transcript events are evaluated by `CoachOrchestrator`.
2. If trigger/cooldown conditions pass, prompt is built from transcript delta.
3. `CoachService` sends request in a persistent conversation session.
4. Coach hints are broadcast as `coach` events.
5. If busy, latest trigger is queued and resumed after current run.

### Topics flow
1. Topics are edited in **Settings → Topics** and staged as part of the runtime settings form.
2. `PUT /api/config` carries `topic_definitions` into runtime config and persistence.
3. `TopicOrchestrator` stores normalized definitions and derived agenda names only.
4. Updates broadcast as `topics_update`.

### Summary flow
1. Session stop (`stop_async`) triggers summary generation when `summary_enabled=true`.
2. `SummaryOrchestrator` builds transcript text from final turns.
3. If agenda definitions exist, orchestrator prepends expected agenda context to the prompt.
4. `SummaryService` generates structured summary via Azure AI Foundry, including `topic_key_points` with `utterance_ids`.
5. Orchestrator resolves `topic_key_points[*].estimated_duration_minutes` deterministically from transcript utterance durations, then computes `topic_breakdown` and `agenda_adherence_pct` from agenda definitions + resolved topic groups.
6. Orchestrator computes deterministic `meeting_insights` and `keyword_index` from the same 500-turn transcript window used for prompting, where `keyword_index` merges GPT keywords, key terms, and entities.
7. Summary is broadcast as `summary` event; clear action broadcasts `summary_cleared`.
8. Separate file-analysis path: `/api/summary/from-transcript` uses the same prompt + deterministic post-processing path and returns the same summary + insights + keyword payload shape; frontend applies it to the main Summary tab view.

## WebSocket event families
- `snapshot` (initial full state)
- `status`
- `partial`
- `partial_clear`
- `final`
- `final_patch`
- `final_shadow_patch` (shadow translation result for a committed utterance; sent only when shadow translation is enabled)
- `telemetry`
- `coach`
- `topics_update`
- `summary`
- `summary_cleared`
- `log`

## Guardrails
- Translation:
  - runtime toggle (`translation_enabled`) to disable translation enqueueing,
  - per-speaker partial throttling,
  - queue priority (`final` before `partial`),
  - partial backlog collapse,
  - generation guard to drop stale work after reset/stop.
- Coach:
  - trigger policy + cooldown,
  - queue-latest while busy.
  - API rate limit on manual ask endpoint.
- Summary:
  - API rate limit on generate/from-file endpoints.
  - deterministic post-processing for durations, topic breakdown, and adherence.

## Concurrency model
- Azure Speech callbacks and Nova listener threads run on background threads.
- Controller modules sharing mutable runtime state use one shared `threading.RLock`.
- `BroadcastService` connection set is event-loop-owned.
- Translation worker is an asyncio task on the app loop.
- Cross-thread dispatch uses `asyncio.run_coroutine_threadsafe`.

## Key review order
1. `app/controller/__init__.py`
2. `app/controller/session_manager.py`
3. `app/controller/topic_orchestrator.py`
4. `app/controller/summary_orchestrator.py`
5. `app/controller/broadcast_service.py`
6. `app/services/translation_pipeline.py`
7. `docs/low-level-design.md`
