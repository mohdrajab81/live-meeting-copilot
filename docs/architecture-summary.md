# Architecture Summary

## Purpose
Live interview translator that captures speech, transcribes EN, translates to AR, and optionally provides coach suggestions.

## High-level components
- `app/services/speech.py`: Azure Speech STT (single/dual input).
- `app/services/translation_pipeline.py`: async translation queue, throttling, segment/revision guards.
- `app/main.py` (`AppController`): orchestration, state, watchdog, coach trigger logic.
- `app/services/coach.py`: Azure AI Foundry coach integration.
- `app/api/routes.py`: REST control/config endpoints.
- `app/api/websocket.py`: realtime event stream endpoint.
- `static/client.js`: frontend state/rendering and operator controls.

## Runtime flow
1. User clicks `Start`.
2. `SpeechService` emits `partial` and `final` events.
3. `AppController`:
   - sends EN partials immediately,
   - enqueues throttled partial translation,
   - enqueues always-on final translation.
4. `TranslationPipeline` worker translates EN->AR and applies:
   - `partial` updates for live panel,
   - `final_patch` updates for timeline rows.
5. WebSocket broadcasts `status`, `partial`, `final`, `final_patch`, `log`, `coach`.
6. Optional coach triggers on final turns based on config.

## Event contracts (core)
- `partial`: `{speaker, speaker_label, segment_id, revision, en, ar, ts}`
- `final`: `{speaker, speaker_label, segment_id, revision, en, ar, ts}`
- `final_patch`: patches AR for an existing final by `segment_id + revision`

## Guardrails and cost controls
- `partial_translate_min_interval_sec`: limits partial translation frequency per speaker.
- Priority queue in translator: final requests before partial requests.
- Backlog collapse for partials: only latest partial per speaker survives while inflight.
- Generation guard: stale translation requests dropped after stop/reset.
- `auto_stop_silence_sec`: auto-stop on inactivity.
- `max_session_sec`: hard session timeout.

## Concurrency model
- Speech callbacks run on background thread.
- Shared state protected by `threading.RLock`.
- Cross-thread async dispatch uses `asyncio.run_coroutine_threadsafe`.
- Translation worker runs on FastAPI event loop task.

## Coach behavior
- Triggered on final events (`remote/local/default/any`) with cooldown.
- Uses transcript delta since last sent index.
- Limited by `coach_max_turns`.
- If busy, latest trigger is queued and resumed after completion.

## Key files to review first
- `app/main.py`
- `app/services/translation_pipeline.py`
- `app/services/speech.py`
- `docs/low-level-design.md`
