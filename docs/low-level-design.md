# Live Interview Translator - Low-Level Design

## 1. Scope and goals
This service captures live speech from one or two audio inputs, performs EN speech recognition, translates EN text to AR, streams updates to a browser UI, and optionally asks an AI coach for reply suggestions.

Primary goals:
- Low-latency transcript updates.
- Controlled translation cost (partial throttling + auto-stop watchdog).
- Deterministic final transcript correctness.
- Safe threading model between speech SDK thread and FastAPI event loop.

## 2. Runtime components

### 2.1 `app/main.py` (`AppController`)
Responsibilities:
- Own global runtime state (`status`, `running`, transcript, logs, coach state).
- Consume speech events (`partial`, `final`, `status`, `log`).
- Coordinate translation requests through `TranslationPipeline`.
- Coordinate coach prompts and queueing.
- Broadcast all updates via WebSocket.
- Enforce session watchdog (`auto_stop_silence_sec`, `max_session_sec`).

Threading model:
- Speech SDK callbacks happen on background thread.
- Shared state is protected by `threading.RLock`.
- Cross-thread async communication uses `asyncio.run_coroutine_threadsafe`.

### 2.2 `app/services/speech.py` (`SpeechService`)
Responsibilities:
- Build Azure Speech recognizers (single or dual capture mode).
- Emit normalized events:
  - partial: `{type='partial', speaker, speaker_label, en}`
  - final: `{type='final', speaker, speaker_label, en, ts}`
  - status/log events.
- Start/stop recognizers and worker thread.

### 2.3 `app/services/translation_pipeline.py` (`TranslationPipeline`)
Responsibilities:
- Maintain segment/revision state per speaker.
- Emit partial translation requests with throttling.
- Always emit final translation requests.
- Serialize translation calls through one bounded priority queue:
  - priority 0 = final
  - priority 1 = partial
- Drop/replace stale partial backlog per speaker.
- Reject stale requests using generation guard after stop/reset.

### 2.4 `app/services/coach.py` (`CoachService`)
Responsibilities:
- Manage Azure AI Projects OpenAI client.
- Ensure/reuse one conversation session.
- Send responses request and auto-approve MCP tool approvals.
- Return latency metrics and response identifiers.

### 2.5 API and frontend
- `app/api/routes.py`: control plane (`/start`, `/stop`, `/config`, `/coach`, etc.).
- `app/api/websocket.py`: state snapshot + incremental events.
- `static/client.js`: UI state reducer, rendering, filters, exports, controls.

## 3. Data contracts

### 3.1 Speech event contracts
- Partial input from `SpeechService` to `AppController`:
  - required: `type='partial'`, `speaker`, `speaker_label`, `en`
- Final input:
  - required: `type='final'`, `speaker`, `speaker_label`, `en`, `ts`

### 3.2 WebSocket outbound contracts
- `snapshot`: full current state.
- `status`: runtime state + recording timers.
- `partial`: segment-scoped live EN/AR (`segment_id`, `revision`).
- `final`: append-only EN transcript entry (AR may be empty initially).
- `final_patch`: patch AR for an existing final item (same `segment_id` + `revision`).
- `log`: user-visible log line.
- `coach`: coach suggestion card.

## 4. Segment and revision model
For each speaker:
- Start partial segment with unique `segment_id`.
- Every new partial increments `revision`.
- Final closes segment and uses next revision.

Correctness rule:
- A translation response is accepted only if its `(speaker, segment_id, revision)` matches current expected state (for partial) or existing final item (for final).
- Late/out-of-order partial responses are ignored.

## 5. Translation flow
1. `on_recognizing` -> emit partial EN immediately.
2. If per-speaker throttle window passed -> queue partial translation request.
3. `on_recognized` -> append final EN and queue final translation request (always).
4. Translation worker executes request, applies result:
   - partial -> updates live AR for same segment+revision.
   - final -> sends `final_patch` to replace/fill AR for exact final row.

Cost controls:
- `partial_translate_min_interval_sec` throttles partial AR calls.
- Auto-stop watchdog avoids idle paid sessions.
- Generation guard prevents post-stop stale queue processing.

## 6. Coach flow
1. Final event arrives.
2. If trigger policy allows and cooldown passed:
   - Build prompt from transcript delta (`coach_last_sent_final_idx..end`).
   - Trim to last `coach_max_turns` turns.
   - Send to coach in same session conversation.
3. If coach busy, keep latest trigger in queue and resume after current run.

## 7. Invariants
- Shared mutable runtime state is accessed under `RLock`.
- Only one active translation worker task.
- `finals` length never exceeds `max_finals`.
- Coach hint history capped to 120.
- Logs capped to 1000.

## 8. Failure handling
- Translator HTTP/network errors return empty translation; app remains live.
- Speech cancellation emits error log and stops recognition loop.
- Coach errors are logged and do not stop speech pipeline.
- Missing settings file on startup falls back to defaults.

## 9. Audit findings and fixes applied
Applied in this revision:
- Added generation guard in `TranslationPipeline` to prevent stale queued requests after stop/reset.
- Applied `coach_max_turns` in coach prompt build path (previously configured but unused).
- Prevented empty final translation result from wiping existing AR text.
- Added explicit start guard when coach is enabled but environment is not configured.

## 10. Remaining technical debt (non-blocking)
- `AppController` is still large and can be split further:
  - session state model
  - coach orchestration
  - websocket broadcast manager
- No automated test suite yet (unit/integration).
- No linter configured in environment (`ruff`/`pytest` not installed).

## 11. Suggested test matrix
- Single mode: partial/final stream and AR patch flow.
- Dual mode: independent segment/revision for local+remote.
- Stop during heavy partial traffic: verify no stale AR updates after stop.
- Translator failure: final AR remains last known good value.
- Coach enabled/disabled and misconfigured startup guard.
- Watchdog silence and max session auto-stop behavior.
