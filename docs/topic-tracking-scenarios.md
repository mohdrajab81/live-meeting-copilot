# Topic Tracking — Recording Scenarios & Edge Cases

This document records all known recording scenarios for the topic-tracking subsystem,
the bugs found during analysis, the fixes applied, and the reasoning behind each decision.

---

## How `time_seconds` Works

`time_seconds` on a topic item is the **cumulative wall-clock seconds allocated to that
topic** across all agent runs, not session elapsed time.

Each agent run measures a `chunk_seconds` value and distributes it among the topics that
were active in that chunk. The value accumulates across runs:

```
next_time_seconds = prev_time_seconds + allocated_seconds_for_this_chunk
```

`chunk_seconds` is computed as `last_statement_ts − span_start_ts` where `span_start_ts`
is determined by the rules below.

---

## `span_start_ts` Rules (since_last mode)

| Condition | `span_start_ts` |
|---|---|
| First agent run of this session (any `from_idx`) | `min(first_statement_ts, session_started_ts)` |
| Subsequent runs (`topics_last_run_ts >= session_started_ts`) | `min(first_statement_ts, last_final_ts_of_previous_chunk)` |
| Window mode | `first_statement_ts` (window handles its own range) |

The "first run of this session" is detected by:
```python
topics_last_run_ts < topics_session_started_ts
```
This correctly handles both a brand-new session (`from_idx == 0`) and a **restart
where the transcript was kept** (`from_idx > 0` but previous finals belong to the old
session). Without this guard, a restart would pull `span_start_ts` back into the
previous session's timeline, inflating `chunk_seconds` with the inter-session gap.

---

## All Recording Scenarios

### 1. Fresh start, single session
- `topics_session_started_ts` set on Start
- `topics_last_run_ts = 0 < topics_session_started_ts` → first chunk clamped to session start
- Periodic runs use `prev_ts` boundary as normal
- **Stop**: `stop_async()` → final topic flush → summary run → `finalize_on_stop_unlocked()` → active→covered

### 2. Single-statement first chunk (was broken)
**Bug**: `chunk_seconds = last_ts − first_ts = 0` for a single-statement chunk.
**Fix**: clamp `span_start_ts` to `session_started_ts` for the first run of every
session. A "Good morning." detected 9 s into a session now correctly produces
`chunk_seconds = 9`.

### 3. Stop → Start (restart, transcript kept)
- `topics_session_started_ts` updated to the new session start time
- `topics_last_run_ts` (old session value) `< topics_session_started_ts` (new) → first
  chunk clamped to new session start ✓
- `gap_seconds = first_new_final_ts − last_old_final_ts` is large → `possible_context_reset = True`
  → agent re-evaluates the chunk as a fresh subject ✓
- No inter-session time bleeds into `time_seconds`

### 4. Stop → Clear Transcript → Start
- `clear_for_transcript_unlocked()` resets `topics_last_run_ts = 0` and `topics_last_final_idx = 0`
- `topics_session_started_ts` updated on Start
- `0 < session_started_ts` → clamping fires, cursor at 0 ✓

### 5. Stop → Clear Topics → Start
- `clear()` resets `topics_last_run_ts = 0` and `topics_last_final_idx = 0`
- Same behaviour as Scenario 4 ✓

### 6. Clear topics mid-session (while running)
- `clear()` resets `topics_last_run_ts = 0`
- `0 < current session_started_ts` → next run clamps span to session start
- `from_idx = 0`, so ALL finals since session start are included in the re-analysis ✓

### 7. Clear transcript mid-session (while running)
- `clear_for_transcript_unlocked()` resets cursor and `topics_last_run_ts = 0`
- Same behaviour as Scenario 6 ✓

### 8. Manual Analyze Now — first run of session
- `topics_last_run_ts < topics_session_started_ts` → clamping fires ✓

### 9. Manual Analyze Now — mid-session
- `topics_last_run_ts > topics_session_started_ts` → clamping does not fire
- Normal `prev_ts` boundary used ✓

### 10. Auto-stop (silence / max session limit)
- Watchdog calls `await self.stop_async()`
- Final topic flush fires before `_do_finalize()` ✓

### 11. SDK stops itself (network error, tier limit, recogniser restart)
- Azure SDK fires a `status` event with `running = False`
- `handle_speech_event` detects `was_running and not self.running`
- Calls `_do_finalize()` → `finalize_on_stop_unlocked()` → active→covered ✓
- This path was previously unguarded; topics would stay `active` indefinitely

### 12. Window mode
- `span_start_ts` clamping is guarded by `topics_chunk_mode == "since_last"`
- Window mode derives its own time range from `now − window_sec`; unaffected ✓

### 13. Stop before any agent run has fired
- `finalize_on_stop_unlocked()` only acts on topics with `status == "active"`
- If no topics exist yet, it is a no-op ✓

---

## Stop Paths and `_do_finalize()`

`_do_finalize()` is the single method that:
1. Resets coach and translation state
2. Sets `topics_pending = False`
3. Calls `finalize_on_stop_unlocked()` — converts all `active` topics to `covered`
4. Broadcasts the final `topics_update` to all WebSocket clients

It is idempotent. `finalize_on_stop_unlocked` only processes `active` topics, so
calling it on an already-finalised session is a no-op.

| Trigger | Path to `_do_finalize()` |
|---|---|
| User presses Stop (API) | `POST /stop` → `controller.stop_async()` → `session_manager.stop_async()` → final topic flush → `run_summary()` → `_do_finalize()` |
| Watchdog auto-stop | `watchdog_loop` → `await self.stop_async()` → final topic flush → `run_summary()` → `_do_finalize()` |
| SDK stops itself | `handle_speech_event("status", running=False)` → `_do_finalize()` |

**Note**: on a user-pressed Stop, `_do_finalize()` is called twice — once from
`stop_async()` and once when the SDK's `status(running=False)` event arrives shortly
after. This is safe (idempotent) and results in one redundant `topics_update` broadcast
with identical data.

---

## Final Flush + Summary on Stop (`stop_async`)

`stop_async()` runs one final topic-agent call before summary/finalize to capture any
transcript turns that arrived after the last periodic run:

```python
async def stop_async(self) -> bool:
    stopped = self._speech.stop_recognition()
    if not stopped:
        return False
    topic_call = None
    with self._lock:
        if topics_enabled and tracker_configured and not topics_pending:
            topic_call = prepare_call_unlocked(now, trigger="auto")
    if topic_call:
        try:
            await asyncio.wait_for(run_update(topic_call), timeout=30.0)
        except Exception:
            pass  # flush failure must not block cleanup
    try:
        await asyncio.wait_for(run_summary(), timeout=60.0)
    except Exception:
        pass  # summary failure must not block cleanup
    self._do_finalize()
    return True
```

If no new finals exist since the last run, `prepare_call_unlocked` returns `None` and
the topic-flush step is skipped. Summary still runs when enabled and configured.

---

## Known Acceptable Limitation

After the final flush, there may be a tiny residual gap (milliseconds) between the last
statement timestamp in the flush chunk and the actual stop time. This is not tracked in
`time_seconds`. The gap is negligible in practice (< 1 s) compared to the previously
untracked trailing speech (which could be minutes).

---

## `possible_context_reset` on Restart

On Stop → Start with transcript kept, the first chunk of the new session will have:

```
gap_seconds = first_new_final_ts − last_old_final_ts
```

This gap includes the inter-session pause, which is always > 45 s (the threshold).
So `possible_context_reset = True` is sent to the agent, which re-evaluates the chunk
as a fresh subject regardless of `current_topics` or `recent_context`. This is the
correct and desired behaviour.
